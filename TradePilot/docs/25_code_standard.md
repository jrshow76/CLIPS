# TradePilot 코드 표준 (Code Standard)

> 문서 ID: 25_CODE_STANDARD
> 버전: v1.0
> 작성자: DevLead
> 최종 수정일: 2026-05-12
> 검토자: BackendSenior, FrontendSenior, QA

본 문서는 TradePilot 저장소에서 작성되는 모든 코드에 적용되는 네이밍, 폴더 컨벤션, 커밋/PR 규칙, 린트/포맷, 테스트 커버리지 기준을 정의한다. 모든 개발자는 PR 머지 전 본 표준을 충족해야 한다.

---

## 1. 일반 원칙

- **가독성 > 영리함**: 짧은 표현보다 의도가 명확한 표현을 선호한다.
- **명시적 > 암시적**: 마법 같은 코드 금지. 타입 힌트/Schema 명시.
- **불변성 > 가변성**: 가능한 경우 immutable 데이터 구조 사용.
- **순수 함수 우선**: 도메인 로직은 부수효과를 최소화한다.
- **죽은 코드 금지**: 미사용 코드/주석 처리된 코드는 제거.

---

## 2. 디렉토리 / 파일 컨벤션

### 2.1 백엔드 (Python)
| 종류 | 규칙 | 예시 |
|---|---|---|
| 패키지/모듈 | snake_case | `order_service.py` |
| 클래스 | PascalCase | `OrderService` |
| 함수/변수 | snake_case | `submit_order()` |
| 상수 | UPPER_SNAKE | `MAX_RETRY = 3` |
| Enum 값 | UPPER_SNAKE | `OrderStatus.FILLED` |
| 테스트 파일 | `test_*.py` | `test_order_service.py` |

### 2.2 프론트엔드 (TypeScript / React)
| 종류 | 규칙 | 예시 |
|---|---|---|
| 파일명 (컴포넌트) | kebab-case | `holdings-card.tsx` |
| 파일명 (훅/유틸) | kebab-case | `use-orders.ts` |
| 컴포넌트 이름 | PascalCase | `HoldingsCard` |
| 훅 | camelCase + `use` 접두사 | `useOrders` |
| 변수/함수 | camelCase | `submitOrder` |
| 상수 | UPPER_SNAKE | `MAX_PAGE_SIZE` |
| 타입/인터페이스 | PascalCase | `OrderDTO` |
| 페이지 (App Router) | `page.tsx` / `layout.tsx` | - |
| 테스트 | `*.test.ts(x)` | `holdings-card.test.tsx` |

### 2.3 디렉토리
- 백엔드 구조: `21_backend_structure.md` 준수.
- 프론트 구조: `22_frontend_structure.md` 준수.
- 신규 디렉토리 추가는 PR 설명에 사유 명시 + DevLead 승인.

---

## 3. 네이밍 규칙

### 3.1 의미
- 약어 금지 (예: `usr` → `user`, `acc` → `account`).
- 예외: 일반 통용 약어 (`id`, `db`, `api`, `url`, `json`).
- 도메인 용어는 `10_srs.md` §1.3 용어 사전 준수.

### 3.2 함수
- 동사로 시작 (`get_`, `create_`, `update_`, `delete_`, `fetch_`, `compute_`).
- 부울 반환은 `is_`, `has_`, `can_` 접두사.
- 비동기 함수는 백엔드에서 `async def`, 프론트엔드에서는 명시적 `Promise<T>` 반환.

### 3.3 변수
- 단수/복수 일치 (`order` vs `orders`).
- 단위 포함 (`timeout_ms`, `price_krw`).
- 한국어 변수명 금지.

### 3.4 DTO / Entity
- 입력: `<Name>In` (예: `OrderCreateIn`).
- 출력: `<Name>Out` (예: `OrderOut`).
- 내부 도메인 엔티티: `<Name>` (예: `Order`).
- ORM 모델: `<Name>Model` 또는 그냥 `<Name>` (단, `app.models` 패키지에 위치).

---

## 4. 코드 스타일 / 린트 / 포맷

### 4.1 Python (백엔드)
| 도구 | 역할 | 설정 |
|---|---|---|
| **Ruff** | 린터 + isort 통합 | `line-length=100`, 룰셋 `E, F, I, B, UP, S, N` |
| **Black** | 포맷터 | `line-length=100` |
| **mypy** | 타입 체크 (strict) | `strict_optional=True` |
| **pytest** | 테스트 | `pytest-asyncio`, `pytest-cov` |

`pyproject.toml` 발췌:
```toml
[tool.ruff]
line-length = 100
target-version = "py311"
select = ["E", "F", "I", "B", "UP", "S", "N"]
ignore = ["S101"]  # pytest assert

[tool.black]
line-length = 100
target-version = ["py311"]

[tool.mypy]
strict = true
plugins = ["pydantic.mypy"]
```

### 4.2 TypeScript (프론트엔드)
| 도구 | 역할 |
|---|---|
| **ESLint** (`@typescript-eslint`, `next/core-web-vitals`) | 린터 |
| **Prettier** | 포맷터 |
| **TypeScript 5.x strict** | 타입 체크 |
| **Vitest** | 단위 테스트 |
| **Playwright** | E2E |

`.prettierrc`:
```json
{
  "singleQuote": true,
  "semi": true,
  "tabWidth": 2,
  "trailingComma": "all",
  "printWidth": 100
}
```

### 4.3 자동화
- pre-commit hook 등록 (lint + format).
- CI에서 lint/format/test 통과 못하면 PR 머지 차단.

---

## 5. 주석 / 문서화

### 5.1 docstring (Python)
- 공개 모듈/클래스/함수는 Google 스타일 docstring.
- 비공개(`_prefix`)는 한 줄 설명으로 충분.

```python
def submit_order(order: Order, mode: TradeMode) -> OrderResult:
    """주문을 모드별 라우터로 전송한다.

    Args:
        order: 도메인 주문 엔티티.
        mode: SIM 또는 LIVE.

    Returns:
        OrderResult: 라우터 응답.

    Raises:
        RiskGuardError: 한도 초과 시.
    """
```

### 5.2 JSDoc (TS)
- 공개 훅/유틸 함수는 JSDoc 요약 + 파라미터/리턴.
- 컴포넌트는 props 인터페이스로 대체.

### 5.3 TODO / FIXME
- 형식: `# TODO(<owner>): <설명> (#<issue>)`.
- owner와 이슈 번호를 반드시 포함.
- 1주 이상 방치 금지.

---

## 6. 테스트 / 커버리지 기준

### 6.1 레벨별 목표
| 레벨 | 목표 |
|---|---|
| 도메인 (`domains/`) | 80% line / 70% branch |
| 서비스 (`services/`) | 70% line |
| 리포지토리 (`repositories/`) | 60% (쿼리 회귀 위주) |
| API (`api/`) | 60% (행복 경로 + 주요 에러) |
| 프론트엔드 (`src/`) | 50% (핵심 훅/컴포넌트 100%) |
| 전체 (저장소) | **60% 이상** |

### 6.2 필수 테스트
- 신규 도메인 로직 → 단위 테스트 필수.
- 신규 API → 200/40x/50x 케이스 최소 3개.
- 버그 수정 → 회귀 테스트 추가 (해당 버그를 재현하는 테스트).

### 6.3 CI 게이트
```yaml
- name: Test backend
  run: poetry run pytest --cov=app --cov-fail-under=60
- name: Test frontend
  run: pnpm test --coverage --coverage.threshold.lines=50
```

### 6.4 테스트 명명
- Python: `test_<unit>_<scenario>_<expected>` (`test_order_create_with_limit_exceeded_raises_e0021`).
- TS: `describe('OrderForm') > it('shows error when qty is zero')`.

### 6.5 픽스처 / 모킹
- 외부 시스템(크레온, SMTP)은 항상 모킹.
- 시계열 데이터는 픽스처 파일 (`tests/fixtures/candles_005930.json`).
- 시간 의존 로직은 `freezegun` (Python) / `vi.setSystemTime` (Vitest).

---

## 7. Git 브랜치 전략

### 7.1 브랜치 모델 (Trunk-based + 단기 feature)
| 브랜치 | 용도 |
|---|---|
| `main` | 항상 배포 가능한 상태 |
| `develop` (선택) | 통합 브랜치 (필요 시) |
| `feature/<scope>-<desc>` | 기능 개발 (예: `feature/order-idempotency`) |
| `fix/<scope>-<desc>` | 버그 수정 |
| `chore/<desc>` | 의존성/설정 등 비기능 변경 |
| `hotfix/<desc>` | 운영 긴급 수정 (main에서 분기) |
| `release/v<ver>` | 릴리즈 준비 (필요 시) |

- 브랜치 수명: 최대 5영업일. 그 이상은 분할 권장.

### 7.2 PR 정책
- **타겟**: `main` (또는 `develop`).
- **머지 방식**: Squash merge (기본). 릴리즈 브랜치는 Merge commit.
- **승인**: 최소 1명 (DevLead 또는 시니어). 운영 영향 큰 변경은 2명.
- **CI 통과 필수**: lint + test + build.
- **PR 크기**: +500 LOC 이내 권장. 초과 시 분할 의무.

---

## 8. 커밋 메시지 규칙

### 8.1 형식 (Conventional Commits)
```
<type>(<scope>): <subject>

<body>

<footer>
```

| type | 의미 |
|---|---|
| `feat` | 신규 기능 |
| `fix` | 버그 수정 |
| `refactor` | 동작 변경 없는 리팩터링 |
| `perf` | 성능 개선 |
| `docs` | 문서만 변경 |
| `test` | 테스트 추가/수정 |
| `chore` | 빌드/의존성/설정 |
| `style` | 포맷/공백 |
| `ci` | CI 설정 |

### 8.2 예시
```
feat(orders): X-Idempotency-Key 24시간 캐시 도입

- Redis에 (user_id, endpoint, key) 키로 응답 저장
- 동일 키 재요청 시 200 또는 기존 4xx 그대로 반환
- 만료 시 정상 처리 흐름으로 진입

Closes #142
```

### 8.3 규칙
- subject: 50자 이내, 명령형, 마침표 금지.
- body: 72자 줄바꿈, 변경 이유 위주.
- breaking change: footer에 `BREAKING CHANGE:` 포함.
- 한글 작성 허용 (단, 영문 prefix는 유지).

---

## 9. PR 템플릿

```markdown
## 변경 요약
- 

## 변경 사유 / 관련 이슈
- Closes #

## 영향 범위
- [ ] 백엔드 API
- [ ] 프론트엔드
- [ ] DB 스키마 (마이그레이션 포함 여부)
- [ ] 외부 시스템 (크레온/Redis)

## 테스트
- [ ] 단위 테스트 추가/갱신
- [ ] 통합 테스트 통과
- [ ] 수동 테스트 시나리오 (있다면 기술)

## 체크리스트
- [ ] 본 표준(25_code_standard.md) 준수
- [ ] API 변경 시 `24_api_response_spec.md` 반영
- [ ] 보안 영향 검토 (인증/권한/로깅)
- [ ] 문서 업데이트 (필요 시)
```

---

## 10. PR 리뷰 가이드

### 10.1 리뷰 우선순위
1. **정확성**: 요구사항/스펙 충족 여부.
2. **보안**: 인증/권한/입력 검증/로깅.
3. **성능**: N+1 쿼리, 불필요한 동기 호출.
4. **테스트**: 커버리지, 엣지 케이스.
5. **가독성/네이밍**.
6. **스타일** (린터가 잡지 못한 부분).

### 10.2 리뷰 톤
- "왜" 이렇게 했는지를 묻는 질문형 권장.
- 강제 변경 요청은 명확한 사유 제시.
- nit (사소한 의견)은 prefix `nit:`로 명시.

### 10.3 리뷰 SLA
- 평일 영업시간 내 24시간 이내 응답.
- 운영 hotfix는 2시간 이내.

---

## 11. 보안 코딩

| 항목 | 규칙 |
|---|---|
| 비밀번호 | 평문 저장 금지, bcrypt 해싱 |
| 시크릿 | 코드/로그 노출 금지, 환경변수 사용 |
| SQL | 파라미터 바인딩 강제 (raw SQL은 PR 시 사유 명시) |
| 직렬화 | `eval`, `pickle` 금지 |
| 외부 입력 | 항상 검증, 화이트리스트 우선 |
| 로깅 | PII 마스킹 (`14_exception_policy.md` §9.3) |
| 의존성 | `dependabot` / `pip-audit` 정기 실행 |

---

## 12. 로깅 가이드

### 12.1 형식
- 구조화 JSON 로그.
- 필수 키: `ts`, `level`, `trace_id`, `user_id?`, `event`, `payload`.

### 12.2 레벨
- DEBUG: 개발 환경 전용.
- INFO: 비즈니스 이벤트 (주문 생성/체결).
- WARN: 자동 복구된 이슈.
- ERROR: 사용자 영향 있는 실패.
- CRITICAL: 자동매매 중단, DB 단절.

### 12.3 금지
- 비밀번호, JWT, 카드/주민번호 로깅.
- 스택 트레이스는 ERROR 이상에서만.

---

## 13. 성능 / DB 가이드

- N+1 쿼리 회피: `selectinload` / `joinedload`.
- 큰 결과는 페이지네이션 강제.
- 시계열 조회는 파티션 키(`date_kst`) 포함.
- 신규 인덱스는 DBA(`10_dba.md`) 협의 후 추가.
- Redis 캐시 TTL은 데이터 성격에 맞게 (시세 3s, 마스터 1h).

---

## 14. 문서 동기화

| 변경 종류 | 갱신 대상 문서 |
|---|---|
| API 신설/변경 | `13_api_requirements.md`, `24_api_response_spec.md` |
| 에러 코드 추가 | `14_exception_policy.md` |
| 매매 정책 | `15_trading_policy.md` (PM 승인) |
| 백엔드 구조 변경 | `21_backend_structure.md` |
| 프론트 구조 변경 | `22_frontend_structure.md` |
| 게이트웨이 프로토콜 | `23_creon_gateway.md` |
| 코드 표준 | 본 문서 |

- 문서 미갱신은 PR 차단 사유.

---

## 15. 라이센스 / 외부 자산

- 외부 라이브러리는 MIT/Apache-2.0/BSD 등 호환 라이선스만 허용.
- GPL/AGPL은 PM 승인 후 사용.
- 이미지/아이콘은 사용 권한 명확한 것만.

---

## 16. CI/CD 게이트 요약

| 단계 | 게이트 |
|---|---|
| Lint | ruff / eslint 무에러 |
| Format | black / prettier 차이 없음 |
| Type | mypy / tsc 무에러 |
| Test | pytest / vitest 통과, 커버리지 임계 충족 |
| Build | docker build 성공 |
| Security | pip-audit / npm audit critical 0건 |

---

## 17. 변경 이력
| 버전 | 일자 | 작성자 | 내용 |
|---|---|---|---|
| v1.0 | 2026-05-12 | DevLead | 최초 작성 |
