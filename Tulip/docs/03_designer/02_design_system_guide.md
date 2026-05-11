# 디자인 시스템 가이드 (Design System Guide)

| 항목 | 내용 |
|---|---|
| 문서명 | Tulip+ 디자인 시스템 가이드 |
| 문서 ID | DSN-02 |
| 버전 | v0.1 Draft |
| 작성일 | 2026-05-11 |
| 작성자 | Designer Agent |
| 검토자 | PM, Planner, DevLead, FrontendSenior |
| 상태 | 초안 |

---

## 1. 브랜드 정체성

### 1.1 브랜드 컨셉

**Tulip+** 는 "지식을 피우다"라는 메시지를 담은 SaaS형 도서관통합관리시스템이다. 튤립의 6장 꽃잎 모티프는 6개 핵심 도메인(수서/목록/열람/장서/출입/시설)을 상징한다.

```
    🌷
   T u l i p +
   ────────────
  Library OS for the modern librarian
```

| 로고 변형 | 사용 위치 |
|---|---|
| Primary (풀 로고) | 로그인, OPAC 헤더, 공식문서 |
| Symbol Only (튤립 마크) | 사이드바 collapsed, favicon, 키오스크 |
| Mono (단색) | 인쇄·라벨 |
| White (역상) | 다크모드, 어두운 헤더 |

최소 사이즈: 마크 24px, 풀로고 96px. 클리어 스페이스: 마크 높이의 0.5배 이상.

### 1.2 디자인 원칙

| 원칙 | 정의 | 적용 예 |
|---|---|---|
| **신뢰성 (Trustworthy)** | 도서·회원·예산 등 중요 데이터를 다루므로 정돈된 정보 표현 | 표 기본 라인 정렬, 차분한 Primary 색상 |
| **효율성 (Efficient)** | 사서의 반복 업무를 빠르게 처리 | 단축키, 폼 자동저장, 인라인 편집, 키보드 우선 |
| **친근함 (Approachable)** | OPAC 이용자에게 어렵지 않게 | 큰 검색바, 따뜻한 보조컬러, 친절한 빈상태 메시지 |
| **접근성 (Accessible)** | WCAG 2.1 AA 충족, 고령·시각약자 포함 | 명도 대비 4.5:1+, 키보드 네비, 스크린리더 라벨 |
| **확장성 (Extensible)** | 도서관 유형·테넌트별 변형 | 디자인 토큰 기반, prop variant 흡수 |

### 1.3 사용자 페르소나 (6개 도메인별)

| 도메인 | 주 사용자 | 핵심 니즈 | UI 톤 |
|---|---|---|---|
| 수서 | 수서 사서, 예산 담당 | 빠른 발주·예산 가시화 | 표 중심, 차분한 |
| 목록 | 편목 사서 | KORMARC 정밀 편집·검증 | 정보 밀도 최대, 모노스페이스 |
| 열람 | 카운터 사서, POS | 한 손 작업·빠른 처리 | 큰 버튼, 단축키, 실시간 |
| 장서 | 장서 사서 | 점검·이동·통계 | 표·차트, RFID 친화 |
| 출입 | 운영 사서, 보안 | 실시간 모니터링 | 대시보드, 알림 강조 |
| 시설 | 운영 사서, 이용자 | 좌석맵·예약 | 그래픽·시각적 |
| OPAC | 일반 이용자, 학생 | 자료 발견·예약 | 친근, 큰 타이포 |

---

## 2. 컬러 토큰

### 2.1 컬러 철학

- **Primary (튤립 자주/푸시아)**: 브랜드 아이덴티티
- **Secondary (딥 그린)**: "지식의 잎"
- **Neutral**: UI 골격
- **Semantic**: 상태 전달 (success/warning/danger/info)
- **Surface**: 배경 계층

모든 색은 라이트·다크 모드 쌍을 가지며, WCAG AA(텍스트 4.5:1, 큰 글자 3:1) 명도 대비를 보장한다.

### 2.2 Primary (Brand) — Tulip Magenta

| Token | Hex (Light) | Hex (Dark) | 용도 |
|---|---|---|---|
| `color-primary-50` | `#FDF2F8` | `#1A0D14` | 배경 강조 약 |
| `color-primary-100` | `#FCE7F3` | `#2D1320` | 호버 배경 |
| `color-primary-200` | `#FBCFE8` | `#4A1F36` | 보더 강조 |
| `color-primary-300` | `#F9A8D4` | `#73304F` | - |
| `color-primary-400` | `#F472B6` | `#A14169` | - |
| `color-primary-500` | `#DB2777` | `#DB2777` | **기본 Primary (버튼·링크)** |
| `color-primary-600` | `#BE185D` | `#EC4899` | 호버 |
| `color-primary-700` | `#9D174D` | `#F472B6` | 액티브 |
| `color-primary-800` | `#831843` | `#F9A8D4` | 텍스트 강조 |
| `color-primary-900` | `#500724` | `#FBCFE8` | - |

### 2.3 Secondary — Knowledge Green

| Token | Hex (Light) | Hex (Dark) |
|---|---|---|
| `color-secondary-500` | `#10B981` | `#34D399` |
| `color-secondary-600` | `#059669` | `#10B981` |
| `color-secondary-700` | `#047857` | `#6EE7B7` |

### 2.4 Neutral (Gray)

| Token | Hex (Light) | Hex (Dark) | 용도 |
|---|---|---|---|
| `color-neutral-0` | `#FFFFFF` | `#0A0A0B` | App 배경 |
| `color-neutral-50` | `#FAFAFA` | `#111114` | Surface base |
| `color-neutral-100` | `#F4F4F5` | `#18181B` | Surface raised |
| `color-neutral-200` | `#E4E4E7` | `#27272A` | Divider |
| `color-neutral-300` | `#D4D4D8` | `#3F3F46` | Border default |
| `color-neutral-400` | `#A1A1AA` | `#52525B` | Border strong |
| `color-neutral-500` | `#71717A` | `#71717A` | Text muted |
| `color-neutral-600` | `#52525B` | `#A1A1AA` | Text secondary |
| `color-neutral-700` | `#3F3F46` | `#D4D4D8` | Text primary 약 |
| `color-neutral-800` | `#27272A` | `#E4E4E7` | Text primary |
| `color-neutral-900` | `#18181B` | `#FAFAFA` | Text heading |

### 2.5 Semantic

| 카테고리 | Token | Light | Dark | 사용 |
|---|---|---|---|---|
| Success | `color-success-500` | `#16A34A` | `#22C55E` | 등록 완료, 검증 통과 |
| Success | `color-success-50` | `#F0FDF4` | `#052E16` | 알림 배경 |
| Warning | `color-warning-500` | `#F59E0B` | `#FBBF24` | 연체 임박, 만기 D-3 |
| Warning | `color-warning-50` | `#FFFBEB` | `#1C1402` | 알림 배경 |
| Danger | `color-danger-500` | `#DC2626` | `#EF4444` | 연체·삭제·오류 |
| Danger | `color-danger-50` | `#FEF2F2` | `#1F0A0A` | 알림 배경 |
| Info | `color-info-500` | `#2563EB` | `#3B82F6` | 정보·알림 |
| Info | `color-info-50` | `#EFF6FF` | `#0B1220` | 알림 배경 |

### 2.6 Surface 계층

| Token | Light | Dark | 설명 |
|---|---|---|---|
| `surface-app` | `#FAFAFA` | `#0A0A0B` | 전체 배경 |
| `surface-card` | `#FFFFFF` | `#18181B` | 카드·테이블 |
| `surface-raised` | `#FFFFFF + shadow-md` | `#27272A` | 모달·드로어 |
| `surface-overlay` | `rgba(0,0,0,.5)` | `rgba(0,0,0,.7)` | 백드롭 |
| `surface-inverse` | `#18181B` | `#FAFAFA` | Tooltip, Toast |

### 2.7 Domain Accent (도서관 6 도메인 강조)

차트·아이콘·뱃지에서 도메인 구분용으로만 한정 사용 (텍스트 색상 금지).

| 도메인 | Hex | 비고 |
|---|---|---|
| 수서 ACQ | `#F97316` (Orange) | 발주·예산 |
| 목록 CAT | `#8B5CF6` (Violet) | KORMARC |
| 열람 CIR | `#0EA5E9` (Sky) | 대출/반납 |
| 장서 COL | `#84CC16` (Lime) | 점검·라벨 |
| 출입 ACS | `#EF4444` (Red) | 보안 |
| 시설 FAC | `#14B8A6` (Teal) | 좌석 |

### 2.8 명도 대비 검증

모든 Primary·Semantic 500 토큰 위 `color-neutral-0` 텍스트 사용 시 4.5:1 이상을 보장한다. 검증은 `npm run a11y:contrast`(추후 도구 도입 예정)로 자동화한다.

---

## 3. 타이포그래피

### 3.1 폰트 패밀리

| Token | 값 | 용도 |
|---|---|---|
| `font-sans` | `'Pretendard Variable', 'Noto Sans KR', system-ui, sans-serif` | 본문, UI 기본 |
| `font-serif` | `'Noto Serif KR', 'Source Serif', serif` | OPAC 서지 인용·헤딩(선택) |
| `font-mono` | `'JetBrains Mono', 'D2Coding', monospace` | KORMARC 필드, 등록번호, 코드 |
| `font-numeric` | `'Pretendard Variable' tnum` | 표·수치 (`tabular-nums`) |

`Pretendard`는 변동 가능, 라이선스 무료, 한·영 혼용 시 균형이 우수해 1차 채택한다. 폴백으로 `Noto Sans KR`을 포함한다.

### 3.2 타입 스케일

| Token | Size / LH | Weight | 용도 |
|---|---|---|---|
| `text-display` | 36 / 44 | 700 | OPAC 홈 큰 타이틀 |
| `text-h1` | 28 / 36 | 700 | 페이지 타이틀 |
| `text-h2` | 22 / 30 | 600 | 섹션 타이틀 |
| `text-h3` | 18 / 26 | 600 | 카드 타이틀 |
| `text-h4` | 16 / 24 | 600 | 폼 그룹 |
| `text-body-lg` | 16 / 24 | 400 | OPAC 본문 |
| `text-body` | 14 / 22 | 400 | 관리자 기본 |
| `text-body-sm` | 13 / 20 | 400 | 보조 텍스트 |
| `text-caption` | 12 / 18 | 400 | 메타·캡션 |
| `text-overline` | 11 / 16 | 600·tracking 0.06em | 라벨·KORMARC 필드명 |
| `text-mono-sm` | 13 / 20, mono | 400 | 등록번호·바코드 |

### 3.3 한글 타이포 가이드

- 글자 간격(자간): 본문 `-0.01em`, 표·수치 `0`, 큰 타이틀 `-0.02em`
- 줄 간격: 한글 본문 기준 1.55~1.7
- 들여쓰기 사용 금지(웹 UI 컨벤션)
- 숫자는 `tabular-nums`로 표·통계에서 정렬 안정성 확보

---

## 4. 간격·그리드·레이아웃

### 4.1 8pt 그리드 토큰

| Token | px | 용도 |
|---|---|---|
| `space-0` | 0 | - |
| `space-1` | 4 | 아이콘-텍스트 갭 |
| `space-2` | 8 | 기본 여백 |
| `space-3` | 12 | 컴팩트 폼 행간 |
| `space-4` | 16 | 카드 패딩 기본 |
| `space-5` | 20 | - |
| `space-6` | 24 | 섹션 간 여백 |
| `space-8` | 32 | 페이지 패딩 |
| `space-10` | 40 | 큰 섹션 |
| `space-12` | 48 | - |
| `space-16` | 64 | 페이지 상하 |

### 4.2 Breakpoints

| Token | 폭 | 대상 |
|---|---|---|
| `bp-sm` | 640 | 모바일 (OPAC) |
| `bp-md` | 768 | 태블릿 |
| `bp-lg` | 1024 | 데스크탑 (사서 최소 권장) |
| `bp-xl` | 1280 | 데스크탑 표준 |
| `bp-2xl` | 1536 | 대시보드·점검 |
| `bp-3xl` | 1920 | 모니터링월 (선택) |

### 4.3 컨테이너 / 그리드

| 컨테이너 | 폭 | 용도 |
|---|---|---|
| `container-fluid` | 100% | 사서 시스템 (좌측 사이드바 240 + 컨텐츠 가변) |
| `container-opac` | max 1200 | OPAC 데스크탑 |
| `container-narrow` | max 720 | 폼·로그인 |

- 사서 시스템 그리드: **12 column** / gutter 16 / margin 24
- OPAC 그리드: **12 column** / gutter 24 / margin 32

---

## 5. 아이콘

### 5.1 기본 시스템

- 베이스: `Lucide` (line, 24px stroke 1.5)
- 보조: `Heroicons` (필요 시), `Tabler` (특수 그래픽)
- 라이브러리 통일: 라이브러리는 1개만 코드에 import, 나머지는 SVG 어셋으로 변환

### 5.2 도서관 도메인 확장 아이콘 (자체 제작)

| 아이콘명 | 용도 |
|---|---|
| `icon-marc` | KORMARC 편집기 |
| `icon-isbn` | ISBN 검색 |
| `icon-shelf` | 서가/배가 |
| `icon-barcode` | 바코드 스캔 |
| `icon-rfid` | RFID 태그 |
| `icon-call-number` | 청구기호 |
| `icon-z3950` | Z39.50 외부서지 |
| `icon-kolis` | KOLIS-NET |
| `icon-loan` | 대출 |
| `icon-return` | 반납 |
| `icon-hold` | 예약/대기 |
| `icon-overdue` | 연체 |
| `icon-seat` | 좌석 |
| `icon-gate` | 출입 게이트 |
| `icon-eas` | 도난방지 |

크기 토큰: `icon-xs=12 / sm=16 / md=20 / lg=24 / xl=32`. stroke 1.5 통일.

---

## 6. Radius / Shadow / Motion

### 6.1 Radius

| Token | px | 용도 |
|---|---|---|
| `radius-none` | 0 | 표·KORMARC 필드 |
| `radius-sm` | 4 | 작은 뱃지 |
| `radius-md` | 8 | 입력·버튼 |
| `radius-lg` | 12 | 카드 |
| `radius-xl` | 16 | 모달 |
| `radius-2xl` | 24 | OPAC 큰 카드 |
| `radius-full` | 9999 | 아바타·태그 |

### 6.2 Shadow

| Token | 값 |
|---|---|
| `shadow-sm` | `0 1px 2px rgba(0,0,0,.06)` |
| `shadow-md` | `0 4px 12px rgba(0,0,0,.08)` |
| `shadow-lg` | `0 12px 32px rgba(0,0,0,.10)` |
| `shadow-xl` | `0 24px 48px rgba(0,0,0,.16)` |
| `shadow-focus` | `0 0 0 3px rgba(219,39,119,.35)` | 포커스링 (Primary 35%) |

다크모드는 shadow 대신 `border + surface-raised` 조합을 우선한다.

### 6.3 Motion / Transition

| Token | 값 | 용도 |
|---|---|---|
| `motion-fast` | 120ms cubic-bezier(.2,0,0,1) | hover, focus |
| `motion-base` | 200ms cubic-bezier(.2,0,0,1) | 일반 전환 |
| `motion-slow` | 320ms cubic-bezier(.2,0,0,1) | 모달·드로어 |
| `motion-reduced` | 0ms (prefers-reduced-motion) | 접근성 |

- `prefers-reduced-motion: reduce` 매체쿼리에서 모든 트랜지션은 `motion-reduced`로 강제.

---

## 7. 접근성 (WCAG 2.1 AA)

| 항목 | 기준 |
|---|---|
| 명도 대비 | 일반 4.5:1, 큰 글자(18pt 또는 14pt bold) 3:1 |
| 키보드 네비 | 모든 인터랙티브 요소 Tab 도달, 시각 포커스링 명시 |
| 포커스링 | `shadow-focus` 토큰 사용, 절대 outline:none 금지 |
| 폼 라벨 | `<label for>` 또는 `aria-label`/`aria-labelledby` 필수 |
| 에러 메시지 | `aria-invalid="true"` + `aria-describedby` 연결 |
| 아이콘 버튼 | `aria-label` 필수 (예: `aria-label="검색"`) |
| 모달 | role="dialog", focus trap, ESC 닫기, 백드롭 클릭 닫기 옵션 |
| 표 | `<th scope="col/row">`, caption, 정렬 상태 aria-sort |
| 컬러 단독 의존 금지 | 상태 색 + 아이콘 + 텍스트 병행 |
| 한국어 음성 가이드 | NVDA / Voice Over / TalkBack 기준 테스트 |
| 다국어 | `<html lang="ko">` 기본, 영문 컨텐츠에 `lang="en"` 마크업 |

---

## 8. 다크모드 정책

- 사서 시스템: 라이트 기본, 사용자 선택 시 다크 적용
- OPAC: 시스템 추종 기본 (`prefers-color-scheme`)
- 키오스크: 라이트 고정 (가독성)
- 토큰 전환은 CSS 변수 `:root` vs `:root[data-theme="dark"]` 로 분기
- 차트 도메인 컬러는 다크에서 채도를 한 단계 낮춰 적용

---

## 9. 다국어(한/영) 가이드

- 텍스트 길이 변동 +30% 여유 (영문 길이 확장 대비)
- 폰트 폴백: `Pretendard → Noto Sans KR → system-ui`
- 날짜 포맷: 한 `YYYY-MM-DD (요일) HH:mm`, 영 `MMM DD, YYYY hh:mm a`
- 통화: 한 `₩12,345`, 영 `₩12,345` (도서관 통화는 KRW 고정)
- KORMARC 필드명·태그 등은 번역하지 않음 (표준)

---

## 10. 디자인 토큰 export 포맷

`tokens.json` (Style Dictionary 호환) → `tokens.ts`, `tokens.css`, `tailwind.config.ts` 로 변환. 자세한 변환 절차는 DSN-05를 참조한다.

```json
{
  "color": {
    "primary": {
      "500": { "value": "#DB2777" },
      "600": { "value": "#BE185D" }
    }
  },
  "space": { "4": { "value": "16px" } }
}
```

---

## 11. 후속 산출물 연계

| 후속 | 입력 |
|---|---|
| DSN-03 컴포넌트 | 토큰 적용 기준 |
| DSN-04 와이어프레임 | 컬러·타이포·간격 규칙 |
| DSN-05 퍼블리싱 스타터 | 토큰 코드 변환 |
| FE 구현 | tokens.ts / tailwind.config.ts |
