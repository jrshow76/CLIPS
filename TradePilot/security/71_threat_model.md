# TradePilot 위협 모델 (Threat Model)

> 문서 ID: 71_THREAT_MODEL
> 버전: v1.0
> 작성자: QA (Security Review)
> 검토자: PM, DevLead
> 최종 수정일: 2026-05-13
> 분석 방법: STRIDE + 자산/공격 시나리오 기반

---

## 1. 자산 식별 (Asset Inventory)

| 자산 ID | 자산 | 영향 등급 | 위치 | 손상 시 영향 |
|---|---|:---:|---|---|
| ASSET-1 | 사용자 자본 (실거래 잔고) | **CRITICAL** | CREON 계좌, `tp_trade.positions` | 직접 금전 손실 |
| ASSET-2 | 계정 자격증명 (이메일/비밀번호 해시/JWT) | **CRITICAL** | `users` 테이블, JWT_SECRET | 계정 탈취 → 자본 직결 |
| ASSET-3 | CREON 계좌 비밀번호 | **CRITICAL** | `users.creon_password_encrypted` (AES-256-GCM) | 실거래 무단 발주 |
| ASSET-4 | 매매 전략 / ML 모델 | **HIGH** | `strategies`, `ML_MODEL_DIR` | 영업 비밀, 전략 모방·역공작 |
| ASSET-5 | 시세 데이터 (CREON 실시간) | **HIGH** | Redis pub/sub, `tp_market.price_*` | 데이터 변조로 잘못된 매매 유도 |
| ASSET-6 | 감사 로그 (audit_login, kill_switch_log, audit_order_history) | **HIGH** | `tp_audit.*` | 사후 책임 추적 불능 |
| ASSET-7 | 백업 데이터 (DB 풀백업, WAL) | **HIGH** | `/var/backup/tradepilot`, S3 | 외부 노출 시 모든 정보 유출 |
| ASSET-8 | 게이트웨이 API Key | **CRITICAL** | `CREON_GATEWAY_API_KEY` | 게이트웨이 무단 호출 → 실거래 |
| ASSET-9 | OTP / 비밀번호 재설정 토큰 | **HIGH** | Redis (`pwreset:*`, `otp:*`) | 단기 계정 탈취 |
| ASSET-10 | 운영 인프라 시크릿 (DB 비밀번호, SMTP, GPG, AWS IAM) | **CRITICAL** | `.env`, AWS IAM | 시스템 전반 침해 |

---

## 2. 신뢰 경계 (Trust Boundaries)

```
[Public Internet]                           ← 신뢰도 0
       │
       │ HTTPS:443 (TLS 1.2+)
       ▼
[nginx 프록시 (TLS 종단)]                    ← 신뢰도 1 (Rate Limit, 보안 헤더)
       │
       │ HTTP (사설 docker network)
       ▼
[backend-api (FastAPI)] ──────► [PostgreSQL]   ← 신뢰도 2 (인증/권한 검증 후)
       │                  └───► [Redis]
       │
       │ HTTPS (or HTTP, 사설망)
       ▼
[creon-gateway (Windows)]                    ← 신뢰도 2 (X-Gateway-Api-Key)
       │
       │ COM (Windows IPC)
       ▼
[CREON Plus] ────► [대신증권 시스템]          ← 외부, 통제 불가
```

### 2.1 경계별 통제

| 경계 | 통제 메커니즘 | 갭 |
|---|---|---|
| Internet → nginx | TLS, HSTS, Rate Limit, IP 동시연결 | A+ 등급 목표(`docs/41` §8) |
| nginx → backend | Docker 사설 네트워크 + JWT 인증 | 평문 HTTP(설계 의도) |
| backend → DB | DATABASE_URL 비밀번호 + 사설 네트워크 | DB 비밀번호 회전 정책 미정 |
| backend → gateway | X-Gateway-Api-Key (timing-safe, SEC-002 수정) | mTLS 미도입(SEC-002-FOLLOWUP) |
| gateway → CREON COM | Windows ACL + 게이트웨이 호스트 격리 | Windows 호스트 OS 보안 의존 |

---

## 3. STRIDE 분석

### S — Spoofing (위장)

| 위협 | 자산 | 영향 | 완화책 | 갭 |
|---|---|---|---|---|
| 사용자 JWT 위조 | ASSET-2 | Critical | HS256 + 32바이트 시크릿, 알고리즘 화이트리스트(SEC-006) | RS256 미적용 |
| Refresh 토큰 탈취 후 재사용 | ASSET-2 | High | Replay 탐지 + 전 세션 폐기(SEC-004 수정) | 완전 회전 미구현 |
| Gateway API Key 추측/탈취 | ASSET-8 | Critical | timing-safe 비교(SEC-002), 32자 강제 | mTLS 부재 |
| WebSocket 연결 위장 | ASSET-2 | High | JWT 검증 (query 또는 첫 메시지) | query token 로그 노출(SEC-007 수정) |
| OAuth state 등 미사용(현재 OAuth 없음) | - | - | - | 향후 SSO 도입 시 검토 |

### T — Tampering (변조)

| 위협 | 자산 | 영향 | 완화책 | 갭 |
|---|---|---|---|---|
| 주문 페이로드 변조(qty 음수, price 0) | ASSET-1 | Critical | Pydantic 검증(`qty >= 1`, regex) | 점검 통과 ✅ |
| X-Trade-Mode 헤더 위조 | ASSET-1 | Critical | `require_trade_mode`에서 사용자 모드 vs 헤더 비교(E0006) | ✅ |
| 백업 파일 변조 | ASSET-7 | High | SHA256 체크섬 + GPG 서명 | 운영 환경 plaintext 토글 가능(SEC-025) |
| 시세 데이터 변조 (man-in-the-middle) | ASSET-5 | High | CREON COM은 ActiveX 암호화, 본체↔게이트웨이는 사설망 | mTLS 권장 |
| ML 모델 파일 변조(모델 디렉토리 침해) | ASSET-4 | High | `ML_MODEL_DIR` 호스트 ACL | 무결성 검증(SHA256) 미적용 |

### R — Repudiation (부인)

| 위협 | 자산 | 영향 | 완화책 | 갭 |
|---|---|---|---|---|
| 사용자가 자신이 발주한 주문 부인 | ASSET-6 | High | `audit_order_history` (append-only), `kill_switch_log` | append-only DB 트리거 미적용(SEC-028-FOLLOWUP) |
| 관리자 권한 변경 부인 | ASSET-6 | High | `audit_login` 기록 + 관리자 API 모두 audit | OK |
| Kill Switch 발동 부인 | ASSET-6 | Critical | `kill_switch_log.trigger_type=USER/AUTO/SYSTEM` | OK |

### I — Information Disclosure (정보 노출)

| 위협 | 자산 | 영향 | 완화책 | 갭 |
|---|---|---|---|---|
| WebSocket 토큰이 nginx 액세스 로그 평문 노출 | ASSET-2 | High | 마스킹 적용(SEC-007 수정) | ✅ |
| DB 에러 메시지의 컬럼명/제약명 응답 노출 | ASSET-4 | Medium | 응답에서 db_error 제거(SEC-008 수정) | ✅ |
| 사용자 enumeration (signup E0051) | ASSET-2 | Medium | - | 후속(SEC-014) |
| 운영 환경 `/docs` OpenAPI 노출 | - | Low | `is_test`만 비활성 | 후속(SEC-023) |
| OTP/비밀번호 재설정 토큰 평문 로깅 | ASSET-9 | High | 평문 로깅 제거(SEC-009 수정) | structlog 자동 마스킹 미적용 |
| 백업 파일 외부 유출(S3 버킷 misconfig) | ASSET-7 | Critical | IAM 최소 권한 정책(`docs/42` §7.2) | 정기 audit 필요 |
| 평문 시크릿 (.env) 호스트 노출 | ASSET-10 | Critical | .gitignore + 600 권한 권장 | Vault 미도입(SEC-001-FOLLOWUP) |

### D — Denial of Service

| 위협 | 자산 | 영향 | 완화책 | 갭 |
|---|---|---|---|---|
| 로그인 brute force / DoS | ASSET-2 | High | nginx zn_login(5r/min/IP) + 백엔드 RateLimit + 5회 실패 시 15분 잠금 | Redis 장애 시 fail-open(SEC-013) |
| 주문 폭주 (시장가 다중 발주) | ASSET-1 | Critical | nginx zn_order(3r/s, burst 5) + RATE_LIMIT_ORDER_PER_DAY=1000 | OK |
| WebSocket 연결 폭주 | - | Medium | nginx zn_ws(20r/s), limit_conn 100/IP | OK |
| 대용량 페이로드 (백테스트 CSV) | - | Medium | nginx client_max_body_size=10m | OK |
| Redis 메모리 폭주(idempotency 키 누적) | - | Medium | TTL 24h + maxmemory-policy=allkeys-lru | OK |
| DB 커넥션 고갈 | - | Medium | DB_POOL_SIZE=10, MAX_OVERFLOW=5 | 워커 다수 시 풀 분리 검토 |

### E — Elevation of Privilege

| 위협 | 자산 | 영향 | 완화책 | 갭 |
|---|---|---|---|---|
| 일반 사용자가 admin 엔드포인트 접근 | ASSET-6 | Critical | `require_role("ROLE_ADMIN")` Depends | ✅ (E0092 자동화 테스트) |
| ROLE_TRADER가 LIVE 모드 발주 | ASSET-1 | Critical | `require_trade_mode`에서 E0002 차단 | ✅ |
| OTP 토큰을 일반 access 토큰처럼 사용 | ASSET-2 | High | `role=ROLE_OTP`로 발급, 권한 가드에서 차단 | OK (단 `ROLE_OTP` 별도 가드 점검 필요) |
| Sub-claim 임의 변경(타 사용자 sub) | ASSET-1 | Critical | JWT 시그니처 검증 | ✅ |
| Postgres `tradepilot` 사용자가 SUPERUSER인지 | ASSET-10 | High | `database/init/` 스크립트 점검 필요 | 후속 점검(SEC-029-FOLLOWUP) |

---

## 4. 공격 시나리오 (Attack Scenarios)

### Scenario 1: 외부 공격자 - JWT 위조 후 자동매매 유발

1. 정찰: `tradepilot.example.com` 노출 → `/api/v1/openapi.json` 또는 `/docs` 분석.
2. 운영 환경에 `JWT_SECRET=change-this-in-production-please-32bytes-min` 잔존(설정 누락).
3. 공격자가 임의 sub로 JWT 위조 → `Authorization: Bearer <forged>` 호출.
4. ROLE_TRADER_PRO + LIVE 모드 인 척 발주 → 피해자 자본으로 임의 매매.

**방어**:
- ✅ SEC-001 자동수정: 운영 기동 시 fail-fast.
- ✅ SEC-006 자동수정: alg 변조 차단.
- 후속: 운영 환경 `/docs` 비활성(SEC-023).

### Scenario 2: 내부 위협 - DBA가 직접 DB 접근하여 주문 변조

1. DBA가 운영 DB에 psql 직접 접근 (현재 정책상 가능).
2. `UPDATE tp_trade.orders SET price=99999 WHERE id=...` 실행.
3. 사용자 모르게 손익 조작 가능.

**방어**:
- `tp_audit.audit_order_history` append-only 트리거 → 변경 이력 추적.
- `docs/42_backup_recovery_guide.md` 시나리오 5: DROP/TRUNCATE EVENT TRIGGER 권장.
- 후속: 운영 DB는 bastion + audit log + RBAC 강화(SEC-029-FOLLOWUP).

### Scenario 3: 공급망 공격 - 의존성 라이브러리 침해

1. `pyjwt`, `cryptography`, `next` 등 의존성 maintainer 계정 탈취.
2. 패치 배포 → CI에서 자동 빌드 시 침해 코드 포함.

**방어**:
- ✅ `tradepilot-security.yml` 워크플로우: pip-audit, npm audit, Trivy 정기 스캔.
- 후속: 의존성 핀(`==X.Y.Z`) 강화 + lockfile 무결성(SHA) 검증.
- 후속: SBOM 생성 + Sigstore 서명 검토.

### Scenario 4: ML 모델 변조 - 가짜 시그널 생성

1. 공격자가 호스트 침해 → `/var/lib/tradepilot/models/` 에 변조 모델 배치.
2. 추론 시 가짜 BUY 시그널 → 사용자 손실.

**방어**:
- 모델 파일 SHA256 검증(현재 미적용) — 후속(SEC-030-FOLLOWUP).
- 모델 디렉토리 read-only 마운트 + 별도 ML 학습 호스트 격리.

### Scenario 5: 봇 자동화 - 계정 탈취 시도

1. 공격자가 유출 자격증명(다른 사이트 유출) credential stuffing.
2. nginx zn_login (5r/min/IP) → IP 분산(프록시 풀)로 우회 시도.
3. 5회 실패 → 15분 잠금.

**방어**:
- ✅ 계정별 잠금 동작 (E0052 자동화 테스트).
- 후속: 로그인 시 비정상 IP 패턴 탐지(SIEM 연동) — SEC-031-FOLLOWUP.
- 후속: hCaptcha/reCAPTCHA 도입 검토.

---

## 5. 위협 우선순위 매트릭스

| 위협 | STRIDE | 영향 | 가능성 | 점수 | 우선순위 |
|---|:---:|:---:|:---:|:---:|:---:|
| 운영 환경 약한 JWT 시크릿 | S+E | 5 | 4 | 20 | P0 |
| Kill Switch LIVE 게이트웨이 미호출 | T+R | 5 | 5 | 25 | P0 |
| Gateway API Key 평문 비교 | S+I | 5 | 3 | 15 | P0 |
| Refresh token replay | S | 4 | 3 | 12 | P1 |
| WebSocket 토큰 로그 노출 | I | 4 | 3 | 12 | P1 |
| JWT alg 변조 | S | 5 | 2 | 10 | P1 |
| DB 에러 메시지 노출 | I | 3 | 4 | 12 | P1 |
| OTP 평문 로깅 | I | 4 | 2 | 8 | P1 |
| 한도 race condition | T | 4 | 2 | 8 | P2 |
| Idempotency race | T | 3 | 2 | 6 | P2 |
| localStorage XSS 토큰 탈취 | I | 4 | 2 | 8 | P2 |
| CSP Report-Only | I | 3 | 3 | 9 | P2 |

> 점수 = 영향(1-5) × 가능성(1-5). P0 ≥ 15, P1 ≥ 10, P2 ≥ 6.

---

## 6. 후속 점검 항목

| ID | 항목 | 담당 |
|---|---|---|
| SEC-026-FOLLOWUP | SIM→LIVE 7단계 검증 우회 가능성 점검 | QA |
| SEC-027-FOLLOWUP | Redis ACL 적용 | DBA |
| SEC-028-FOLLOWUP | audit_order_history append-only DB 트리거 | DBA |
| SEC-029-FOLLOWUP | 운영 DB 사용자 권한(SUPERUSER 여부) 점검 + bastion 도입 | DBA |
| SEC-030-FOLLOWUP | ML 모델 파일 SHA256 무결성 검증 | BackendSenior |
| SEC-031-FOLLOWUP | 로그인 비정상 패턴 탐지 (SIEM/Sentry) | DevLead |

---

## 7. 변경 이력

| 버전 | 일자 | 작성자 | 내용 |
|---|---|---|---|
| v1.0 | 2026-05-13 | QA (Security Review) | 최초 작성 - STRIDE + 자산 10종 + 시나리오 5종 |
