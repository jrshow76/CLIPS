/**
 * 전역 네임스페이스: 빌드 도구 없이 <script> 순차 로딩으로 모듈을 공유한다.
 * 이후 모든 파일은 window.MCG 에 자기 자신을 등록한다.
 */
(function (global) {
  "use strict";

  const GAME_WIDTH = 960;
  const GAME_HEIGHT = 720;

  // 이모지 풀 (동물 12 + 과일 12 = 총 24종)
  const EMOJI_POOL = [
    "🐶", "🐱", "🐭", "🐹", "🐰", "🦊",
    "🐻", "🐼", "🐨", "🦁", "🐯", "🐸",
    "🍎", "🍊", "🍋", "🍌", "🍉", "🍇",
    "🍓", "🍒", "🍑", "🥝", "🍍", "🥥",
  ];

  /**
   * 난이도별 보드 구성과 점수 계산용 상수.
   * timeLimit: 시간 보너스 산출 기준 (초)
   * timeCoef: 잔여 시간 × 계수
   */
  const DIFFICULTIES = {
    easy:   { key: "easy",   label: "Easy",   cols: 4, rows: 3, pairs: 6,  timeLimit: 60,  timeCoef: 2 },
    normal: { key: "normal", label: "Normal", cols: 4, rows: 4, pairs: 8,  timeLimit: 100, timeCoef: 3 },
    hard:   { key: "hard",   label: "Hard",   cols: 6, rows: 4, pairs: 12, timeLimit: 180, timeCoef: 5 },
  };

  const SCORE = {
    base: 100,             // 매칭 기본 점수
    comboStep: 50,         // 콤보 보너스 1단계당
    attemptPenalty: 5,     // 초과 시도 1회당 페널티
  };

  const TIMING = {
    flipDuration: 180,     // 카드 뒤집기 한 방향 (ms)
    mismatchLockMs: 800,   // 매칭 실패 후 잠금 시간
    matchedFadeMs: 220,    // 매칭 성공 시 살짝 줄어드는 연출
  };

  const STORAGE_KEYS = {
    bestScore: (diff) => `mcg.bestScore.${diff}`,
    bestTime:  (diff) => `mcg.bestTime.${diff}`,
    settings:  "mcg.settings",
  };

  // 컬러 팔레트 (Phaser 16진 정수)
  const COLORS = {
    bgTop: 0x1a1d2e,
    bgBottom: 0x0f1120,
    cardBack: 0x4361ee,
    cardBackEdge: 0x3a0ca3,
    cardFront: 0xfdf6e3,
    cardFrontEdge: 0xeee8d5,
    cardMatched: 0x06d6a0,
    text: 0xf1f3ff,
    textMuted: 0xb9bee0,
    accent: 0xffd166,
    danger: 0xef476f,
    buttonBg: 0x2a2f55,
    buttonBgHover: 0x3a4180,
  };

  const SCENES = {
    title: "TitleScene",
    game: "GameScene",
    result: "ResultScene",
  };

  global.MCG = global.MCG || {};
  global.MCG.config = {
    GAME_WIDTH,
    GAME_HEIGHT,
    EMOJI_POOL,
    DIFFICULTIES,
    SCORE,
    TIMING,
    STORAGE_KEYS,
    COLORS,
    SCENES,
  };
})(window);
