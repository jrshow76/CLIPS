# TradePilot 에러 코드 회귀 매트릭스 (Exception Regression Matrix)

> 문서 ID: 53_EXCEPTION_MATRIX
> 버전: v1.0
> 작성자: QA
> 최종 수정일: 2026-05-12

본 문서는 `14_exception_policy.md`의 40개+ 에러 코드를 회귀 테스트 매트릭스 형태로 정리한다. 각 코드는 트리거 시나리오, 기대 응답, 자동화 위치를 명시한다.

## 응답 검증 공통 항목
- HTTP 상태 코드
- 응답 본문 `success=false`, `error.code` 정확 일치
- `error.message`, `error.trace_id`, `error.ts` 필드 존재
- 입력 검증류는 `error.details` 에 필드별 메시지 누적
- 외부 시스템 장애류는 `error.details` 에 원인 코드 포함

---

## 1. 공통/시스템 (E0001~E0009)

| 코드 | HTTP | 트리거 시나리오 | 검증 포인트 | 자동화 위치 |
|---|:---:|---|---|---|
| E0001 | 401 | 토큰 미첨부 / 만료 / 시그니처 변조로 `/auth/me` 호출 | code, 로그인 페이지 리다이렉트 권고 | `test_security_jwt_otp.py::test_expired_jwt_returns_E0001` |
| E0002 | 403 | ROLE_TRADER 가 `/admin/users` 호출 | code, 메뉴 비활성 안내 | `test_security_jwt_otp.py::test_role_guard_E0002` |
| E0003 | 400 | RSI 파라미터 500, 종목코드 형식 위반, 한도 음수 | code, details 필드별 메시지 | `test_pagination_response.py` 외 다수 |
| E0004 | 502 | 시세 1차 소스 다운 + 폴백 적용 케이스 / 뉴스 소스 장애 | code, fallback 데이터 노출 | `test_market_settings_api.py` 보강 |
| E0005 | 500 | 강제 ZeroDivisionError 주입 (디버그용) | code, trace_id, 자동 재시도 X | `test_exception_matrix.py` (수동 트리거) |
| E0006 | 409 | 사용자 SIM, 헤더 `X-Trade-Mode: LIVE` 로 주문 | code, 모드 재확인 모달 트리거 | `test_trade_mode_guard.py::test_header_mismatch_E0006` |
| E0007 | 409 | KST 16:00 또는 휴장일에 주문 호출 | code, 매매 버튼 비활성 권고 | `test_trade_limits.py::test_off_hours_E0007` |
| E0008 | 429 | 4티어 슬라이딩 윈도우 초과(인증 5/min) | code, Retry-After 헤더 | `test_rate_limit.py::test_auth_tier_E0008` |
| E0009 | 503 | 점검 모드 ON 상태 일반 API 호출 | code, 점검 페이지 노출 | `test_admin.py::test_maintenance_E0009` |

---

## 2. 인증/모드 전환 (E0011~E0019)

| 코드 | HTTP | 트리거 | 검증 | 자동화 |
|---|:---:|---|---|---|
| E0011 | 401 | OTP 잘못된 코드 또는 5분 만료 | code, 재발급 5회 제한 동작 | `test_security_jwt_otp.py::test_otp_expired_E0011` |
| E0012 | 502 | LIVE 전환 시 게이트웨이 OFF | code, 진단 가이드 메시지 | `test_trade_mode_guard.py::test_creon_unreachable_E0012` |
| E0013 | 403 | 약관 미동의로 LIVE 전환 | code, 약관 모달 트리거 | `test_trade_mode_guard.py::test_disclaimer_E0013` |
| E0014 | 502 | LIVE→SIM 전환 시 미체결 1건 취소 실패 | code, 실패 주문 ID details | `test_kill_switch.py::test_partial_cancel_E0014` |
| E0015 | 502 | Kill Switch 부분 실패 | code, 미처리 ID 리스트 details | `test_kill_switch.py::test_killswitch_partial_E0015` |
| E0016 | 403 | 시뮬 15건 / 한도 미설정 상태로 LIVE 전환 | code, 사유 details | `test_trade_mode_guard.py::test_precondition_E0016` |
| E0017 | 409 | 동시 LIVE 전환 요청 | code, 중복 요청 차단 | `test_trade_mode_guard.py::test_concurrent_switch_E0017` |

---

## 3. 주문/매매 (E0021~E0029)

| 코드 | HTTP | 트리거 | 검증 | 자동화 |
|---|:---:|---|---|---|
| E0021 | 422 | 일일 5,000,001원 매수 시도 | code, `limit`/`attempted` details | `test_trade_limits.py::test_daily_limit_E0021` |
| E0022 | 409 | 동일 페이로드 60초 윈도우 재호출 | code, idempotency 안내 | `test_idempotency.py::test_dup_order_E0022` |
| E0023 | 502 | 모의 게이트웨이 응답 코드 != 0 | code, 응답 메시지 details | `test_orders_live.py::test_live_E0023` |
| E0024 | 422 | 잔고 1,000원으로 1억 매수 | code, 잔액 안내 | `test_trade_limits.py::test_margin_E0024` |
| E0025 | 502 | 강제 청산 부분 실패 | code, 미처리 종목 리스트 | `test_kill_switch.py::test_forceliq_E0025` |
| E0026 | 422 | 호가 단위 위반 (코스피 12,345원) | code, 자동 보정 옵션 안내 | `test_trade_limits.py::test_tick_E0026` |
| E0027 | 422 | 상한가 종목 매수 | code, 거부 사유 | 수동 (TC-ORDER-012) |
| E0028 | 422 | 거래정지 종목 (캐시 hit) 주문 | code, 24h 캐시 검증 | `test_trade_limits.py::test_halt_E0028` |

---

## 4. 백테스트 (E0031~E0039)

| 코드 | HTTP | 트리거 | 검증 | 자동화 |
|---|:---:|---|---|---|
| E0031 | 410 | 30일 경과 결과 조회 | code, 재실행 안내 | `test_backtest.py::test_expired_E0031` |
| E0032 | 422 | 기간 6년 / 종목 201개 입력 | code, 범위 위반 | `test_backtest.py::test_range_E0032` |
| E0033 | 500 | 워커 비정상 종료 시뮬레이션 | code, 운영자 알림 | 수동 |

---

## 5. ML/예측 (E0041~E0049)

| 코드 | HTTP | 트리거 | 검증 | 자동화 |
|---|:---:|---|---|---|
| E0041 | 404 | 미학습 종목 예측 호출 | code, 학습 대기열 등록 확인 | `test_ml.py::test_unknown_code_E0041` |
| E0042 | 500 | 야간 학습 실패 시뮬레이션 | code, 운영자 알림 | 수동 |

---

## 6. 사용자/계정 (E0051~E0059)

| 코드 | HTTP | 트리거 | 검증 | 자동화 |
|---|:---:|---|---|---|
| E0051 | 409 | 동일 이메일 재가입 | code | `test_auth_api.py::test_duplicate_E0051` (기존) |
| E0052 | 423 | 5회 실패 후 6회차 로그인 | code, 15분 안내 | `test_security_jwt_otp.py::test_lockout_E0052` |
| E0053 | 410 | 비밀번호 재설정 토큰 1시간 경과 | code, 재발급 안내 | `test_auth_api.py::test_token_expired_E0053` |
| E0054 | 400 | 위변조 재설정 토큰 | code | `test_auth_api.py::test_invalid_token_E0054` |
| E0055 | 422 | 비밀번호 정책 위반 (영문만 8자) | code, 규칙 메시지 | `test_auth_api.py::test_password_policy_E0055` |

---

## 7. 시세/시장 데이터 (E0061~E0069)

| 코드 | HTTP | 트리거 | 검증 | 자동화 |
|---|:---:|---|---|---|
| E0061 | 502 | 실시간 시세 3초 이상 미수신 | code, 직전 캐시 노출, "지연" 배지 | 수동 |
| E0062 | 404 | code="999999" 시세 조회 | code, 종목 없음 | `test_market.py::test_unknown_code_E0062` |
| E0063 | 422 | 차트 기간 6년 요청 | code, 분할 요청 안내 | `test_chart.py::test_range_E0063` |

---

## 8. 외부 시스템 (E0071~E0079)

| 코드 | HTTP | 트리거 | 검증 | 자동화 |
|---|:---:|---|---|---|
| E0071 | 502 | 외부 데이터 소스 5xx 응답 | code | 수동 |
| E0072 | 504 | CREON 응답 5초 초과 | code, 재시도 3회 후 실패 | `test_orders_live.py::test_timeout_E0072` |

---

## 9. 알림/외부채널 (E0081~E0089)

| 코드 | HTTP | 트리거 | 검증 | 자동화 |
|---|:---:|---|---|---|
| E0081 | 502 | SMTP 다운 상태 발송 | code, 큐 재시도 5회 | 수동 (`test_notifications_api.py` 확장) |
| E0082 | 422 | 미설정 채널로 발송 시도 | code | `test_notifications_api.py::test_unconfigured_E0082` |

---

## 10. 운영/관리 (E0091~E0099)

| 코드 | HTTP | 트리거 | 검증 | 자동화 |
|---|:---:|---|---|---|
| E0091 | 503 | DB 헬스체크 실패 시 일반 API | code, 메인터넌스 모드 진입 | 수동 |
| E0092 | 403 | 일반 사용자가 `/admin/*` 호출 | code | `test_security_jwt_otp.py::test_admin_only_E0092` |

---

## 11. 매트릭스 요약

| 그룹 | 코드 수 | 자동화 | 수동 |
|---|:---:|:---:|:---:|
| 공통/시스템 (E000x) | 9 | 7 | 2 |
| 인증/모드 (E001x) | 7 | 7 | 0 |
| 주문/매매 (E002x) | 8 | 7 | 1 |
| 백테스트 (E003x) | 3 | 2 | 1 |
| ML/예측 (E004x) | 2 | 1 | 1 |
| 사용자 (E005x) | 5 | 5 | 0 |
| 시세 (E006x) | 3 | 2 | 1 |
| 외부 (E007x) | 2 | 1 | 1 |
| 알림 (E008x) | 2 | 1 | 1 |
| 운영 (E009x) | 2 | 1 | 1 |
| **합계** | **43** | **34** | **9** |

> 자동화 비율: 34/43 ≈ 79.1% (P0 코드는 100% 자동화 유지)

---

## 12. 회귀 실행

```bash
# 백엔드 회귀 (qa 마커 + integration)
cd backend
pytest tests/qa tests/integration -m "qa or integration" -v --tb=short

# 특정 그룹만
pytest tests/qa -k "E002" -v
```

---

## 13. 응답 본문 회귀 샘플 (Schema)

```jsonc
{
  "success": false,
  "error": {
    "code": "E0021",                         // ^E\\d{4}$
    "message": "일일 매수 한도를 초과했습니다.",  // 한글 메시지
    "details": {                              // 코드별 컨텍스트
      "limit": 5000000,
      "attempted": 5200000
    },
    "trace_id": "uuid-...",                  // 운영 추적용
    "ts": "2026-05-12T10:11:22+09:00"        // ISO-8601 KST
  }
}
```

- 모든 에러 응답은 위 스키마를 따른다(JSON Schema 검증을 자동화 회귀에 포함).

---

## 14. 변경 이력
| 버전 | 일자 | 작성자 | 내용 |
|---|---|---|---|
| v1.0 | 2026-05-12 | QA | 최초 작성 |
