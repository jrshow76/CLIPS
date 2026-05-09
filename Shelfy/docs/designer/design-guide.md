# Shelfy Design Guide

- 작성일: 2026-05-09
- 작성자: Designer
- 버전: v1.0.0

---

## 목차

1. [디자인 원칙](#1-디자인-원칙)
2. [컬러 시스템](#2-컬러-시스템)
3. [타이포그래피](#3-타이포그래피)
4. [스페이싱 & 그리드](#4-스페이싱--그리드)
5. [Border Radius & Shadow](#5-border-radius--shadow)
6. [컴포넌트 규격](#6-컴포넌트-규격)
7. [반응형 브레이크포인트](#7-반응형-브레이크포인트)
8. [아이콘 가이드라인](#8-아이콘-가이드라인)
9. [CSS 클래스 명명 규칙 (BEM)](#9-css-클래스-명명-규칙-bem)
10. [화면별 구조 요약](#10-화면별-구조-요약)

---

## 1. 디자인 원칙

### 톤앤매너

- **미니멀하고 따뜻한 감성**: 선반(Shelf)이라는 물리적 공간을 디지털로 표현
- **신뢰감**: 깔끔한 레이아웃과 명확한 정보 계층으로 구매자의 신뢰를 유도
- **콘텐츠 중심**: UI 요소는 콘텐츠를 방해하지 않도록 최소화
- **접근성**: WCAG 2.1 AA 기준 준수. 색상 대비 4.5:1 이상 유지

### 핵심 키워드

선반(Shelf), 온기, 신뢰, 창작, 공유, 미니멀

---

## 2. 컬러 시스템

모든 색상은 CSS Custom Properties로 관리하며 `common.css`의 `:root`에 정의되어 있다.

### Brand Colors

| 토큰명 | 값 | 용도 |
|---|---|---|
| `--color-primary` | `#C85C3D` | 딥 테라코타. 주요 CTA, 강조 요소 |
| `--color-primary-light` | `#E07B5F` | 호버 상태 밝은 버전 |
| `--color-primary-dark` | `#A34428` | 호버 상태 어두운 버전, 클릭 피드백 |
| `--color-primary-10` | `rgba(200, 92, 61, 0.10)` | 선택 상태 배경, 알림 배경 |
| `--color-primary-20` | `rgba(200, 92, 61, 0.20)` | 텍스트 선택 강조 |

### Background Colors

| 토큰명 | 값 | 용도 |
|---|---|---|
| `--color-bg-base` | `#FAF9F6` | 따뜻한 오프화이트. 전체 페이지 배경 |
| `--color-bg-surface` | `#FFFFFF` | 카드, 모달, 패널 배경 |
| `--color-bg-muted` | `#F3F1EC` | 비활성 영역, 인풋 배경, 섹션 배경 |
| `--color-bg-subtle` | `#EAE8E2` | 경계선 근접 배경, 호버 배경 |

### Text Colors

| 토큰명 | 값 | 용도 |
|---|---|---|
| `--color-text-primary` | `#1C1A17` | 주요 텍스트, 제목 |
| `--color-text-secondary` | `#5C5751` | 본문, 설명 텍스트 |
| `--color-text-tertiary` | `#9B948C` | 힌트, 메타 정보 |
| `--color-text-disabled` | `#C4BFB9` | 비활성화된 텍스트 |
| `--color-text-inverse` | `#FFFFFF` | 어두운 배경 위 텍스트 |

### Semantic Colors

| 토큰명 | 값 | 용도 |
|---|---|---|
| `--color-success` | `#2D7D4A` | 성공 상태 |
| `--color-warning` | `#B57A1E` | 경고 상태 |
| `--color-error` | `#C0392B` | 오류 상태 |
| `--color-info` | `#2563EB` | 정보 안내 |

### Badge Colors (판매 유형 구분)

| 유형 | 색상 | 토큰 |
|---|---|---|
| 구매 (PURCHASE) | `#3D5AC8` (인디고) | `--color-badge-purchase` |
| 구독 (SUBSCRIBE) | `#C85C3D` (테라코타) | `--color-primary` |
| 구매+구독 (BOTH) | `#7C3DBF` (퍼플) | `--color-badge-both` |

---

## 3. 타이포그래피

### 서체

```
Primary: 'Pretendard' → 'Noto Sans KR' → -apple-system → sans-serif
Mono: 'JetBrains Mono' → 'Courier New' → monospace
```

Pretendard는 한글/영문 최적화된 Variable Font로 웹폰트 CDN을 통해 로드한다.

### 폰트 크기 스케일

| 토큰 | 값 | px | 용도 |
|---|---|---|---|
| `--font-size-2xs` | `0.625rem` | 10px | 뱃지 텍스트 |
| `--font-size-xs` | `0.75rem` | 12px | 캡션, 힌트, 메타 |
| `--font-size-sm` | `0.875rem` | 14px | 본문 소, 버튼, 레이블 |
| `--font-size-base` | `1rem` | 16px | 본문 기본 |
| `--font-size-lg` | `1.125rem` | 18px | 소제목, 강조 본문 |
| `--font-size-xl` | `1.25rem` | 20px | 카드 제목 |
| `--font-size-2xl` | `1.5rem` | 24px | 섹션 제목 |
| `--font-size-3xl` | `1.875rem` | 30px | 페이지 제목 |
| `--font-size-4xl` | `2.25rem` | 36px | 대형 제목 |
| `--font-size-5xl` | `3rem` | 48px | 히어로 제목 |

### 폰트 굵기

| 토큰 | 값 | 용도 |
|---|---|---|
| `--font-weight-regular` | 400 | 본문 |
| `--font-weight-medium` | 500 | 레이블, 네비게이션 |
| `--font-weight-semibold` | 600 | 카드 제목, 버튼 |
| `--font-weight-bold` | 700 | 페이지 제목, 강조 |
| `--font-weight-extrabold` | 800 | 히어로 제목 |

### 줄간격 (Line Height)

| 토큰 | 값 | 용도 |
|---|---|---|
| `--line-height-tight` | 1.2 | 제목 |
| `--line-height-snug` | 1.35 | 카드 제목 |
| `--line-height-normal` | 1.5 | UI 요소 |
| `--line-height-relaxed` | 1.65 | 본문 텍스트 |
| `--line-height-loose` | 1.8 | 긴 설명 |

---

## 4. 스페이싱 & 그리드

### 스페이싱 스케일 (4px 기반)

| 토큰 | 값 | px | 용도 예시 |
|---|---|---|---|
| `--space-1` | `0.25rem` | 4px | 아이콘-텍스트 간격 |
| `--space-2` | `0.5rem` | 8px | 인라인 요소 간격 |
| `--space-3` | `0.75rem` | 12px | 버튼 패딩 소 |
| `--space-4` | `1rem` | 16px | 카드 내부 패딩, 기본 간격 |
| `--space-5` | `1.25rem` | 20px | 폼 필드 간격 |
| `--space-6` | `1.5rem` | 24px | 섹션 내부 패딩 |
| `--space-8` | `2rem` | 32px | 카드 간격, 섹션 상단 |
| `--space-10` | `2.5rem` | 40px | 큰 버튼 패딩 |
| `--space-12` | `3rem` | 48px | 섹션 간격 |
| `--space-16` | `4rem` | 64px | 대형 섹션 패딩 |
| `--space-20` | `5rem` | 80px | 페이지 하단 여백 |
| `--space-24` | `6rem` | 96px | 히어로 패딩 |

### 컨테이너 너비

| 토큰 | 값 | 용도 |
|---|---|---|
| `--container-sm` | 640px | 인증 폼, 좁은 모달 |
| `--container-md` | 768px | 중간 크기 콘텐츠 |
| `--container-lg` | 1024px | 등록 폼 |
| `--container-xl` | 1280px | 일반 페이지 최대 너비 |
| `--container-2xl` | 1440px | GNB 최대 너비 |

### 그리드 컬럼

| 화면 | 상품 카드 그리드 | 비고 |
|---|---|---|
| Desktop (1280px+) | 4컬럼 | 홈/탐색 |
| Tablet (768-1024px) | 3컬럼 | |
| Mobile Large (480-768px) | 2컬럼 | |
| Mobile Small (-480px) | 2컬럼 | gap 축소 |

---

## 5. Border Radius & Shadow

### Border Radius

| 토큰 | 값 | 용도 |
|---|---|---|
| `--radius-sm` | 4px | 뱃지, 체크박스 |
| `--radius-md` | 8px | 버튼, 인풋, 드롭다운 |
| `--radius-lg` | 12px | 카드 내부 요소 |
| `--radius-xl` | 16px | 카드, 패널 |
| `--radius-2xl` | 24px | 모달, 큰 카드 |
| `--radius-full` | 9999px | 아바타, 태그, 필 버튼 |

### Shadow

| 토큰 | 용도 |
|---|---|
| `--shadow-xs` | 매우 미세한 그림자 (인풋 기본) |
| `--shadow-sm` | 인풋 호버, 작은 카드 |
| `--shadow-md` | 드롭다운, 툴팁 |
| `--shadow-lg` | 카드 호버 상태 |
| `--shadow-xl` | 모달, 플로팅 패널 |
| `--shadow-focus` | 포커스 링 (primary 색상 25% 투명도) |

---

## 6. 컴포넌트 규격

### Button

| 클래스 | 높이 | 패딩 | 폰트 크기 | 용도 |
|---|---|---|---|---|
| `.btn--sm` | 36px | 0 16px | 12px | 인라인, 테이블 액션 |
| `.btn` (default) | 44px | 0 24px | 14px | 일반 버튼 |
| `.btn--lg` | 52px | 0 32px | 16px | 주요 CTA |
| `.btn--xl` | 60px | 0 40px | 18px | 히어로 CTA |

**변형:**
- `.btn--primary`: 테라코타 배경, 흰색 텍스트
- `.btn--secondary`: 흰색 배경, 테두리, 기본 텍스트
- `.btn--ghost`: 투명 배경, 보조 텍스트
- `.btn--danger`: 에러 색상 배경

**상태:**
- Hover: 배경색 어둡게 (primary-dark)
- Focus: focus ring (3px, 25% 투명도)
- Active: translateY(1px)
- Disabled: opacity 0.45, pointer-events none

### Input / Textarea

| 속성 | 값 |
|---|---|
| 기본 높이 | 44px |
| 패딩 | 0 16px |
| 테두리 | 1.5px solid `--color-border-default` |
| 포커스 테두리 | `--color-primary` + shadow-focus |
| 오류 테두리 | `--color-error` |
| Border Radius | `--radius-md` (8px) |

### Card (item-card)

| 속성 | 값 |
|---|---|
| 배경 | `--color-bg-surface` |
| 테두리 | 1px solid `--color-border-default` |
| Border Radius | `--radius-xl` (16px) |
| 이미지 비율 | 3:2 (padding-top: 66.67%) |
| 호버 | translateY(-3px), shadow-lg |
| 전환 효과 | 300ms ease |

**구조:**
```
.item-card
  └── .item-card__thumb (이미지 영역)
        ├── img (object-fit: cover)
        └── .item-card__badge (판매 유형 뱃지)
  └── .item-card__body
        ├── .item-card__seller (셀러 정보)
        ├── .item-card__title (상품명, 2줄 클램프)
        └── .item-card__footer
              ├── .item-card__price
              └── .item-card__meta (조회수 등)
```

### Badge

| 클래스 | 색상 | 용도 |
|---|---|---|
| `.badge--purchase` | 인디고 (#3D5AC8) | 단일 구매 |
| `.badge--subscribe` | 테라코타 (#C85C3D) | 구독 |
| `.badge--both` | 퍼플 (#7C3DBF) | 구매+구독 |
| `.badge--success` | 그린 | 성공, 활성 |
| `.badge--warning` | 옐로우 | 경고 |
| `.badge--error` | 레드 | 오류 |
| `.badge--neutral` | 그레이 | 비공개, 기본 |

높이: 자동, 패딩: 2px 8px, 폰트: 10px, 대문자, letter-spacing: 0.04em

### GNB (Global Navigation Bar)

| 속성 | 값 |
|---|---|
| 높이 (데스크탑) | 64px |
| 높이 (모바일) | 56px |
| 배경 | `--color-bg-surface` |
| 테두리 하단 | 1px solid `--color-border-default` |
| 위치 | fixed, top: 0, z-index: 200 |
| 최대 너비 | `--container-2xl` (1440px) |

**로고:** 32x32 박스 (radius-md), 텍스트 20px extrabold

**검색 인풋:**
- 최대 너비: 480px
- 높이: 40px
- 기본 배경: `--color-bg-muted`
- 포커스: `--color-bg-surface` + 테두리 primary

### Modal

| 속성 | 값 |
|---|---|
| 최대 너비 | 480px |
| 최대 높이 | 90vh |
| Border Radius | `--radius-2xl` (24px) |
| 배경막 | rgba(28,26,23, 0.50) + blur(2px) |
| z-index | 400 |

**모바일:** 화면 하단에서 슬라이드업 (border-radius 상단만 적용)

### Form Field

**구조:**
```
.form-field
  ├── .form-label (필수 시 ::after 별표)
  ├── .form-input / .form-textarea / .form-select
  ├── .form-hint (회색, xs 크기)
  └── .form-error (error 색상, xs 크기)
```

### Avatar

| 클래스 | 크기 | 용도 |
|---|---|---|
| `.avatar--sm` | 32px | 리스트 셀러 정보 |
| `.avatar--md` | 48px | 카드 셀러 정보 |
| `.avatar--lg` | 64px | 상세 페이지 셀러 |
| `.avatar--xl` | 80px | 프로필 페이지 |
| `.avatar--2xl` | 96px | 프로필 히어로 |

---

## 7. 반응형 브레이크포인트

| 브레이크포인트 | 범위 | 변화 내용 |
|---|---|---|
| Desktop | 1024px 초과 | 4컬럼 그리드, 풀 GNB |
| Tablet | 768-1024px | 3컬럼 그리드, 필터 사이드바 220px |
| Mobile Large | 480-768px | 2컬럼 그리드, GNB 검색 숨김, 필터 서랍 |
| Mobile Small | 480px 이하 | 2컬럼 유지, 모달 하단 슬라이드업 |

### 모바일 퍼스트 전략

- 기본 스타일: 모바일 기준
- `min-width` 미디어 쿼리로 점진적 향상
- 단, 기존 퍼블리싱은 데스크탑 중심으로 작성 후 반응형 오버라이드 포함

---

## 8. 아이콘 가이드라인

### 아이콘 소스

- 인라인 SVG 사용 (외부 라이브러리 의존 최소화)
- stroke 방식, stroke-width: 1.5~2.5

### 크기 규격

| 용도 | 크기 |
|---|---|
| 인라인 텍스트 | 14-16px |
| 버튼 내 아이콘 | 16-18px |
| 네비게이션 | 18-20px |
| 카드 메타 | 12-14px |
| 대형 Empty State | 24-32px |

### aria 처리 원칙

- 장식용 아이콘: `aria-hidden="true"`
- 의미 있는 아이콘: `aria-label` 또는 `title` 요소 추가
- 아이콘 단독 버튼: 버튼에 `aria-label` 필수

---

## 9. CSS 클래스 명명 규칙 (BEM)

```
Block__Element--Modifier
```

**예시:**
```css
.item-card                    /* Block */
.item-card__thumb             /* Element */
.item-card__thumb--video      /* Element + Modifier */
.item-card--draft             /* Block + Modifier */
```

### 전역 유틸리티 클래스

- `.sr-only`: 스크린리더 전용 텍스트
- `.truncate`: 텍스트 한 줄 말줄임
- `.line-clamp-2`, `.line-clamp-3`: 다중 줄 말줄임
- `.container`: 최대 너비 1280px + 좌우 패딩

### 상태 클래스 (JavaScript와 연동)

| 클래스 | 용도 |
|---|---|
| `--active` | 활성 탭, 선택된 항목 |
| `--selected` | 선택된 옵션 (라디오/체크박스 대체) |
| `--open` | 드롭다운/아코디언 열림 상태 |
| `--loading` | 로딩 중 상태 |
| `--disabled` | 비활성화 (JS로 추가) |
| `--error` | 오류 상태 (폼 필드) |
| `--draft` | 비공개 상품 카드 |

---

## 10. 화면별 구조 요약

### 01_landing.html (SCR-001)

```
<body>
  <header class="gnb">         ← 고정 상단 바
  <main class="page-body">
    <section class="hero">     ← 히어로 (2컬럼: 텍스트 + 목업)
    <nav class="category-bar"> ← 스티키 카테고리 탭
    <div class="browse-toolbar">← 정렬 선택
    <section class="items-section">
      <div class="items-grid"> ← 4컬럼 상품 카드 그리드
    <section class="featured-section"> ← 추천 셀러 3컬럼
    <div class="cta-banner">   ← 테라코타 CTA 배너
  <footer class="footer">
```

### 02_browse.html (SCR-002)

```
<body>
  <header class="gnb">
  <div class="search-header">  ← 검색바 + 결과 정보 + 활성 필터칩
  <main class="page-body">
    <div class="browse-layout"> ← 2컬럼 레이아웃
      <aside class="filter-sidebar"> ← 260px 필터 사이드바
        <div class="filter-group">  ← 아코디언 필터 그룹
      <div class="browse-content">
        <div class="browse-toolbar-row"> ← 정렬 + 뷰 토글
        <div class="browse-grid">  ← 3컬럼 카드 그리드
        <nav class="pagination">
  <footer>
```

### 03_item-detail.html (SCR-003)

```
<body>
  <header class="gnb">
  <main class="page-body">
    <div class="detail-layout">
      <nav class="breadcrumb">
      <div class="detail-content"> ← 2컬럼 (콘텐츠 / 구매 패널)
        <div class="detail-body">
          <section .gallery>      ← 이미지 갤러리
          <section .detail-section> ← 상품 설명
          <section .detail-section> ← 셀러 정보
        <aside class="item-panel"> ← 스티키 구매 패널
          <div .item-panel__price-block>
          <div .sub-plans>        ← 구독 플랜 선택
          <div .item-panel__cta>  ← 구매/구독 버튼
      <section .related-section>  ← 관련 상품 4컬럼
  <div class="mobile-purchase-bar"> ← 모바일 하단 고정
  <footer>
```

### 04_my-shelf.html (SCR-004 / SCR-021)

```
<body>
  <header class="gnb">
  <main class="page-body">
    <div class="profile-hero">   ← 프로필 헤더 섹션
      <div .profile-owner-notice> ← 소유자 알림 (본인만)
      <div .profile-hero__top>   ← 아바타 + 이름 + 통계
      <nav .profile-tabs>        ← 탭 네비게이션
    <div class="shelf-layout">
      <div .shelf-owner-toolbar> ← 상태 탭 + 정렬 + 등록 버튼
      <div class="shelf-grid">   ← 4컬럼 카드 그리드
        (item-card + overlay controls + toggle)
      <nav .pagination>
  <footer>
```

### 05_item-register.html (SCR-022)

```
<body>
  <header class="gnb">          ← 자동저장 표시
  <main class="page-body">
    <div class="register-layout">
      <div .register-header>    ← 뒤로가기 + 제목
      <div .step-indicator>     ← 4단계 인디케이터
      <div .form-card>          ← Step 1 (완료 상태)
      <div .form-card#step-2>   ← Step 2 판매유형 (활성)
        .sale-type-cards        ← 3가지 판매 유형 선택
        .pricing-section        ← 구독 플랜 빌더
        .form-nav               ← 이전/다음 버튼
      <div .form-card#step-3>   ← Step 3 이미지/태그
        .image-upload-zone      ← 드래그앤드롭 영역
        .image-preview-grid     ← 5컬럼 이미지 프리뷰
        .tag-input-area         ← 태그 입력
      <div .form-card#step-4>   ← Step 4 공개 설정
        .publish-option-cards   ← DRAFT / PUBLISHED 선택
  <footer>
```

---

## 변경 이력

| 버전 | 날짜 | 내용 |
|---|---|---|
| v1.0.0 | 2026-05-09 | 최초 작성 (5개 화면 퍼블리싱 완료) |
