/**
 * ResultScene
 * - 클리어 메시지, 소요 시간/시도/점수 breakdown, 신기록 배지 표시.
 * - [다시 하기] 동일 난이도 재시작, [메뉴] 타이틀로 복귀.
 */
(function (global) {
  "use strict";

  const {
    GAME_WIDTH,
    GAME_HEIGHT,
    DIFFICULTIES,
    COLORS,
    SCENES,
  } = global.MCG.config;

  class ResultScene extends Phaser.Scene {
    constructor() {
      super({ key: SCENES.result });
    }

    init(data) {
      this.difficultyKey = (data && data.difficultyKey) || "easy";
      this.difficulty = DIFFICULTIES[this.difficultyKey];
      this.finalScore = (data && data.finalScore) || 0;
      this.breakdown = (data && data.breakdown) || {
        base: 0,
        comboBonus: 0,
        penalty: 0,
        timeBonus: 0,
        elapsed: 0,
        attempts: 0,
        pairs: this.difficulty.pairs,
      };
      this.newBestScore = !!(data && data.newBestScore);
      this.newBestTime = !!(data && data.newBestTime);
    }

    create() {
      // 배경
      const bg = this.add.graphics();
      bg.fillGradientStyle(
        COLORS.bgTop,
        COLORS.bgTop,
        COLORS.bgBottom,
        COLORS.bgBottom,
        1
      );
      bg.fillRect(0, 0, GAME_WIDTH, GAME_HEIGHT);

      // 패널
      const panelW = 640;
      const panelH = 520;
      const panelX = GAME_WIDTH / 2;
      const panelY = GAME_HEIGHT / 2;
      const panel = this.add.graphics();
      panel.fillStyle(0x1a1d2e, 0.95);
      panel.fillRoundedRect(
        panelX - panelW / 2,
        panelY - panelH / 2,
        panelW,
        panelH,
        20
      );
      panel.lineStyle(2, COLORS.accent, 0.5);
      panel.strokeRoundedRect(
        panelX - panelW / 2,
        panelY - panelH / 2,
        panelW,
        panelH,
        20
      );

      // 타이틀
      this.add
        .text(GAME_WIDTH / 2, panelY - panelH / 2 + 50, "Clear!", {
          fontFamily: '"Segoe UI", "Noto Sans KR", system-ui, sans-serif',
          fontSize: "52px",
          fontStyle: "bold",
          color: "#ffd166",
        })
        .setOrigin(0.5);

      this.add
        .text(
          GAME_WIDTH / 2,
          panelY - panelH / 2 + 96,
          `난이도: ${this.difficulty.label}`,
          {
            fontFamily: '"Segoe UI", "Noto Sans KR", system-ui, sans-serif',
            fontSize: "18px",
            color: "#b9bee0",
          }
        )
        .setOrigin(0.5);

      // 메인 점수
      const scoreY = panelY - 70;
      this.add
        .text(GAME_WIDTH / 2, scoreY, String(this.finalScore), {
          fontFamily: '"Segoe UI", "Noto Sans KR", system-ui, sans-serif',
          fontSize: "76px",
          fontStyle: "bold",
          color: "#06d6a0",
        })
        .setOrigin(0.5);
      this.add
        .text(GAME_WIDTH / 2, scoreY + 52, "FINAL SCORE", {
          fontFamily: '"Segoe UI", "Noto Sans KR", system-ui, sans-serif',
          fontSize: "14px",
          color: "#b9bee0",
        })
        .setOrigin(0.5);

      // 신기록 배지
      if (this.newBestScore || this.newBestTime) {
        const badgeLabel = this.newBestScore
          ? "★ NEW BEST SCORE ★"
          : "★ NEW BEST TIME ★";
        const badge = this.add
          .text(GAME_WIDTH / 2, scoreY - 80, badgeLabel, {
            fontFamily: '"Segoe UI", "Noto Sans KR", system-ui, sans-serif',
            fontSize: "20px",
            fontStyle: "bold",
            color: "#0f1120",
            backgroundColor: "#ffd166",
            padding: { x: 14, y: 6 },
          })
          .setOrigin(0.5);
        this.tweens.add({
          targets: badge,
          scale: { from: 0.6, to: 1 },
          duration: 350,
          ease: "Back.easeOut",
        });
      }

      // 상세 표
      const detail = [
        [`소요 시간`, formatMmSs(this.breakdown.elapsed)],
        [`시도 횟수`, `${this.breakdown.attempts} (최소 ${this.breakdown.pairs})`],
        [`매칭 기본`, `+${this.breakdown.base}`],
        [`콤보 보너스`, `+${this.breakdown.comboBonus}`],
        [`시도 페널티`, `-${this.breakdown.penalty}`],
        [`시간 보너스`, `+${this.breakdown.timeBonus}`],
      ];
      const detailY0 = panelY + 30;
      detail.forEach((row, i) => {
        const y = detailY0 + i * 26;
        this.add
          .text(panelX - 200, y, row[0], {
            fontFamily: '"Segoe UI", "Noto Sans KR", system-ui, sans-serif',
            fontSize: "16px",
            color: "#b9bee0",
          })
          .setOrigin(0, 0.5);
        this.add
          .text(panelX + 200, y, row[1], {
            fontFamily: '"Segoe UI", "Noto Sans KR", system-ui, sans-serif',
            fontSize: "16px",
            color: "#f1f3ff",
          })
          .setOrigin(1, 0.5);
      });

      // 버튼
      const btnY = panelY + panelH / 2 - 60;
      this._createButton(panelX - 110, btnY, 200, 50, "다시 하기 (R)", () =>
        this.scene.start(SCENES.game, { difficultyKey: this.difficultyKey })
      );
      this._createButton(panelX + 110, btnY, 200, 50, "메뉴 (M)", () =>
        this.scene.start(SCENES.title)
      );

      // 키보드 단축키
      this.input.keyboard.on("keydown", (e) => {
        if (e.key === "r" || e.key === "R" || e.key === "Enter") {
          this.scene.start(SCENES.game, { difficultyKey: this.difficultyKey });
        } else if (e.key === "m" || e.key === "M" || e.key === "Escape") {
          this.scene.start(SCENES.title);
        }
      });
    }

    _createButton(x, y, w, h, label, onClick) {
      const container = this.add.container(x, y);
      const bg = this.add.graphics();
      const draw = (hover) => {
        bg.clear();
        bg.fillStyle(hover ? COLORS.buttonBgHover : COLORS.buttonBg, 1);
        bg.fillRoundedRect(-w / 2, -h / 2, w, h, h / 2);
      };
      draw(false);
      const text = this.add
        .text(0, 0, label, {
          fontFamily: '"Segoe UI", "Noto Sans KR", system-ui, sans-serif',
          fontSize: "18px",
          fontStyle: "bold",
          color: "#f1f3ff",
        })
        .setOrigin(0.5);
      container.add([bg, text]);
      container.setSize(w, h);
      container.setInteractive(
        new Phaser.Geom.Rectangle(-w / 2, -h / 2, w, h),
        Phaser.Geom.Rectangle.Contains
      );
      container.input.cursor = "pointer";
      container.on("pointerover", () => {
        draw(true);
        this.tweens.add({ targets: container, scale: 1.04, duration: 120 });
      });
      container.on("pointerout", () => {
        draw(false);
        this.tweens.add({ targets: container, scale: 1.0, duration: 120 });
      });
      container.on("pointerdown", onClick);
      return container;
    }
  }

  function formatMmSs(sec) {
    const m = Math.floor(sec / 60);
    const s = sec % 60;
    return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
  }

  global.MCG.ResultScene = ResultScene;
})(window);
