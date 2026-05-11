# Memory Card Game

Phaser 3 기반 1인용 짝맞추기 카드 게임. 빌드 도구 없이 Vanilla HTML/CSS/JS + CDN 로 동작한다.

## 게임 소개

- 카드를 뒤집어 같은 이모지 쌍을 모두 찾으면 클리어한다.
- 난이도 3종 (Easy 4x3 / Normal 4x4 / Hard 6x4) 지원.
- 시간·시도·콤보 기반 점수 시스템과 난이도별 최고기록(localStorage) 제공.
- 효과음은 외부 파일 없이 Web Audio API 로 합성한다.

## 실행 방법

브라우저의 `file://` 정책으로 일부 기능이 막힐 수 있으므로 간단한 정적 서버를 추천한다.

```bash
# 프로젝트 루트로 이동
cd memory-card-game

# Python 3 내장 서버
python3 -m http.server 8080

# 또는 Node 환경이라면
npx serve .
```

브라우저에서 `http://localhost:8080/` 에 접속한다.

## 조작법

| 입력 | 동작 |
|---|---|
| 마우스 클릭 / 터치 | 카드 뒤집기, 버튼 클릭 |
| `1` / `2` / `3` | 타이틀 화면에서 난이도 선택 (Easy / Normal / Hard) |
| `Enter` / `Space` | 타이틀에서 게임 시작, 결과 화면에서 다시 하기 |
| `R` | 게임 / 결과 화면에서 재시작 |
| `M` / `Esc` | 메뉴(타이틀)로 이동 |
| `S` | 사운드 ON/OFF 토글 |

## 점수 계산

`최종 점수 = (100 × 쌍수) + 콤보보너스 합 - 5 × max(0, 시도-쌍수) + 시간보너스`

- 콤보 보너스: 연속 매칭 성공 시 `+50 × (콤보-1)` 누적, 실패 시 콤보 0 리셋
- 시도 페널티: 이론 최소 시도(=쌍 수) 초과분 1회당 5점 차감
- 시간 보너스: `max(0, (기준시간 - 경과초) × 난이도계수)`
  - Easy 기준 60초 / 계수 2, Normal 100초 / 3, Hard 180초 / 5

자세한 명세는 [`docs/SPEC.md`](docs/SPEC.md) 참고.

## 기술 스택

- Phaser 3.80.1 (CDN)
- Vanilla JS (ES2017+, ES Module 미사용 — `window.MCG` 네임스페이스로 정리)
- HTML5 Canvas / Web Audio API
- localStorage (최고 기록, 마지막 난이도, 사운드 설정 저장)

## 디렉토리 구조

```
memory-card-game/
├── docs/SPEC.md              # 기능 명세서 (SRS)
├── index.html                # Phaser CDN 로드 + 스크립트 진입점
├── css/style.css             # 페이지 레이아웃 / 컨테이너 스타일
├── js/
│   ├── main.js               # Phaser.Game 부팅, 씬 등록
│   ├── config.js             # 난이도, 이모지 풀, 상수, 컬러 팔레트
│   ├── scenes/
│   │   ├── TitleScene.js     # 시작 화면 (난이도 선택, 사운드 토글, 최고기록)
│   │   ├── GameScene.js      # 카드 그리드, HUD, 매칭 로직
│   │   └── ResultScene.js    # 결과 (점수 breakdown, 신기록 배지)
│   └── modules/
│       ├── ScoreManager.js   # 점수/콤보/타이머/localStorage
│       ├── SoundManager.js   # Web Audio 합성 SFX (flip/match/mismatch/clear)
│       └── CardFactory.js    # 카드 Container (Graphics + Text, flip tween)
└── README.md
```

## 구현 메모

- 카드는 `Phaser.GameObjects.Container` 로 합성하며, 뒷면(Graphics) + 앞면(Graphics) + 이모지(Text) 세 레이어로 구성한다.
- 뒤집기 애니메이션은 `scaleX 1 → 0` → 표시 토글 → `0 → 1` 두 단계 tween 으로 처리한다.
- 매칭 실패 시 800ms 동안 `isLocked` 플래그로 입력을 차단하고 자동 복귀한다.
- AudioContext 는 브라우저 자동재생 정책에 맞춰 첫 사용자 입력 이후에 생성한다.
- localStorage 접근은 모두 try/catch 로 감싸 손상 데이터/접근 불가 환경에서도 게임이 진행되도록 한다.

## 라이선스

학습/포트폴리오 목적의 샘플 코드이며, 이모지는 시스템 폰트를 사용한다.
