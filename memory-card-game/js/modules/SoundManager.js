/**
 * SoundManager
 * - Web Audio API 기반 효과음 합성기. 외부 오디오 파일을 사용하지 않는다.
 * - 브라우저 자동재생 정책에 따라, 최초 사용자 입력 후 AudioContext 를 활성화한다.
 *   (Phaser 의 첫 클릭 콜백 또는 ensure() 메서드 호출 시점)
 */
(function (global) {
  "use strict";

  class SoundManager {
    constructor() {
      this.ctx = null;
      this.master = null;
      this.enabled = true;
      this._ready = false;
    }

    /** 처음 호출 시 AudioContext 생성. 사용자 입력 후에 호출되어야 한다. */
    ensure() {
      if (this._ready) return;
      const Ctor = global.AudioContext || global.webkitAudioContext;
      if (!Ctor) {
        // 미지원 브라우저는 무음 처리
        this._ready = true;
        return;
      }
      try {
        this.ctx = new Ctor();
        this.master = this.ctx.createGain();
        this.master.gain.value = 0.25;
        this.master.connect(this.ctx.destination);
        this._ready = true;
      } catch (e) {
        this._ready = true;
      }
    }

    setEnabled(on) {
      this.enabled = !!on;
    }

    isEnabled() {
      return this.enabled;
    }

    _resumeIfNeeded() {
      if (this.ctx && this.ctx.state === "suspended") {
        // resume 은 Promise 를 돌려주지만 fire-and-forget 으로 충분
        this.ctx.resume().catch(() => {});
      }
    }

    /**
     * 짧은 톤 하나 재생.
     * @param {object} opts { freq, type, duration(ms), gain, startOffset(ms), slideTo }
     */
    _playTone(opts) {
      if (!this.enabled || !this._ready || !this.ctx) return;
      const {
        freq = 440,
        type = "sine",
        duration = 120,
        gain = 0.4,
        startOffset = 0,
        slideTo = null,
      } = opts;
      this._resumeIfNeeded();

      const now = this.ctx.currentTime + startOffset / 1000;
      const osc = this.ctx.createOscillator();
      const g = this.ctx.createGain();

      osc.type = type;
      osc.frequency.setValueAtTime(freq, now);
      if (slideTo != null) {
        osc.frequency.linearRampToValueAtTime(slideTo, now + duration / 1000);
      }

      // ADSR 비슷한 짧은 envelope (클릭 노이즈 방지)
      g.gain.setValueAtTime(0.0001, now);
      g.gain.exponentialRampToValueAtTime(gain, now + 0.005);
      g.gain.exponentialRampToValueAtTime(0.0001, now + duration / 1000);

      osc.connect(g).connect(this.master);
      osc.start(now);
      osc.stop(now + duration / 1000 + 0.02);
    }

    /* ------------------------- 게임 이벤트별 SFX ------------------------- */

    // 카드 뒤집기: 800Hz square, 50ms (짧은 클릭)
    flip() {
      this._playTone({ freq: 800, type: "square", duration: 50, gain: 0.2 });
    }

    // 매칭 성공: C5 → E5 상행, sine, 각 100ms
    match() {
      this._playTone({ freq: 523.25, type: "sine", duration: 100, gain: 0.35 });
      this._playTone({ freq: 659.26, type: "sine", duration: 100, gain: 0.35, startOffset: 90 });
    }

    // 매칭 실패: A3 하강, sawtooth, 200ms
    mismatch() {
      this._playTone({
        freq: 220,
        slideTo: 150,
        type: "sawtooth",
        duration: 200,
        gain: 0.2,
      });
    }

    // 게임 클리어: C5-E5-G5-C6 멜로디 100ms씩
    clear() {
      const notes = [523.25, 659.26, 783.99, 1046.5];
      notes.forEach((f, i) => {
        this._playTone({
          freq: f,
          type: "triangle",
          duration: 130,
          gain: 0.3,
          startOffset: i * 110,
        });
      });
    }
  }

  // 전역 싱글톤
  global.MCG.SoundManager = SoundManager;
  global.MCG.sound = new SoundManager();
})(window);
