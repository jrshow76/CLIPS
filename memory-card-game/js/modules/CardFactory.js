/**
 * CardFactory
 * - 카드 한 장을 Phaser.GameObjects.Container 로 만든다.
 * - 외부 이미지/스프라이트 시트 없이, Graphics + Text 만으로 구성한다.
 * - flip 애니메이션은 scaleX (1 → 0 → 1) tween 으로 처리하면서
 *   중간 시점에 앞/뒷면 표시를 토글한다.
 */
(function (global) {
  "use strict";

  const { COLORS, TIMING } = global.MCG.config;

  /**
   * @param {Phaser.Scene} scene
   * @param {object} opts { x, y, width, height, emoji, onClick }
   * @returns Phaser.GameObjects.Container (.cardState, .flip(), .showMatched() 등 메서드 포함)
   */
  function createCard(scene, opts) {
    const { x, y, width, height, emoji, onClick } = opts;
    const radius = Math.min(14, Math.floor(Math.min(width, height) * 0.12));

    const container = scene.add.container(x, y);
    container.setSize(width, height);

    // 뒷면: 카드 베이스 + 패턴 점 + 가장자리
    const back = scene.add.graphics();
    drawCardBg(back, width, height, radius, COLORS.cardBack, COLORS.cardBackEdge);
    drawBackPattern(back, width, height);

    // 앞면: 밝은 배경 + 이모지
    const front = scene.add.graphics();
    drawCardBg(front, width, height, radius, COLORS.cardFront, COLORS.cardFrontEdge);

    const emojiSize = Math.floor(Math.min(width, height) * 0.55);
    const emojiText = scene.add.text(0, 0, emoji, {
      fontFamily:
        '"Apple Color Emoji","Segoe UI Emoji","Noto Color Emoji",sans-serif',
      fontSize: `${emojiSize}px`,
      color: "#222",
    });
    emojiText.setOrigin(0.5, 0.5);

    front.setVisible(false);
    emojiText.setVisible(false);

    container.add([back, front, emojiText]);

    // 인터랙션 영역
    container.setInteractive(
      new Phaser.Geom.Rectangle(-width / 2, -height / 2, width, height),
      Phaser.Geom.Rectangle.Contains
    );
    container.input.cursor = "pointer";

    // 상태 관리
    container.cardState = {
      emoji,
      isRevealed: false,
      isMatched: false,
      isAnimating: false,
    };

    container.on("pointerover", () => {
      if (
        container.cardState.isRevealed ||
        container.cardState.isMatched ||
        container.cardState.isAnimating
      )
        return;
      scene.tweens.add({
        targets: container,
        scale: 1.04,
        duration: 120,
        ease: "Sine.easeOut",
      });
    });
    container.on("pointerout", () => {
      if (container.cardState.isMatched) return;
      scene.tweens.add({
        targets: container,
        scale: 1,
        duration: 120,
        ease: "Sine.easeOut",
      });
    });
    container.on("pointerdown", () => {
      if (typeof onClick === "function") onClick(container);
    });

    /**
     * 카드를 reveal=true(앞면) 또는 false(뒷면) 로 뒤집는 애니메이션.
     * @param {boolean} reveal
     * @param {Function} [onComplete]
     */
    container.flip = function flip(reveal, onComplete) {
      if (container.cardState.isAnimating) return;
      container.cardState.isAnimating = true;
      const half = TIMING.flipDuration;
      scene.tweens.add({
        targets: container,
        scaleX: 0,
        duration: half,
        ease: "Cubic.easeIn",
        onComplete: () => {
          container.cardState.isRevealed = reveal;
          back.setVisible(!reveal);
          front.setVisible(reveal);
          emojiText.setVisible(reveal);
          scene.tweens.add({
            targets: container,
            scaleX: 1,
            duration: half,
            ease: "Cubic.easeOut",
            onComplete: () => {
              container.cardState.isAnimating = false;
              if (typeof onComplete === "function") onComplete();
            },
          });
        },
      });
    };

    /** 매칭 완료 연출: 살짝 축소 + 색상 하이라이트 */
    container.showMatched = function showMatched() {
      container.cardState.isMatched = true;
      // 매칭됨을 표현하기 위해 앞면 배경을 다시 그린다
      front.clear();
      drawCardBg(front, width, height, radius, COLORS.cardMatched, COLORS.cardMatched);
      // 이모지 색 대비를 위해 흰색에 가까운 명도로
      emojiText.setAlpha(0.95);

      scene.tweens.add({
        targets: container,
        scale: 0.92,
        alpha: 0.9,
        duration: TIMING.matchedFadeMs,
        ease: "Sine.easeOut",
      });
      container.disableInteractive();
    };

    return container;
  }

  /** 둥근 모서리 사각형 카드 배경 그리기 */
  function drawCardBg(g, w, h, r, fill, edge) {
    g.fillStyle(edge, 1);
    g.fillRoundedRect(-w / 2, -h / 2, w, h, r);
    g.fillStyle(fill, 1);
    const inset = 3;
    g.fillRoundedRect(
      -w / 2 + inset,
      -h / 2 + inset,
      w - inset * 2,
      h - inset * 2,
      Math.max(0, r - inset)
    );
  }

  /** 뒷면 장식: 가운데 마름모 + 작은 점들 */
  function drawBackPattern(g, w, h) {
    g.lineStyle(2, 0xffffff, 0.25);
    const cx = 0;
    const cy = 0;
    const d = Math.min(w, h) * 0.35;
    g.beginPath();
    g.moveTo(cx, cy - d);
    g.lineTo(cx + d, cy);
    g.lineTo(cx, cy + d);
    g.lineTo(cx - d, cy);
    g.closePath();
    g.strokePath();

    g.fillStyle(0xffffff, 0.18);
    const dotR = Math.max(2, Math.floor(Math.min(w, h) * 0.025));
    g.fillCircle(cx, cy, dotR);
    g.fillCircle(cx, cy - d, dotR);
    g.fillCircle(cx, cy + d, dotR);
    g.fillCircle(cx - d, cy, dotR);
    g.fillCircle(cx + d, cy, dotR);
  }

  global.MCG.CardFactory = { createCard };
})(window);
