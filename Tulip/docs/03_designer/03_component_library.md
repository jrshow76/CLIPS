# 공통 컴포넌트 라이브러리 (Component Library)

| 항목 | 내용 |
|---|---|
| 문서명 | Tulip+ 공통 컴포넌트 라이브러리 |
| 문서 ID | DSN-03 |
| 버전 | v0.1 Draft |
| 작성일 | 2026-05-11 |
| 작성자 | Designer Agent |
| 검토자 | PM, Planner, DevLead, FrontendSenior, FrontendDev |
| 상태 | 초안 |

---

## 1. 문서 목적

Atomic Design 원칙에 따라 Tulip+ 컴포넌트를 4계층(Atom/Molecule/Organism/Template)으로 분류하고, 각 컴포넌트의 **용도·props·상태·접근성(a11y) 요건·도서관 도메인 사용처·Backend API 의존성**을 정의한다.

## 2. 분류 체계

```
src/components/
├─ atoms/        — 단일 기능 최소 단위 (Button, Input, Icon ...)
├─ molecules/    — Atom 조합 (FormField, SearchBar, Pagination ...)
├─ organisms/    — 화면 단위 블록 (Table, MarcEditor, SeatMap ...)
├─ templates/    — 페이지 레이아웃 (AdminShell, OPACShell, KioskShell)
└─ patterns/     — 도메인 화면 패턴 (DetailPage, ListPage, EditorPage)
```

---

## 3. Atoms

### 3.1 Button

| 항목 | 내용 |
|---|---|
| 용도 | 행위 트리거 |
| Variants | `primary` / `secondary` / `tertiary` / `ghost` / `danger` / `link` |
| Sizes | `xs(24) / sm(32) / md(40) / lg(48)` |
| States | default / hover / active / focus / disabled / loading |
| Props | `variant, size, leftIcon, rightIcon, loading, disabled, fullWidth, onClick, type, htmlForm` |
| a11y | `aria-busy` when loading, focus ring `shadow-focus`, role=button, 키보드 Enter/Space |
| 사용처 | 모든 액션 |

### 3.2 IconButton

| 용도 | 아이콘 단독 버튼 |
| Props | `icon, size, variant, label(필수, aria-label)` |
| a11y | `aria-label` 필수, tooltip 권장 |

### 3.3 Input

| Variants | `text / email / password / number / tel / search` |
| Sizes | `sm(32) / md(40) / lg(48)` |
| States | default / focus / disabled / readonly / invalid |
| Props | `value, defaultValue, onChange, placeholder, prefix, suffix, error, disabled, readOnly, autoComplete, maxLength` |
| a11y | `<label for>`, `aria-invalid`, `aria-describedby=errorId` |

### 3.4 Textarea
표준 input과 동일한 API + `rows, autoResize`.

### 3.5 Select / Combobox

| Variants | `select(단일)`, `multi-select`, `combobox(검색가능)` |
| Props | `options, value, onChange, placeholder, searchable, clearable, async, loadOptions` |
| a11y | `role=combobox`, `aria-expanded`, `aria-activedescendant`, 키보드 ↑↓ Enter Esc |

### 3.6 Checkbox / Radio / Switch

| Props | `checked, indeterminate, onChange, label, description` |
| a11y | 키보드 Space 토글, `<fieldset><legend>` 라디오 그룹 |

### 3.7 Badge / Tag / Chip

| Variants | `solid / soft / outline` × Semantic 컬러 |
| 용도 | 상태(대출중·연체·예약), 카운트, 태그 필터 |
| 사용처 | 회원 상세(연체 뱃지), 자료 카드(대출가능/불가), 좌석맵(점유/예약/공석) |

### 3.8 Avatar

회원 사진 또는 이니셜. 사이즈 24/32/40/64.

### 3.9 Skeleton

로딩 자리표시. Variants: `text`, `circle`, `rect`. `prefers-reduced-motion` 시 정적.

### 3.10 Divider / Spinner / Tooltip / Icon

표준 Atom. Tooltip은 `delay 300ms`, ESC 닫힘, focus 시 표시.

---

## 4. Molecules

### 4.1 FormField

Input + Label + HelpText + Error를 묶은 표준 폼 필드.

| Props | `label, required, helpText, error, children` |
| a11y | label 클릭 시 포커스, 에러 시 `aria-describedby` 자동 연결 |

### 4.2 SearchBar (with Autocomplete)

| 용도 | OPAC 통합검색, 글로벌 검색(`Ctrl+K`), 회원·서지 검색 |
| Props | `placeholder, value, onSearch, suggestions, onSelect, async, recentItems, scopeOptions` |
| 변형 | `large-hero (OPAC홈)`, `default`, `compact (헤더)`, `command-palette (Cmd+K)` |
| a11y | role=combobox, listbox 키보드 네비, `aria-live=polite` 결과 안내 |
| **API 의존** | `GET /search/suggest` (자동완성), `GET /search` |

### 4.3 Pagination

| Props | `current, total, pageSize, onChange, showSizeChanger, showJumper, mode='page'|'cursor'` |
| 변형 | 페이지번호 / 더보기 버튼(OPAC) / 무한스크롤 / 커서 |
| a11y | `<nav aria-label="페이지">`, 현재 페이지 `aria-current=page` |

### 4.4 DatePicker / DateRangePicker

| Props | `value, onChange, min, max, format, locale='ko', disabledDates, presets` |
| 도메인 | 운영시간, 휴관일, 대출만기, 좌석예약, 통계기간 |
| 변형 | 단일·범위·시간 포함·다중월 |
| a11y | 키보드 화살표, PageUp/Down 월·년 |

### 4.5 FileUpload

| Props | `accept, multiple, maxSize, onUpload, mode='button|dropzone'` |
| 도메인 | 회원 일괄등록(CSV), MARC import, 자료 표지 이미지, 발주서 첨부 |

### 4.6 Stepper

가입·발주·점검 등 다단계 워크플로 표시.

| Props | `steps, current, status, vertical` |
| a11y | `<ol>` 시맨틱, 현재 단계 `aria-current=step` |

### 4.7 Tabs

| Variants | `line / pill / segment / vertical` |
| Props | `items, value, onChange, lazy` |
| a11y | role=tablist/tab/tabpanel, 키보드 화살표, Home/End |

### 4.8 Breadcrumb

| Props | `items: [{label, href}]` |
| a11y | `<nav aria-label="breadcrumb">`, 마지막 `aria-current=page` |

### 4.9 Toast / Snackbar

| Props | `type, title, description, duration, action` |
| a11y | `role=status` (info) / `role=alert` (danger) |
| 사용처 | 저장완료, 대출성공, 오류 |

### 4.10 EmptyState

| Props | `icon, title, description, primaryAction` |
| 사용처 | 검색결과 없음, MyLibrary 대출 없음, 알림 없음 |

### 4.11 KeyValueList

라벨-값 쌍 (회원 상세, 서지 상세, 발주 상세 등).

| Props | `items: [{label, value, copyable?}], columns?` |

---

## 5. Organisms

### 5.1 Table (Data Grid)

사서 시스템의 핵심 컴포넌트.

| 핵심 기능 | 정렬 / 필터 / 페이지네이션 / 컬럼 표시 토글 / 컬럼 폭 조절 / 가로 스크롤 / 행 선택 / 일괄작업 / 인라인 편집 / 엑셀 다운로드 / 가상스크롤 |
| Props | `columns, data, sort, onSortChange, filter, onFilterChange, selection, onSelectionChange, page, onPageChange, rowActions, bulkActions, density='compact|comfortable', editable, virtual, loading, empty` |
| 변형 | `dense-list (관리자 기본)`, `card-grid (OPAC)`, `tree-table (분류표)` |
| a11y | `<table>` 시맨틱, `<th scope>`, `aria-sort`, 키보드 네비, 선택 chk Space |
| **API 의존** | 도메인별 list API (`/members`, `/biblios`, `/items`, `/loans` ...) |
| 사용처 | 회원조회·서지검색·소장조회·대출이력·예약목록·연체·발주 |

### 5.2 MarcEditor (KORMARC 편집기) ★ 핵심

```
┌─────────────────────────────────────────────────────────────────┐
│ Leader: 00000nam a2200000  c 4500   [Leader 편집 모달]          │
├─────────────────────────────────────────────────────────────────┤
│ 태그│인1│인2│ 식별기호                                          │
│─────┼──┼──┼─────────────────────────────────────────────────── │
│ 008 │   │   │ 240511s2024    ulk           kor                   │
│ 020 │   │   │ ▾a 9788956000000 ▾c ₩15000                         │
│ 245 │1  │0  │ ▾a 디자인 시스템 / ▾d 김디자인 지음                │
│ 260 │   │   │ ▾a 서울 : ▾b Tulip+, ▾c 2024                      │
│ 650 │   │8  │ ▾a 디자인 ▾x 시스템 [권위 ✓]                       │
│ ＋필드 추가                                                       │
├─────────────────────────────────────────────────────────────────┤
│ 검증: 필수필드 누락(020 ISBN) ⚠                                  │
└─────────────────────────────────────────────────────────────────┘
```

| Props | `record(KORMARC), schema(필드정의), readOnly, onChange, onValidate, onSave, validation, externalImport` |
| 기능 | 필드 자동완성, 지시기호 도움말, 식별기호 단축키, 권위 자동 매칭, 검증 인라인, 단축키 |
| 단축키 | `F8`=필드추가, `F9`=식별기호추가, `Ctrl+S`=저장, `Ctrl+D`=필드복제, `Ctrl+I`=Z39.50 import |
| a11y | 각 필드 `<fieldset>`, 라벨 명시, 키보드 그리드 네비 |
| **API 의존** | `GET /biblios/{id}` (`/marc`), `PUT /biblios/{id}`, `GET /authorities/search`, `GET /external/z3950` |
| 사용처 | M-CAT-03-02 (KORMARC 편집기), M-CAT-03-04 (KOLIS-NET) |

### 5.3 BookCard

| Variants | `cover-large (OPAC홈)`, `cover-list (검색결과)`, `compact (MyLibrary)`, `shelf (서가브라우즈)` |
| Props | `biblio, cover, holdings, badges, actions, layout` |
| 표시 | 표지, 서명·저자·발행처, 청구기호, 대출가능여부, 예약수 |
| **API 의존** | `GET /biblios/{id}`, `GET /biblios/{id}/holdings` |

### 5.4 BookCoverThumbnail

표지 이미지 + 미존재 시 자동 플레이스홀더(서명·저자 합성).

### 5.5 Modal / Dialog

| Variants | `default / confirm / form / fullscreen` |
| Props | `open, title, size='sm|md|lg|xl|full', onClose, footer, closeOnBackdrop, closeOnEsc` |
| a11y | role=dialog, focus trap, ESC 닫기, 백드롭 클릭 닫기 옵션, 초기 포커스 |

### 5.6 Drawer (Side Sheet)

| Variants | `right / left / bottom (모바일)` |
| 사용처 | 회원 상세 빠른보기, 필터 드로어, 단축키 도움말 |
| a11y | Modal과 동일 |

### 5.7 BarcodeInput

바코드 스캐너(USB HID) 입력 처리. Enter 자동 처리, 디바운스, 회원증·자료 자동 분기.

| Props | `mode='member|item|auto', onScan, autoFocus, autoSubmit, debounceMs=80` |
| a11y | label "바코드 스캔 입력" |
| **API 의존** | `GET /members/by-barcode/{}` / `GET /items/by-barcode/{}` |
| 사용처 | 대출카운터, 자가대출 키오스크 |

### 5.8 RfidPanel

RFID 리더 연동 상태·태그 목록·EAS 제어.

| Props | `device, tags, onTagScan, onEasToggle, mode='loan|return|inventory'` |
| **API 의존** | SIP2 게이트웨이 / `/devices`, `/rfid/encode` |
| 사용처 | 자가대출/반납기, 라벨·RFID 인코딩, 장서점검 |

### 5.9 SeatMap

좌석 평면도. 좌석 클릭 → 예약/이용 시작.

| Props | `floorPlan, seats, selectedId, onSelectSeat, mode='view|admin|reserve', filter` |
| 표시 | 좌석 상태 색상 (공석/예약/이용중/장애), 줌·팬·검색 |
| a11y | 키보드 좌석 탐색, 좌석 상태 라이브 안내 |
| **API 의존** | `GET /seats`, `GET /seats/status`, `POST /seat-reservations` |
| 사용처 | M-FAC-08-01, M-OPC-05-01 |

### 5.10 FacilityCalendar

회의실·세미나실 예약 캘린더 (일/주/월 뷰).

| Props | `resources(시설), events(예약), view, onSelectSlot, onSelectEvent, onCreate` |
| **API 의존** | `GET /facilities/{id}/reservations`, `POST /reservations` |

### 5.11 ShelfBrowser

KDC/DDC 트리 + 청구기호 범위 자료 목록.

| Props | `classificationTree, selectedNode, onSelect, items` |
| **API 의존** | `GET /classifications/{scheme}/tree`, `GET /biblios?callNumber=...` |

### 5.12 FilterPanel

복잡한 검색 결과 필터 (패싯). 카테고리별 접기·다중 선택·검색 가능.

| 사용처 | OPAC 검색결과, 사서 자료조회, 통계 조건 |

### 5.13 NotificationCenter

벨 아이콘 + 드롭다운 + 필터(타입). 읽음·전체 읽음·페이지 이동.

| **API 의존** | `GET /notifications`, `PATCH /notifications/{id}/read` |

### 5.14 GlobalCommandPalette (`Ctrl+K`)

회원·서지·소장·메뉴 통합검색. 최근 액션·즐겨찾기.

| 단축키 | `Ctrl+K` / `Cmd+K` |
| **API 의존** | `GET /search/global` |

### 5.15 BudgetGauge

수서 예산 게이지 (편성/집행/잔액/이월). 차트는 `Recharts`.

### 5.16 OccupancyGauge

재실현황 / 좌석 점유율 실시간 게이지.

### 5.17 StatChart

도메인 차트 컴포넌트 (선/막대/도넛/히트맵). 색상은 Domain Accent 토큰.

---

## 6. Templates / Patterns

### 6.1 AdminShell

```
┌─ Sidebar(240) ─┬─ Header(56) ─────────────────────────────────┐
│                ├─ Breadcrumb ─────────────────────────────────┤
│   GNB 메뉴      │                                              │
│                │              Content                          │
│   1·2 레벨      │              (page-specific)                 │
│                │                                              │
└────────────────┴──────────────────────────────────────────────┘
```

Props: `user, branchContext, navItems, children`.

### 6.2 OPACShell

상단 헤더 + 검색바 노출 영역 + 본문 + 푸터. 모바일 시 하단 탭바 5개.

### 6.3 KioskShell

전체화면, 큰 폰트, 단순 색상, 키보드 미지원 가정 (터치 우선), 비활성 5분 자동 로그아웃.

### 6.4 페이지 패턴 (Patterns)

| 패턴명 | 구성 |
|---|---|
| `ListPage` | 필터바 + 액션바 + Table + Pagination + Drawer(상세) |
| `DetailPage` | Header(타이틀·뱃지·액션) + Tabs(기본/이력/관련) + Content |
| `EditorPage` | Header(저장·임시저장) + 본문(폼/MarcEditor) + 사이드 패널(검증·도움말) |
| `DashboardPage` | KPI 카드 그리드 + 차트 영역 + 알림·최근활동 |
| `WizardPage` | Stepper + Step별 폼 + 이전/다음/완료 |
| `CounterPage` | 좌:회원 패널 / 우:자료 처리 패널 (대출카운터 전용) |

---

## 7. 컴포넌트 → Backend API 의존성 매트릭스 (요약)

| 컴포넌트 | 주요 API |
|---|---|
| Table (회원조회) | `GET /members?...` |
| Table (서지검색) | `GET /biblios?q=...` |
| MarcEditor | `GET/PUT /biblios/{id}/marc`, `GET /authorities` |
| BookCard | `GET /biblios/{id}`, `/holdings` |
| BarcodeInput | `GET /members/by-barcode`, `GET /items/by-barcode` |
| RfidPanel | SIP2 / `/devices`, `/rfid/*` |
| SeatMap | `GET /seats`, `POST /seat-reservations` |
| FacilityCalendar | `GET /facilities/{id}/reservations` |
| NotificationCenter | `GET /notifications` |
| BudgetGauge | `GET /budgets/{year}` |
| GlobalCommandPalette | `GET /search/global` |
| SearchBar | `GET /search/suggest` |
| OccupancyGauge | `GET /access/occupancy/realtime` |

> 위 API 경로는 가설이며 DevLead/BackendSenior의 API 설계서로 확정한다. 본 문서는 컴포넌트가 의존하는 도메인 데이터의 가시화 목적이다.

---

## 8. 컴포넌트 명세 카드 템플릿

신규 컴포넌트는 다음 카드 양식을 따른다.

```
### {ComponentName}
- 분류: Atom|Molecule|Organism|Template
- 용도:
- Variants:
- Sizes:
- States:
- Props:
- 슬롯/Children:
- a11y 요건:
- 키보드 네비:
- 사용처(메뉴 ID):
- API 의존:
- 디자인 토큰 사용:
- 변경 이력:
```

---

## 9. 컴포넌트 개수 요약

| 분류 | 개수 |
|---|---|
| Atoms | 10 (Button, IconButton, Input, Textarea, Select/Combobox, Checkbox/Radio/Switch, Badge/Tag/Chip, Avatar, Skeleton, Divider/Spinner/Tooltip/Icon) |
| Molecules | 11 (FormField, SearchBar, Pagination, DatePicker, FileUpload, Stepper, Tabs, Breadcrumb, Toast, EmptyState, KeyValueList) |
| Organisms | 17 (Table, MarcEditor, BookCard, BookCoverThumbnail, Modal, Drawer, BarcodeInput, RfidPanel, SeatMap, FacilityCalendar, ShelfBrowser, FilterPanel, NotificationCenter, GlobalCommandPalette, BudgetGauge, OccupancyGauge, StatChart) |
| Templates | 3 (AdminShell, OPACShell, KioskShell) |
| Patterns | 6 (ListPage, DetailPage, EditorPage, DashboardPage, WizardPage, CounterPage) |
| **총계** | **47** |

---

## 10. 후속 작업

| 작업 | 담당 |
|---|---|
| Figma 컴포넌트 라이브러리 구축 | Designer |
| 디자인 토큰 코드 export | Designer → FrontendSenior |
| 스토리북 구성 | FrontendSenior |
| 컴포넌트별 단위 a11y 테스트 | FrontendSenior + QA |
