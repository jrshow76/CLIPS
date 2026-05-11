/**
 * ScoreManager
 * - 한 게임의 점수/콤보/시도/타이머를 관리한다.
 * - 최종 점수 공식 (SPEC §3):
 *     score = (base * pairs) + comboBonusSum - attemptPenalty + timeBonus
 *     attemptPenalty = penalty * max(0, attempts - pairs)
 *     timeBonus      = max(0, (timeLimit - elapsed) * timeCoef)
 * - localStorage 의 최고 점수/최단 시간 갱신도 담당.
 */
(function (global) {
  "use strict";

  const { SCORE, STORAGE_KEYS } = global.MCG.config;

  class ScoreManager {
    constructor(difficulty) {
      this.difficulty = difficulty; // { pairs, timeLimit, timeCoef, key, ... }
      this.reset();
    }

    reset() {
      this.attempts = 0;
      this.matchedPairs = 0;
      this.combo = 0;
      this.comboBonusSum = 0;
      this.elapsedMs = 0;
      this.timerStarted = false;
      this.timerStartTs = 0;
      this.timerStoppedAt = 0;
    }

    /** 첫 카드 뒤집힐 때 타이머 시작 */
    startTimer() {
      if (this.timerStarted) return;
      this.timerStarted = true;
      this.timerStartTs = performance.now();
    }

    /** 결과 화면 진입 시 타이머 종료 */
    stopTimer() {
      if (!this.timerStarted || this.timerStoppedAt) return;
      this.timerStoppedAt = performance.now();
      this.elapsedMs = this.timerStoppedAt - this.timerStartTs;
    }

    /** 매 프레임에서 호출 — 종료 전까지 elapsed 갱신 */
    tick() {
      if (this.timerStarted && !this.timerStoppedAt) {
        this.elapsedMs = performance.now() - this.timerStartTs;
      }
    }

    /** 2장째 카드가 뒤집힌 시점에 호출 */
    registerAttempt() {
      this.attempts += 1;
    }

    /**
     * 매칭 결과 적용. 성공 시 콤보 보너스를 누적해서 돌려준다.
     * @returns {{ isMatch: boolean, gained: number, comboBonus: number }}
     */
    applyMatchResult(isMatch) {
      if (!isMatch) {
        this.combo = 0;
        return { isMatch: false, gained: 0, comboBonus: 0 };
      }
      this.combo += 1;
      this.matchedPairs += 1;
      const comboBonus = Math.max(0, (this.combo - 1) * SCORE.comboStep);
      this.comboBonusSum += comboBonus;
      const gained = SCORE.base + comboBonus;
      return { isMatch: true, gained, comboBonus };
    }

    getElapsedSeconds() {
      return Math.floor(this.elapsedMs / 1000);
    }

    /** 현재까지의 점수 (게임 중 표시용) */
    getCurrentScore() {
      const pairs = this.difficulty.pairs;
      const base = SCORE.base * this.matchedPairs;
      const penalty =
        SCORE.attemptPenalty * Math.max(0, this.attempts - pairs);
      // 게임 중에는 시간 보너스를 실시간으로 미리보기처럼 보여준다.
      const elapsed = this.getElapsedSeconds();
      const timeBonus = Math.max(
        0,
        (this.difficulty.timeLimit - elapsed) * this.difficulty.timeCoef
      );
      return Math.max(0, base + this.comboBonusSum - penalty + timeBonus);
    }

    /** 종료 시 최종 점수 — stopTimer() 이후 호출하세요. */
    getFinalScore() {
      const pairs = this.difficulty.pairs;
      const base = SCORE.base * pairs;
      const penalty =
        SCORE.attemptPenalty * Math.max(0, this.attempts - pairs);
      const elapsed = this.getElapsedSeconds();
      const timeBonus = Math.max(
        0,
        (this.difficulty.timeLimit - elapsed) * this.difficulty.timeCoef
      );
      const total = base + this.comboBonusSum - penalty + timeBonus;
      return {
        total: Math.max(0, total),
        breakdown: {
          base,
          comboBonus: this.comboBonusSum,
          penalty,
          timeBonus,
          elapsed,
          attempts: this.attempts,
          pairs,
        },
      };
    }

    /* --------------------------- localStorage --------------------------- */

    static safeGetNumber(key) {
      try {
        const v = localStorage.getItem(key);
        if (v == null) return 0;
        const n = Number(v);
        return Number.isFinite(n) ? n : 0;
      } catch (e) {
        return 0;
      }
    }

    static safeSetNumber(key, value) {
      try {
        localStorage.setItem(key, String(value));
        return true;
      } catch (e) {
        return false;
      }
    }

    static getBestScore(difficultyKey) {
      return ScoreManager.safeGetNumber(STORAGE_KEYS.bestScore(difficultyKey));
    }

    static getBestTime(difficultyKey) {
      return ScoreManager.safeGetNumber(STORAGE_KEYS.bestTime(difficultyKey));
    }

    /**
     * 최고 기록 갱신 시도.
     * @returns {{ newBestScore: boolean, newBestTime: boolean }}
     */
    static updateBestRecords(difficultyKey, finalScore, elapsedSec) {
      const result = { newBestScore: false, newBestTime: false };
      const prevScore = ScoreManager.getBestScore(difficultyKey);
      if (finalScore > prevScore) {
        ScoreManager.safeSetNumber(
          STORAGE_KEYS.bestScore(difficultyKey),
          finalScore
        );
        result.newBestScore = true;
      }
      const prevTime = ScoreManager.getBestTime(difficultyKey);
      if (prevTime === 0 || elapsedSec < prevTime) {
        ScoreManager.safeSetNumber(
          STORAGE_KEYS.bestTime(difficultyKey),
          elapsedSec
        );
        result.newBestTime = true;
      }
      return result;
    }

    /* ------------------------------ settings ----------------------------- */

    static getSettings() {
      const defaults = { soundOn: true, lastDifficulty: "easy" };
      try {
        const raw = localStorage.getItem(STORAGE_KEYS.settings);
        if (!raw) return defaults;
        const obj = JSON.parse(raw);
        return { ...defaults, ...obj };
      } catch (e) {
        // 손상 시 기본값 반환 + 정리
        try { localStorage.removeItem(STORAGE_KEYS.settings); } catch (_) {}
        return defaults;
      }
    }

    static saveSettings(partial) {
      const merged = { ...ScoreManager.getSettings(), ...partial };
      try {
        localStorage.setItem(STORAGE_KEYS.settings, JSON.stringify(merged));
      } catch (e) {
        // 무시 (메모리 폴백)
      }
      return merged;
    }
  }

  global.MCG.ScoreManager = ScoreManager;
})(window);
