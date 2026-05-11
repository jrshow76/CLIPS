/**
 * main.js — Phaser.Game 부팅 엔트리.
 * - DOM 의 #game-container 에 캔버스를 부착한다.
 * - 씬 등록 순서: Title → Game → Result (Title 부터 시작)
 */
(function (global) {
  "use strict";

  const { GAME_WIDTH, GAME_HEIGHT } = global.MCG.config;
  const { TitleScene, GameScene, ResultScene } = global.MCG;

  window.addEventListener("load", () => {
    const config = {
      type: Phaser.AUTO,
      parent: "game-container",
      width: GAME_WIDTH,
      height: GAME_HEIGHT,
      backgroundColor: "#1a1d2e",
      scale: {
        // 캔버스를 컨테이너에 맞춰 종횡비 유지 스케일
        mode: Phaser.Scale.FIT,
        autoCenter: Phaser.Scale.CENTER_BOTH,
        width: GAME_WIDTH,
        height: GAME_HEIGHT,
      },
      render: {
        antialias: true,
        pixelArt: false,
      },
      scene: [TitleScene, GameScene, ResultScene],
    };

    global.MCG.game = new Phaser.Game(config);
  });
})(window);
