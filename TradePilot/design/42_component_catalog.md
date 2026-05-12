# TradePilot 컴포넌트 카탈로그

> 문서 ID: 42_COMPONENT_CATALOG
> 버전: v1.0
> 작성자: Designer
> 최종 수정일: 2026-05-12

본 문서는 `styles/components.css`에 정의된 모든 BEM 컴포넌트의 사용법, 변형(modifier), 상태, React 변환 가이드를 정리한다. Atomic Design 분류(Atom/Molecule/Organism/Template)를 함께 표기한다.

---

## 1. 컴포넌트 인덱스

| 분류 | 이름 | 클래스 | 비고 |
|---|---|---|---|
| Atom | Button | `.btn` | primary/danger/success/ghost/outline, sm/lg/icon/block |
| Atom | Input | `.input` | error 변형 |
| Atom | Select | `.select` | - |
| Atom | Textarea | `.textarea` | - |
| Atom | Switch | `.switch` | `--on` |
| Atom | Checkbox | `.checkbox` | `--checked` |
| Atom | Badge | `.badge` | up/down/success/warning/danger/info/sim/live |
| Atom | Kbd | `.kbd` | 단축키 표시 |
| Atom | Avatar | `.avatar` | 이니셜 표시 |
| Atom | Progress | `.progress` | success/danger 변형 |
| Atom | Sparkline | `.sparkline` | placeholder |
| Molecule | Field | `.field` | label/hint/error 조합 |
| Molecule | InputGroup | `.input-group` | 아이콘 prefix |
| Molecule | StatRow | `.stat-row` | label/value 한 줄 |
| Molecule | KPI | `.kpi` | label/value/delta |
| Molecule | Tabs | `.tabs` | 활성 인디케이터 |
| Molecule | PillTabs | `.pill-tabs` | 라운드형 토글 그룹 |
| Molecule | FilterBar | `.filter-bar` | 인풋 + select 컨테이너 |
| Molecule | StockRow | `.stock-row` | 종목 한 줄 |
| Molecule | ModeToggle | `.mode-toggle` | SIM/LIVE |
| Molecule | Toast | `.toast` | success/warning/danger |
| Molecule | Banner | `.banner` | live/warning/info |
| Organism | Card | `.card` | header/body/footer, compact/ghost |
| Organism | Table | `.table` | compact, 정렬 헤더 |
| Organism | Modal | `.modal` | sm/lg/xl/danger |
| Organism | EmptyState | `.empty-state` | icon/title/desc/action |
| Organism | ErrorCard | `.error-card` | 부분 장애 |
| Organism | Pager | `.pager` | 페이지네이션 |
| Organism | AppSidebar | `.app-sidebar` | 좌측 GNB |
| Organism | AppHeader | `.app-header` | 상단 헤더 |
| Organism | Heatmap | `.heatmap` | 섹터 |
| Template | AppShell | `.app-shell` | 사이드바 + 헤더 + 메인 그리드 |
| Placeholder | Chart | `.chart-placeholder` | 차트/지표 자리 |
| Atom | Skeleton | `.skeleton` | 로딩 자리 |

---

## 2. Button `.btn`

### 변형
| 모디파이어 | 용도 |
|---|---|
| `.btn--primary` | 기본 CTA (브랜드 인디고) |
| `.btn--danger` | 비상정지, 청산, LIVE 전환 확인 |
| `.btn--success`| 성공/활성화 |
| `.btn--ghost` | 보더/배경 없음 (보조 액션) |
| `.btn--outline`| 외곽선 강조 |
| `.btn--sm` / `.btn--lg` | 크기 |
| `.btn--icon` | 정사각 아이콘 버튼 |
| `.btn--block` | 폭 100% |

### 상태
- `:hover`, `:active`, `disabled`(`aria-disabled="true"`)
- 로딩: 텍스트를 스피너 SVG로 교체(React에서 처리)

### React 매핑
```tsx
<Button variant="primary" size="md" disabled>주문하기</Button>
```

---

## 3. Input / Field

```html
<div class="field">
  <label class="field__label">이메일</label>
  <input class="input" placeholder="you@trade.com">
  <span class="field__hint">로그인 시 사용됩니다</span>
</div>
```
- 에러: `.input--has-error` + `.field__error`
- 아이콘 prefix: `.input-group` + `.input--prefix-pad`

---

## 4. Badge

| 클래스 | 색 |
|---|---|
| `.badge--up`   | 상승(빨강) |
| `.badge--down` | 하락(파랑) |
| `.badge--sim`  | 시뮬레이션 |
| `.badge--live` | 실거래 |
| `.badge--warning` | 지연/주의 |
| `.badge--danger`  | 위험 |

`.badge-dot::before`로 좌측에 작은 점 표기.

---

## 5. Card

```html
<section class="card">
  <header class="card__header">
    <h3 class="card__title">보유 종목</h3>
    <button class="btn btn--sm btn--ghost">더보기 →</button>
  </header>
  <div class="card__body">...</div>
  <footer class="card__footer">...</footer>
</section>
```
- KPI는 `.card__body` 내부에 `.kpi`로 작성.
- `.card--ghost`는 빈 상태/플레이스홀더.

---

## 6. Table

```html
<div class="table-wrap">
  <div class="table-scroll">
    <table class="table">
      <thead><tr><th>종목</th><th class="num">가격</th></tr></thead>
      <tbody>
        <tr><td>삼성전자</td><td class="num text-up">82,500 ▲ 1.20%</td></tr>
      </tbody>
    </table>
  </div>
  <nav class="pager">...</nav>
</div>
```
- 모바일에서는 `.table-scroll`이 가로 스크롤. 추천주 페이지는 대안으로 카드 리스트 전환.

---

## 7. Modal

```html
<div class="modal-mask" role="dialog" aria-modal="true">
  <div class="modal modal--danger">
    <header class="modal__header">
      <h3 class="modal__title">실거래 전환</h3>
      <button class="btn btn--ghost btn--icon" aria-label="닫기">✕</button>
    </header>
    <div class="modal__body">...</div>
    <footer class="modal__footer">
      <button class="btn btn--ghost">취소</button>
      <button class="btn btn--danger">전환</button>
    </footer>
  </div>
</div>
```
- `modal--danger`는 상단 4px 빨강 라인. LIVE 전환·비상정지·강제 청산에 사용.

---

## 8. Tabs / PillTabs

- `.tabs` : 페이지 내 섹션 전환 (활성 항목은 하단 인디케이터).
- `.pill-tabs` : 그래프 주기 선택 등 토글 그룹.

---

## 9. Toast & Banner

- 토스트: `.toast-region` 컨테이너에 `.toast` n개 (success/warning/danger).
- 배너: 페이지 상단에 `.banner banner--live`로 LIVE 모드 노출, `.banner banner--warning`로 시세 지연/장 종료.

---

## 10. EmptyState / ErrorCard / Skeleton

```html
<div class="empty-state">
  <div class="empty-state__icon">★</div>
  <p class="empty-state__title">아직 보유 종목이 없습니다</p>
  <p class="empty-state__desc">추천주에서 시뮬 매수로 시작해보세요</p>
  <a class="btn btn--primary empty-state__action" href="recommendations.html">추천주 보기</a>
</div>
```
- 에러: `.error-card`는 부분 장애용. 전체 페이지 오류는 별도 `S-ERR-500` 화면 적용.
- 로딩: `.skeleton`을 카드 본문/표 행에 배치.

---

## 11. AppShell / Header / Sidebar

- `app-shell`: `grid-template-areas`로 sidebar / header / main 영역 정의.
- 1024px 이하: 사이드바 폭 64px로 축소.
- 768px 이하: 사이드바 숨김, 헤더 햄버거 메뉴로 드로어 호출.

```html
<div class="app-shell">
  <aside class="app-sidebar">...</aside>
  <header class="app-header">...</header>
  <main class="app-shell__main">...</main>
</div>
```

---

## 12. ModeToggle (SIM / LIVE)

```html
<div class="mode-toggle">
  <span class="mode-toggle__item mode-toggle__item--sim is-active">SIM</span>
  <span class="mode-toggle__item mode-toggle__item--live">LIVE</span>
</div>
```
- LIVE 활성 시 빨강. 클릭 시 `MD-001` 모달 트리거.

---

## 13. ChartPlaceholder / Heatmap

- `.chart-placeholder` : 격자 배경 + 가운데 라벨. 사이즈 변형 sm/lg.
- `.heatmap` : 섹터 상관/등락률 매트릭스. 셀 단계 6종(`--up-1/2/3`, `--down-1/2/3`).

---

## 14. 상태 매트릭스 (요약)

| 컴포넌트 | hover | active | disabled | loading | empty | error |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| Button | O | O | O | O(스피너) | - | - |
| Input  | O | O(focus) | O | O(우측 스피너) | - | O |
| Card   | - | - | - | O(skeleton) | O(empty-state) | O(error-card) |
| Table  | O(행) | - | - | O(skeleton 행) | O | O |
| Modal  | - | - | - | O | - | O |

---

## 15. React 변환 체크리스트

- 클래스명 그대로 `className`에 매핑(짧은 이름이면 컴포넌트 props로 추상화).
- `--color-*` 토큰은 Tailwind `theme.extend.colors`로 동기화.
- 상태 모디파이어(`--checked`, `is-active`)는 props/state 기반으로 토글.
- 모달은 React Portal로 `#modal-root`에 마운트.
- 차트 placeholder는 lightweight-charts/Recharts 인스턴스로 교체. 색 토큰을 차트 옵션에 주입.

---

## 16. 변경 이력
| 버전 | 일자 | 작성자 | 내용 |
|---|---|---|---|
| v1.0 | 2026-05-12 | Designer | 최초 작성 |
