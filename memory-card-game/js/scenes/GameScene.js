/**
 * GameScene
 * - 난이도에 따라 카드 그리드를 생성, HUD 표시, 매칭 로직 처리.
 * - 입력 잠금 플래그(isLocked) 로 빠른 연속 클릭을 차단한다.
 * - 모든 쌍 매칭 완료 시 ResultScene 으로 전환한다.
 */
(function (global) {
  "use strict";

  const {
    GAME_WIDTH,
    GAME_HEIGHT,
    DIFFICULTIES,
    EMOJI_POOL,
    COLORS,
    TIMING,
    SCENES,
  } = global.MCG.config;

  const { ScoreManager, CardFactory } = global.MCG;

  // HUD 영역 (상단/하단 reserve)
  const HUD_TOP_H = 90;
  const HUD_BOTTOM_H = 70;

  class GameScene extends Phaser.Scene {
    constructor() {
      super({ key: SCENES.game });
    }

    init(data) {
      this.difficultyKey = (data && data.difficultyKey) || "easy";
      this.difficulty = DIFFICULTIES[this.difficultyKey];
      this.score = new ScoreManager(this.difficulty);
      this.cards = [];
      this.firstPick = null;
      this.secondPick = null;
      this.isLocked = false;
      this.gameOver = false;
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

      this._buildHud();
      this._buildBoard();
      this._buildBottomBar();
      this._bindKeyboard();

      // 사용자 입력 후 AudioContext 활성화 (안전망)
      this.input.once("pointerdown", () => global.MCG.sound.ensure());
    }

    update() {
      if (this.gameOver) return;
      this.score.tick();
      this._refreshHud();
    }

    /* ------------------------------ HUD ------------------------------ */

    _buildHud() {
      const padX = 28;
      const y = HUD_TOP_H / 2;

      this.hudTime = this.add
        .text(padX, y, "00:00", this._hudStyle(28))
        .setOrigin(0, 0.5);

      this.add
        .text(padX, y + 22, "TIME", this._hudStyle(12, "#b9bee0"))
        .setOrigin(0, 0.5);

      this.hudAttempts = this.add
        .text(GAME_WIDTH * 0.33, y, "0", this._hudStyle(28))
        .setOrigin(0.5);
      this.add
        .text(GAME_WIDTH * 0.33, y + 22, "TRIES", this._hudStyle(12, "#b9bee0"))
        .setOrigin(0.5);

      this.hudScore = this.add
        .text(GAME_WIDTH * 0.66, y, "0", this._hudStyle(28, "#ffd166"))
        .setOrigin(0.5);
      this.add
        .text(GAME_WIDTH * 0.66, y + 22, "SCORE", this._hudStyle(12, "#b9bee0"))
        .setOrigin(0.5);

      this.hudCombo = this.add
        .text(GAME_WIDTH - padX, y, "x0", this._hudStyle(28, "#06d6a0"))
        .setOrigin(1, 0.5);
      this.add
        .text(GAME_WIDTH - padX, y + 22, "COMBO", this._hudStyle(12, "#b9bee0"))
        .setOrigin(1, 0.5);

      // 구분선
      const line = this.add.graphics();
      line.lineStyle(2, 0x2a2f55, 0.8);
      line.beginPath();
      line.moveTo(20, HUD_TOP_H - 2);
      line.lineTo(GAME_WIDTH - 20, HUD_TOP_H - 2);
      line.strokePath();
    }

    _hudStyle(size, color) {
      return {
        fontFamily: '"Segoe UI", "Noto Sans KR", system-ui, sans-serif',
        fontSize: `${size}px`,
        fontStyle: "bold",
        color: color || "#f1f3ff",
      };
    }

    _refreshHud() {
      this.hudTime.setText(formatMmSs(this.score.getElapsedSeconds()));
      this.hudAttempts.setText(String(this.score.attempts));
      this.hudScore.setText(String(this.score.getCurrentScore()));
      this.hudCombo.setText(`x${this.score.combo}`);
    }

    /* ----------------------------- BOARD ----------------------------- */

    _buildBoard() {
      const { cols, rows, pairs } = this.difficulty;

      // 이모지 풀에서 pairs 개 무작위 추출 → 2배 복제 → 셔플
      const chosen = shuffle(EMOJI_POOL.slice()).slice(0, pairs);
      const deck = shuffle(chosen.concat(chosen));

      // 보드 영역
      const boardTop = HUD_TOP_H + 16;
      const boardBottom = GAME_HEIGHT - HUD_BOTTOM_H - 16;
      const boardLeft = 24;
      const boardRight = GAME_WIDTH - 24;
      const boardW = boardRight - boardLeft;
      const boardH = boardBottom - boardTop;

      const gap = 14;
      const cardW = Math.floor((boardW - gap * (cols - 1)) / cols);
      const cardH = Math.floor((boardH - gap * (rows - 1)) / rows);
      const size = Math.min(cardW, cardH);

      // 실제 그리드 폭/높이 → 가운데 정렬
      const gridW = size * cols + gap * (cols - 1);
      const gridH = size * rows + gap * (rows - 1);
      const originX = boardLeft + (boardW - gridW) / 2 + size / 2;
      const originY = boardTop + (boardH - gridH) / 2 + size / 2;

      for (let r = 0; r < rows; r++) {
        for (let c = 0; c < cols; c++) {
          const idx = r * cols + c;
          const emoji = deck[idx];
          const x = originX + c * (size + gap);
          const y = originY + r * (size + gap);

          const card = CardFactory.createCard(this, {
            x,
            y,
            width: size,
            height: size,
            emoji,
            onClick: (c) => this._onCardClick(c),
          });
          this.cards.push(card);
        }
      }
    }

    _buildBottomBar() {
      const y = GAME_HEIGHT - HUD_BOTTOM_H / 2;

      this._createSmallButton(GAME_WIDTH / 2 - 110, y, 180, 44, "재시작 (R)", () =>
        this._restart()
      );
      this._createSmallButton(GAME_WIDTH / 2 + 110, y, 180, 44, "메뉴 (M)", () =>
        this._toMenu()
      );
    }

    _createSmallButton(x, y, w, h, label, onClick) {
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
          fontSize: "16px",
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
      container.on("pointerover", () => draw(true));
      container.on("pointerout", () => draw(false));
      container.on("pointerdown", onClick);
      return container;
    }

    _bindKeyboard() {
      this.input.keyboard.on("keydown", (e) => {
        if (this.gameOver) return;
        if (e.key === "r" || e.key === "R") this._restart();
        else if (e.key === "m" || e.key === "M") this._toMenu();
        else if (e.key === "s" || e.key === "S") this._toggleSound();
      });
    }

    _toggleSound() {
      const next = !global.MCG.sound.isEnabled();
      global.MCG.sound.setEnabled(next);
      ScoreManager.saveSettings({ soundOn: next });
    }

    /* ----------------------------- LOGIC ----------------------------- */

    _onCardClick(card) {
      if (this.gameOver) return;
      if (this.isLocked) return;
      const st = card.cardState;
      if (st.isRevealed || st.isMatched || st.isAnimating) return;

      // 첫 카드 뒤집을 때 타이머 시작
      this.score.startTimer();
      global.MCG.sound.flip();

      card.flip(true);

      if (!this.firstPick) {
        this.firstPick = card;
        return;
      }

      // 두 번째 카드 선택
      this.secondPick = card;
      this.score.registerAttempt();
      this.isLocked = true;

      // 뒤집기 애니메이션이 끝난 직후 매칭 판정 (약간 여유)
      this.time.delayedCall(TIMING.flipDuration * 2 + 30, () =>
        this._resolveAttempt()
      );
    }

    _resolveAttempt() {
      const a = this.firstPick;
      const b = this.secondPick;
      if (!a || !b) {
        this.isLocked = false;
        return;
      }
      const isMatch = a.cardState.emoji === b.cardState.emoji;
      const result = this.score.applyMatchResult(isMatch);

      if (isMatch) {
        global.MCG.sound.match();
        a.showMatched();
        b.showMatched();
        this._flashHud(result.gained, result.comboBonus);
        this.firstPick = null;
        this.secondPick = null;
        this.isLocked = false;

        if (this.score.matchedPairs >= this.difficulty.pairs) {
          this._completeGame();
        }
      } else {
        global.MCG.sound.mismatch();
        // 800ms 잠금 후 두 카드 다시 뒤집기
        this.time.delayedCall(TIMING.mismatchLockMs, () => {
          a.flip(false);
          b.flip(false);
          this.time.delayedCall(TIMING.flipDuration * 2 + 20, () => {
            this.firstPick = null;
            this.secondPick = null;
            this.isLocked = false;
          });
        });
      }
    }

    /** 점수 변동 시 SCORE HUD 가볍게 펌프 */
    _flashHud(gained, comboBonus) {
      this.tweens.add({
        targets: this.hudScore,
        scale: 1.25,
        duration: 120,
        yoyo: true,
        ease: "Sine.easeOut",
      });
      if (comboBonus > 0) {
        this.tweens.add({
          targets: this.hudCombo,
          scale: 1.3,
          duration: 120,
          yoyo: true,
          ease: "Sine.easeOut",
        });
      }
    }

    _completeGame() {
      this.gameOver = true;
      this.score.stopTimer();
      global.MCG.sound.clear();

      const final = this.score.getFinalScore();
      const elapsedSec = final.breakdown.elapsed;
      const records = ScoreManager.updateBestRecords(
        this.difficulty.key,
        final.total,
        elapsedSec
      );

      // 살짝 여유를 두고 결과 화면 전환
      this.time.delayedCall(800, () => {
        this.scene.start(SCENES.result, {
          difficultyKey: this.difficulty.key,
          finalScore: final.total,
          breakdown: final.breakdown,
          newBestScore: records.newBestScore,
          newBestTime: records.newBestTime,
        });
      });
    }

    _restart() {
      if (this.gameOver) return;
      this.scene.restart({ difficultyKey: this.difficulty.key });
    }

    _toMenu() {
      this.scene.start(SCENES.title);
    }
  }

  /* ----------------------------- helpers ----------------------------- */

  function shuffle(arr) {
    // Fisher-Yates
    for (let i = arr.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [arr[i], arr[j]] = [arr[j], arr[i]];
    }
    return arr;
  }

  function formatMmSs(sec) {
    const m = Math.floor(sec / 60);
    const s = sec % 60;
    return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
  }

  global.MCG.GameScene = GameScene;
})(window);
