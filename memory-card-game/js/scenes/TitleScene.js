/**
 * TitleScene
 * - 게임 제목, 난이도 선택(Easy/Normal/Hard), 최고기록 표시, 사운드 토글, 시작 버튼.
 * - 난이도 선택 시 settings.lastDifficulty 를 갱신한다.
 * - [게임 시작] 클릭 시 GameScene 으로 difficulty 를 넘긴다.
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

  const { ScoreManager } = global.MCG;

  class TitleScene extends Phaser.Scene {
    constructor() {
      super({ key: SCENES.title });
    }

    create() {
      // 배경 그라데이션 (위→아래)
      const bg = this.add.graphics();
      bg.fillGradientStyle(
        COLORS.bgTop,
        COLORS.bgTop,
        COLORS.bgBottom,
        COLORS.bgBottom,
        1
      );
      bg.fillRect(0, 0, GAME_WIDTH, GAME_HEIGHT);

      // 타이틀
      this.add
        .text(GAME_WIDTH / 2, 110, "Memory Card Game", {
          fontFamily: '"Segoe UI", "Noto Sans KR", system-ui, sans-serif',
          fontSize: "56px",
          fontStyle: "bold",
          color: "#ffd166",
        })
        .setOrigin(0.5);

      this.add
        .text(GAME_WIDTH / 2, 165, "짝맞추기 카드 게임", {
          fontFamily: '"Segoe UI", "Noto Sans KR", system-ui, sans-serif',
          fontSize: "20px",
          color: "#b9bee0",
        })
        .setOrigin(0.5);

      // 현재 선택된 난이도 (마지막 플레이 난이도 우선)
      const settings = ScoreManager.getSettings();
      this.selectedDifficulty = DIFFICULTIES[settings.lastDifficulty]
        ? settings.lastDifficulty
        : "easy";

      // 난이도 버튼 3개
      const diffKeys = ["easy", "normal", "hard"];
      const btnW = 240;
      const btnH = 130;
      const gap = 30;
      const totalW = btnW * 3 + gap * 2;
      const startX = (GAME_WIDTH - totalW) / 2 + btnW / 2;
      const y = 320;

      this.difficultyButtons = {};
      diffKeys.forEach((key, i) => {
        const x = startX + i * (btnW + gap);
        const btn = this._createDifficultyCard(x, y, btnW, btnH, key);
        this.difficultyButtons[key] = btn;
      });
      this._refreshDifficultySelection();

      // 시작 버튼
      this._createPrimaryButton(
        GAME_WIDTH / 2,
        540,
        260,
        62,
        "게임 시작",
        () => this._startGame()
      );

      // 사운드 토글
      this.soundOn = !!settings.soundOn;
      global.MCG.sound.setEnabled(this.soundOn);
      this.soundToggleText = this.add
        .text(GAME_WIDTH / 2, 620, this._soundLabel(), {
          fontFamily: '"Segoe UI", "Noto Sans KR", system-ui, sans-serif',
          fontSize: "18px",
          color: "#b9bee0",
        })
        .setOrigin(0.5)
        .setInteractive({ useHandCursor: true });

      this.soundToggleText.on("pointerdown", () => this._toggleSound());

      // 키보드: 1/2/3 난이도 선택, Enter 시작, S 사운드 토글
      this.input.keyboard.on("keydown", (e) => {
        if (e.key === "1") this._selectDifficulty("easy");
        else if (e.key === "2") this._selectDifficulty("normal");
        else if (e.key === "3") this._selectDifficulty("hard");
        else if (e.key === "Enter" || e.key === " ") this._startGame();
        else if (e.key === "s" || e.key === "S") this._toggleSound();
      });

      // 푸터 안내
      this.add
        .text(
          GAME_WIDTH / 2,
          GAME_HEIGHT - 30,
          "키보드: 1/2/3 = 난이도, Enter = 시작, S = 사운드",
          {
            fontFamily: '"Segoe UI", "Noto Sans KR", system-ui, sans-serif',
            fontSize: "14px",
            color: "#7a80a8",
          }
        )
        .setOrigin(0.5);
    }

    /* ------------------------------- 내부 ------------------------------- */

    _soundLabel() {
      return this.soundOn ? "사운드: ON  (S)" : "사운드: OFF  (S)";
    }

    _toggleSound() {
      this.soundOn = !this.soundOn;
      global.MCG.sound.setEnabled(this.soundOn);
      ScoreManager.saveSettings({ soundOn: this.soundOn });
      this.soundToggleText.setText(this._soundLabel());
    }

    _selectDifficulty(key) {
      if (!DIFFICULTIES[key]) return;
      this.selectedDifficulty = key;
      ScoreManager.saveSettings({ lastDifficulty: key });
      this._refreshDifficultySelection();
    }

    _refreshDifficultySelection() {
      Object.keys(this.difficultyButtons).forEach((key) => {
        const isSel = key === this.selectedDifficulty;
        this.difficultyButtons[key].setSelected(isSel);
      });
    }

    _startGame() {
      // 사용자 입력 후 AudioContext 활성화
      global.MCG.sound.ensure();
      this.scene.start(SCENES.game, {
        difficultyKey: this.selectedDifficulty,
      });
    }

    /** 난이도 선택 카드 — 점수/시간 최고기록 함께 표기 */
    _createDifficultyCard(x, y, w, h, diffKey) {
      const diff = DIFFICULTIES[diffKey];

      const container = this.add.container(x, y);
      const bg = this.add.graphics();
      const draw = (selected) => {
        bg.clear();
        const fill = selected ? COLORS.accent : COLORS.buttonBg;
        const edge = selected ? 0xffe79e : COLORS.buttonBgHover;
        bg.fillStyle(edge, 1);
        bg.fillRoundedRect(-w / 2, -h / 2, w, h, 14);
        bg.fillStyle(fill, 1);
        bg.fillRoundedRect(-w / 2 + 3, -h / 2 + 3, w - 6, h - 6, 12);
      };
      draw(false);

      const titleText = this.add
        .text(0, -h / 2 + 22, diff.label, {
          fontFamily: '"Segoe UI", "Noto Sans KR", system-ui, sans-serif',
          fontSize: "26px",
          fontStyle: "bold",
          color: "#0f1120",
        })
        .setOrigin(0.5);

      const sizeText = this.add
        .text(0, -h / 2 + 52, `${diff.cols} × ${diff.rows}  ·  ${diff.pairs}쌍`, {
          fontFamily: '"Segoe UI", "Noto Sans KR", system-ui, sans-serif',
          fontSize: "16px",
          color: "#1a1d2e",
        })
        .setOrigin(0.5);

      const bestScore = ScoreManager.getBestScore(diffKey);
      const bestTime = ScoreManager.getBestTime(diffKey);
      const bestLine =
        bestScore > 0
          ? `최고 ${bestScore}점 · ${formatTime(bestTime)}`
          : "최고기록 없음";

      const bestText = this.add
        .text(0, h / 2 - 22, bestLine, {
          fontFamily: '"Segoe UI", "Noto Sans KR", system-ui, sans-serif',
          fontSize: "14px",
          color: "#3a3f66",
        })
        .setOrigin(0.5);

      container.add([bg, titleText, sizeText, bestText]);
      container.setSize(w, h);
      container.setInteractive(
        new Phaser.Geom.Rectangle(-w / 2, -h / 2, w, h),
        Phaser.Geom.Rectangle.Contains
      );
      container.input.cursor = "pointer";

      container.on("pointerdown", () => this._selectDifficulty(diffKey));
      container.on("pointerover", () => {
        this.tweens.add({ targets: container, scale: 1.03, duration: 120 });
      });
      container.on("pointerout", () => {
        this.tweens.add({ targets: container, scale: 1.0, duration: 120 });
      });

      container.setSelected = (selected) => draw(selected);
      return container;
    }

    /** 주요 액션 버튼 (시작) */
    _createPrimaryButton(x, y, w, h, label, onClick) {
      const container = this.add.container(x, y);
      const bg = this.add.graphics();
      const drawBg = (hover) => {
        bg.clear();
        bg.fillStyle(hover ? 0xff9f1c : COLORS.danger, 1);
        bg.fillRoundedRect(-w / 2, -h / 2, w, h, h / 2);
      };
      drawBg(false);

      const text = this.add
        .text(0, 0, label, {
          fontFamily: '"Segoe UI", "Noto Sans KR", system-ui, sans-serif',
          fontSize: "24px",
          fontStyle: "bold",
          color: "#ffffff",
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
        drawBg(true);
        this.tweens.add({ targets: container, scale: 1.04, duration: 120 });
      });
      container.on("pointerout", () => {
        drawBg(false);
        this.tweens.add({ targets: container, scale: 1.0, duration: 120 });
      });
      container.on("pointerdown", onClick);
      return container;
    }
  }

  function formatTime(sec) {
    if (!sec) return "--:--";
    const m = Math.floor(sec / 60);
    const s = Math.floor(sec % 60);
    return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
  }

  global.MCG.TitleScene = TitleScene;
})(window);
