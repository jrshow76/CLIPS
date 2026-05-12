# TradePilot 디자인 가이드

> 문서 ID: DESIGN_README
> 버전: v1.0
> 작성자: Designer
> 최종 수정일: 2026-05-12

TradePilot의 디자인 시스템, 화면 인벤토리, HTML/CSS 퍼블리싱 산출물을 보관하는 디렉토리이다. 본 산출물은 FrontendSenior가 Next.js + Tailwind 환경에서 React 컴포넌트로 변환하는 기반이 된다.

---

## 1. 디자인 컨셉

| 항목 | 내용 |
|---|---|
| 톤 | 전문 트레이딩 도구. 명료하고 데이터 밀도가 높다 |
| 기본 테마 | 다크 모드(시인성, 야간 매매 편의), 라이트 모드 토글 지원 |
| 등락 색 | 상승 = 빨강 `#ef4444`, 하락 = 파랑 `#3b82f6` (국내 증권 관습) |
| 강조 색 | 브랜드 인디고 `#2f5cff` |
| 폰트 | Pretendard (없으면 시스템 sans-serif), 숫자는 tabular-nums |
| 모드 배지 | SIM 파랑, LIVE 빨강 (모드 전환은 안전 흐름 필수) |

---

## 2. 디렉토리 구조

```
design/
├── README.md                  ← 본 문서
├── 40_design_system.md        ← 디자인 시스템 (토큰/타이포/간격/반응형)
├── 41_screen_inventory.md     ← 화면 인벤토리 (36개 화면 와이어 설명)
├── 42_component_catalog.md    ← 컴포넌트 카탈로그
├── preview.html               ← 퍼블리싱 결과 인덱스
├── tokens/
│   └── tokens.css             ← CSS 변수(:root, [data-theme="light"])
├── styles/
│   ├── base.css               ← 리셋 + 타이포 + 레이아웃 유틸리티
│   └── components.css         ← BEM 컴포넌트 스타일
└── pages/
    ├── _shared/
    │   ├── header.html        ← 공통 헤더 마크업 파셜
    │   └── sidebar.html       ← 공통 사이드바 마크업 파셜
    ├── login.html
    ├── dashboard.html
    ├── recommendations.html
    ├── chart-analysis.html
    ├── sector-analysis.html
    ├── signals.html
    ├── auto-trading.html
    ├── profit-report.html
    ├── backtest.html
    └── settings.html
```

---

## 3. 사용 방법

### 3.1 정적 미리보기
모든 페이지는 `design/preview.html`에서 링크로 접근 가능하다. 로컬에서 다음과 같이 띄울 수 있다.

```bash
cd /home/user/CLIPS/TradePilot/design
python3 -m http.server 8080
# http://localhost:8080/preview.html
```

### 3.2 CSS 로딩 순서
페이지에서는 항상 다음 순서로 로드한다.

```html
<link rel="stylesheet" href="../tokens/tokens.css">
<link rel="stylesheet" href="../styles/base.css">
<link rel="stylesheet" href="../styles/components.css">
```

### 3.3 테마 토글
`<html data-theme="dark">` 또는 `data-theme="light"`. 기본값은 다크.
```html
<html lang="ko" data-theme="dark">
```

### 3.4 React 변환 가이드 (FrontendSenior 인계)
- 각 BEM 클래스는 Tailwind `@apply` 또는 컴포넌트 파일로 1:1 매핑 가능.
- `--color-*` 토큰은 `tailwind.config`의 `theme.extend.colors`에 반영.
- 차트 자리표시(`.chart-placeholder`)는 추후 lightweight-charts/Recharts로 대체.
- 아이콘은 lucide-react 사용 권장(현재 마크업은 텍스트 대체).

---

## 4. 협업 인계 사항

| 인계 대상 | 인계 내용 |
|---|---|
| FrontendSenior | 컴포넌트화 기준이 되는 CSS/HTML, 디자인 토큰 변환 가이드 |
| FrontendDev | 페이지별 마크업 구조 보존, API 연동 위치 |
| QA | 빈/로딩/에러 상태 처리 기준, 다크/라이트 양 모드 회귀 |
| DevLead | 다크 모드 기본 정책, 모드 배지 표기 규칙 |

---

## 5. 변경 이력
| 버전 | 일자 | 작성자 | 내용 |
|---|---|---|---|
| v1.0 | 2026-05-12 | Designer | 디자인 시스템 v1, 36개 화면 마크업 초안 |
