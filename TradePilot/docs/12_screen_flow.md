# TradePilot 화면 흐름도 (Screen Flow)

> 문서 ID: 12_SCREEN_FLOW
> 버전: v1.0
> 작성자: Planner
> 최종 수정일: 2026-05-12

---

## 1. 메뉴 구조도 (IA)

```mermaid
graph TD
    A[TradePilot] --> B[인증]
    A --> C[메인]

    B --> B1[로그인]
    B --> B2[회원가입]
    B --> B3[비밀번호 재설정]

    C --> D[대시보드]
    C --> E[추천주]
    C --> F[차트분석]
    C --> G[업종분석]
    C --> H[매매타이밍/시그널]
    C --> I[자동매매 관리]
    C --> J[수익률 리포트]
    C --> K[백테스트]
    C --> L[설정]

    E --> E1[전략별 추천 리스트]
    E --> E2[종목 상세]

    F --> F1[캔들/지표]
    F --> F2[2종목 비교]

    G --> G1[섹터 랭킹]
    G --> G2[자금 흐름]
    G --> G3[순환 히트맵]

    H --> H1[활성 시그널]
    H --> H2[시그널 이력]
    H --> H3[알림 설정]

    I --> I1[전략 목록]
    I --> I2[전략 등록/수정]
    I --> I3[모드 전환]
    I --> I4[한도/리스크]
    I --> I5[비상정지]

    J --> J1[일/주/월 수익률]
    J --> J2[종목별 손익]
    J --> J3[거래 내역]
    J --> J4[전략별 성과]

    K --> K1[백테스트 실행]
    K --> K2[결과 조회]
    K --> K3[결과 비교]

    L --> L1[프로필]
    L --> L2[보안/OTP]
    L --> L3[알림 채널]
    L --> L4[테마]
```

---

## 2. 사용자 페르소나

| 페르소나 | 설명 | 핵심 니즈 |
|---|---|---|
| 김주식 (30대 직장인) | 평일 장중 매매 불가, 자동매매 의존 | 안정적 수익, 손실 통제, 알림 |
| 박분석 (40대 전업) | 다양한 전략 검증, 백테스트 활용 | 정교한 지표, 성과 비교, 빠른 차트 |
| 이체험 (20대 초보) | 시뮬레이션으로 학습 | 직관적 UI, 추천주, 가이드 |

---

## 3. 전체 사용자 흐름 (Top-level User Flow)

```mermaid
flowchart LR
    Start([앱 접속]) --> Login{로그인?}
    Login -- 신규 --> Signup[회원가입] --> EmailVerify[이메일 인증] --> Login
    Login -- 기존 --> Auth[로그인 처리]
    Auth --> Dashboard[대시보드]

    Dashboard --> Reco[추천주]
    Dashboard --> Chart[차트분석]
    Dashboard --> Sector[업종분석]
    Dashboard --> Signal[시그널]
    Dashboard --> Auto[자동매매]
    Dashboard --> Report[수익률 리포트]
    Dashboard --> Backtest[백테스트]
    Dashboard --> Setting[설정]

    Auto --> ModeSwitch{모드 전환}
    ModeSwitch -- SIM→LIVE --> OTPCheck[OTP/약관/한도 확인]
    OTPCheck --> CreonCheck[크레온 연결 테스트]
    CreonCheck -- 성공 --> LiveMode[LIVE 모드 활성]
    CreonCheck -- 실패 --> SimMode[SIM 모드 유지]
```

---

## 4. 시나리오별 상세 흐름

### 4.1 시나리오 A: 신규 사용자 가입 → 시뮬레이션 첫 거래

```mermaid
sequenceDiagram
    actor U as 사용자
    participant FE as Frontend
    participant BE as Backend API
    participant DB as PostgreSQL
    participant MAIL as Mail Service

    U->>FE: 회원가입(email, password)
    FE->>BE: POST /api/v1/auth/signup
    BE->>DB: users insert (status=PENDING)
    BE->>MAIL: 인증 메일 발송
    MAIL-->>U: 인증 링크
    U->>FE: 인증 링크 클릭
    FE->>BE: POST /api/v1/auth/verify-email
    BE->>DB: status=ACTIVE
    BE-->>FE: 200 OK
    U->>FE: 로그인
    FE->>BE: POST /api/v1/auth/login
    BE-->>FE: JWT(access, refresh)
    U->>FE: 대시보드 진입(SIM 모드 기본)
    U->>FE: 추천주 → 종목 상세 → 시뮬 매수
    FE->>BE: POST /api/v1/orders (X-Trade-Mode: SIM)
    BE->>BE: 가상 체결 처리
    BE->>DB: orders / portfolios 갱신
    BE-->>FE: 체결 결과
```

### 4.2 시나리오 B: 자동매매 전략 등록 및 활성화

```mermaid
sequenceDiagram
    actor U as 사용자
    participant FE as Frontend
    participant BE as Backend API
    participant ENG as Strategy Engine
    participant DB as PostgreSQL

    U->>FE: 자동매매 관리 → 전략 등록
    FE->>BE: POST /api/v1/strategies
    BE->>DB: strategies insert(active=false)
    BE-->>FE: strategy_id
    U->>FE: 활성화 토글
    FE->>BE: PATCH /api/v1/strategies/{id}/activate
    BE->>DB: active=true
    BE->>ENG: 전략 로딩 이벤트 발행
    ENG->>ENG: 5초 주기 시그널 산출 시작
    ENG-->>U: 시그널 발생 시 알림 발송
```

### 4.3 시나리오 C: 시뮬레이션 → 실거래 전환 (가장 중요한 안전 흐름)

```mermaid
flowchart TD
    Start([실거래 전환 요청]) --> Pre1{시뮬 거래 ≥30건?}
    Pre1 -- NO --> Reject1[전환 거부\n시뮬 거래 누적 필요]
    Pre1 -- YES --> Pre2{약관 동의 완료?}
    Pre2 -- NO --> ShowTerms[약관/리스크 고지 화면] --> AgreeCheck{동의}
    AgreeCheck -- NO --> Reject2[전환 취소]
    AgreeCheck -- YES --> Pre3
    Pre2 -- YES --> Pre3{OTP 인증}
    Pre3 -- 실패 --> Reject3[OTP 재시도]
    Pre3 -- 성공 --> Pre4{한도 설정 존재?}
    Pre4 -- NO --> SetLimit[일일/종목 한도 설정 화면] --> Pre5
    Pre4 -- YES --> Pre5{크레온 COM 연결 테스트}
    Pre5 -- 실패 --> Reject4[연결 실패 사유 표시]
    Pre5 -- 성공 --> Confirm[최종 확인 모달\n빨강 배경 + 체크박스]
    Confirm -- 취소 --> SimKeep[SIM 모드 유지]
    Confirm -- 확인 --> Audit[audit_log 기록] --> LiveOn[LIVE 모드 활성화]
    LiveOn --> Banner[상단 빨강 배너 노출\n실거래 모드 작동중]
```

### 4.4 시나리오 D: 시그널 발생 → 자동 주문 → 체결

```mermaid
sequenceDiagram
    participant SCH as Scheduler(5s)
    participant ENG as Strategy Engine
    participant DB as PostgreSQL
    participant CREON as 크레온 COM
    participant NOTI as Notification
    actor U as 사용자

    SCH->>ENG: tick(every 5s)
    ENG->>DB: 활성 전략/시세 조회
    ENG->>ENG: 시그널 조건 평가
    alt 시그널 발생
        ENG->>DB: signals insert
        ENG->>NOTI: 알림 발송
        NOTI-->>U: 인앱/이메일/푸시
        ENG->>ENG: 한도/모드 검사
        alt LIVE 모드
            ENG->>CREON: 매수 주문 전송
            CREON-->>ENG: 주문 응답
            ENG->>DB: orders insert
            CREON-->>ENG: 체결 이벤트
            ENG->>DB: portfolios 갱신
        else SIM 모드
            ENG->>ENG: 가상 체결(슬리피지 0.1%)
            ENG->>DB: orders/portfolios 갱신
        end
    end
```

### 4.5 시나리오 E: 비상정지(Kill Switch)

```mermaid
flowchart LR
    U[사용자] -- 클릭 --> KS[비상정지 버튼]
    KS --> Confirm{2단계 확인}
    Confirm -- 취소 --> End
    Confirm -- 확인 --> Stop1[자동매매 OFF]
    Stop1 --> Stop2[미체결 주문 전체 취소]
    Stop2 --> Stop3[현재 모드 SIM 강제]
    Stop3 --> Audit[audit_log 기록]
    Audit --> Result[처리 결과 표시\n취소 N건, 실패 M건]
```

### 4.6 시나리오 F: 백테스트 실행 및 결과 비교

```mermaid
sequenceDiagram
    actor U as 사용자
    participant FE as Frontend
    participant BE as Backend API
    participant Q as Job Queue
    participant W as Backtest Worker
    participant DB as PostgreSQL

    U->>FE: 전략·기간·자본 입력 → 실행
    FE->>BE: POST /api/v1/backtest/jobs
    BE->>Q: enqueue(job)
    BE-->>FE: job_id
    loop 진행률 폴링(3s)
        FE->>BE: GET /api/v1/backtest/jobs/{id}/progress
        BE-->>FE: percent
    end
    Q->>W: dispatch
    W->>DB: 시세 로드
    W->>W: 시뮬레이션 진행
    W->>DB: backtest_results insert
    W->>BE: 완료 콜백
    FE->>BE: GET /api/v1/backtest/jobs/{id}/result
    BE-->>FE: 결과 데이터
    U->>FE: 결과 저장/비교
```

---

## 5. 페이지 전이 다이어그램 (State)

```mermaid
stateDiagram-v2
    [*] --> 비인증
    비인증 --> 인증: 로그인 성공
    비인증 --> 비인증: 로그인 실패

    인증 --> 대시보드
    대시보드 --> 추천주
    대시보드 --> 차트분석
    대시보드 --> 업종분석
    대시보드 --> 시그널
    대시보드 --> 자동매매
    대시보드 --> 리포트
    대시보드 --> 백테스트
    대시보드 --> 설정

    자동매매 --> 모드전환: 모드 토글
    모드전환 --> 자동매매: 성공/취소

    state 자동매매 {
        [*] --> SIM
        SIM --> LIVE: 전환 조건 충족
        LIVE --> SIM: 토글 OR Kill Switch
        LIVE --> 강제청산: 손실 한도 초과
        강제청산 --> SIM
    }

    인증 --> 비인증: 로그아웃 / 토큰 만료
```

---

## 6. 모달/팝업 정의

| 모달 ID | 명칭 | 트리거 | 액션 |
|---|---|---|---|
| MD-001 | 매매 모드 전환 확인 | 모드 토글 | 확인/취소, 빨강 배경 |
| MD-002 | 약관 동의 | 첫 LIVE 전환 | 스크롤 끝 + 체크박스 |
| MD-003 | OTP 입력 | LIVE 전환, 출금 등 | 6자리 입력, 만료 3분 |
| MD-004 | 비상정지 확인 | Kill Switch | 사유 입력(선택), 확인/취소 |
| MD-005 | 강제 청산 알림 | 시스템 트리거 | 안내 + 결과 표 |
| MD-006 | 주문 확인 | 수동 매매 시 | 종목/수량/가격 표시 |
| MD-007 | 백테스트 결과 저장 | 완료 후 | 라벨 입력 |

---

## 7. 빈/오류/로딩 상태 정의

| 상태 | 화면 처리 |
|---|---|
| 로딩 | 스켈레톤 + 5초 초과 시 진행 표시 |
| 빈 상태 | 일러스트 + CTA 버튼 (예: "전략 등록하기") |
| 부분 장애 | 영역 단위 에러 카드, 재시도 버튼 |
| 시세 지연 | 가격 옆 "지연" 배지 + 마지막 갱신 시각 |
| 장 종료 | 상단 배너 + 매매 버튼 비활성 |

---

## 8. 반응형 Breakpoint

| 화면 | Desktop(≥1024) | Tablet(≥768) | Mobile(<768) |
|---|---|---|---|
| 대시보드 | 3컬럼 | 2컬럼 | 1컬럼 스택 |
| 차트분석 | 메인 + 사이드 지표 | 메인 + 하단 탭 | 메인 전용 + 모달 지표 |
| 추천주 | 테이블 | 테이블(가로 스크롤) | 카드 리스트 |
| 자동매매 | 좌측 메뉴 + 우측 컨텐츠 | 상단 탭 | 풀스크린 탭 |

---

## 9. 접근성/단축키

| 단축키 | 동작 |
|---|---|
| `Ctrl + K` | 종목 검색 |
| `Ctrl + Shift + S` | 비상정지(2단계 확인) |
| `Ctrl + M` | 모드 토글 |
| `Esc` | 모달 닫기 |

---

## 10. 변경 이력
| 버전 | 일자 | 작성자 | 내용 |
|---|---|---|---|
| v1.0 | 2026-05-12 | Planner | 최초 작성 |
