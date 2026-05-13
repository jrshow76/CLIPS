# TradePilot 보안 스코어카드

> 문서 ID: 74_SECURITY_SCORECARD
> 버전: v1.0
> 작성자: QA (Security Review)
> 검토자: PM, DevLead, BackendSenior, DBA
> 최종 수정일: 2026-05-13
> 평가 기준일: 2026-05-13

본 문서는 TradePilot의 보안 성숙도를 카테고리별 0~100점으로 측정하고, 운영 진입 GO/NO-GO 판정을 제공한다.

---

## 1. 카테고리별 점수

### 1.1 OWASP Top 10 매핑

| 카테고리 | 점수 | 등급 | 비고 |
|---|:---:|:---:|---|
| A01 Broken Access Control | 85 | A- | X-Trade-Mode 가드, IDOR 방어 OK. 후속: 관리자 API 2FA. |
| A02 Cryptographic Failures | 65 → **80** | C+ → B | 자동수정 후 (JWT alg 화이트리스트, 운영 시크릿 검증). 후속: RS256, mTLS. |
| A03 Injection | 90 | A | SQLAlchemy ORM 중심. partitioner f-string은 입력 검증된 안전 영역. |
| A04 Insecure Design | 60 → **65** | C → C+ | **Kill Switch SLA 미보장(SEC-003) 미해소** 시 60점 유지. |
| A05 Security Misconfiguration | 60 → **75** | C → B- | 자동수정 후 (CORS 와일드카드 차단, fail-fast). 후속: Vault. |
| A06 Vulnerable Components | 75 | B- | CI에서 정기 스캔 OK. SBOM/서명 미적용. |
| A07 Identification & Auth | 70 → **80** | B- → B | 자동수정 후 (refresh replay 탐지). 후속: 완전 토큰 회전, 2FA. |
| A08 Software & Data Integrity | 80 | B | 멱등성 + 백업 SHA256 OK. CI artifact 서명 미적용. |
| A09 Security Logging | 55 → **75** | C- → B- | 자동수정 후 (토큰 마스킹, DB 에러 비노출, 토큰 로깅 제거). |
| A10 SSRF | 95 | A+ | 외부 호출 표면 적음, 화이트리스트 운영 가능. |

### 1.2 매매 시스템 특화

| 영역 | 점수 | 등급 | 비고 |
|---|:---:|:---:|---|
| 주문 페이로드 무결성 | 85 | A- | Pydantic 검증 OK. |
| 모드 가드 (X-Trade-Mode) | 90 | A | E0006 자동화 테스트 통과. |
| 한도 검사 동시성 | 60 | C | race condition 가능(SEC-012). |
| Kill Switch SLA 5초 | **40** | F | LIVE 모드 게이트웨이 미호출(SEC-003). **운영 진입 차단.** |
| SIM→LIVE 7단계 검증 | 70 | B- | 별도 점검 필요(SEC-026-FOLLOWUP). |
| 게이트웨이 인증 | 60 → **80** | C → B | 자동수정 후 (timing-safe). mTLS 후속. |
| Redis Pub/Sub 격리 | 80 | B | 운영 compose에서 호스트 포트 제거. ACL 후속. |
| WebSocket 인증 | 70 → **85** | B- → A- | 자동수정 후 (토큰 로그 마스킹). |

### 1.3 프론트엔드/인프라

| 영역 | 점수 | 등급 | 비고 |
|---|:---:|:---:|---|
| 프론트엔드 XSS | 80 | B | dangerouslySetInnerHTML 미사용 확인. |
| 프론트엔드 CSRF | 85 | A- | JWT 헤더 방식 + same-origin. |
| localStorage 토큰 저장 | 60 | C | XSS 시 토큰 탈취 위험(SEC-015). |
| CSP | 50 | F | Report-Only + unsafe-inline. Enforce 전환 후속. |
| TLS 구성 | 95 | A+ | Mozilla Intermediate, A+ 목표. |
| nginx 보안 헤더 | 90 | A | HSTS, COOP, CORP 등 풀세트. |
| Docker 평문 시크릿 | 60 | C | Vault 도입 후속(SEC-017). |
| 백업 암호화 | 90 | A | GPG/age 강제, SHA256 + S3 IAM 최소권한. |

---

## 2. 종합 점수

| 영역 | 가중치 | 점수 (자동수정 후) | 가중 점수 |
|---|:---:|:---:|:---:|
| OWASP Top 10 평균 | 40% | 80.5 | 32.2 |
| 매매 시스템 특화 평균 | 35% | 73.8 | 25.8 |
| 프론트엔드/인프라 평균 | 25% | 76.3 | 19.1 |
| **총점** | 100% | - | **77.1** |

> **종합 등급: B (77/100)** — 운영 가능 임계(80) 미달.

### 2.1 Kill Switch (SEC-003) 해소 시 예상 점수

| 영역 | 가중치 | 점수 (SEC-003 해소 후) | 가중 점수 |
|---|:---:|:---:|:---:|
| OWASP Top 10 평균 | 40% | 80.5 | 32.2 |
| 매매 시스템 특화 평균 | 35% | 80.0 (Kill Switch 90점) | 28.0 |
| 프론트엔드/인프라 평균 | 25% | 76.3 | 19.1 |
| **총점** | 100% | - | **79.3** |

> **종합 등급: B+ (79/100)** — 운영 가능 임계 거의 도달.

---

## 3. 운영 GO/NO-GO 판정

### 3.1 판정 결과

> **현재 시점 판정: NO-GO**
>
> 사유:
> 1. **SEC-003 (Kill Switch LIVE 게이트웨이 미호출)** — Critical 미해소.
> 2. **SEC-001 자동수정 적용** 했으나 운영 환경 시크릿이 실제로 교체되었는지 별도 확인 필요.
> 3. SEC-004 (Refresh token rotation) — 부분 적용. 완전 회전은 후속.
>
> 운영 진입 임계 충족 후 GO 변경 가능.

### 3.2 운영 진입 필수 조치 (NO-GO → GO 전환 조건)

| ID | 조치 | 담당 | 마감 |
|---|---|---|---|
| **GATE-1** | SEC-003: Kill Switch가 LIVE 모드에서 게이트웨이 cancel_order 호출하도록 구현 + 5초 SLA 회로차단기 + 통합 테스트 | BackendSenior | 운영 진입 전 |
| **GATE-2** | SEC-001 운영 환경 시크릿 실제 교체 확인 (`_validate_production_settings()` 통과 + 운영 컨테이너 기동 로그 확인) | DevOps | 운영 진입 전 |
| **GATE-3** | SEC-004 완전 토큰 회전(refresh 발급 시 기존 세션 폐기 + 새 refresh 발급) | BackendSenior | 운영 진입 전 |
| **GATE-4** | SEC-009-FOLLOWUP: structlog processor 자동 마스킹 필터(token/password/otp) | BackendDev | 운영 진입 전 |
| **GATE-5** | qa/53 P0 회귀 테스트 100% 통과 + 본 보고서의 자동수정으로 인한 회귀 없음 확인 | QA | 운영 진입 전 |

### 3.3 권장 추가 조치 (GO 가능하나 1주 내 권장)

- SEC-005-FOLLOWUP: CORS origin 빈 리스트 fail-fast
- SEC-007-FOLLOWUP: 프론트엔드 WebSocket 인증을 첫 메시지 방식으로 전환
- SEC-016: CSP Enforce 전환 (현재 Report-Only)
- SEC-026-FOLLOWUP: SIM→LIVE 7단계 검증 우회 가능성 점검

---

## 4. 사인오프 양식

### 4.1 검토자 서명

| 역할 | 이름 | 검토일 | 의견 (NO-GO 사유 / GO 동의) | 서명 |
|---|---|---|---|---|
| QA Lead (보고서 작성자) | _________ | 2026-05-13 | NO-GO — GATE-1~5 미해소 | _________ |
| DevLead | _________ | _________ | _________ | _________ |
| BackendSenior | _________ | _________ | _________ | _________ |
| DBA | _________ | _________ | _________ | _________ |
| PM (최종 GO/NO-GO 결정) | _________ | _________ | _________ | _________ |

### 4.2 GO 전환 기록 (GATE-1~5 해소 후 작성)

| GATE ID | 해소 일자 | 검증 방법 | 검증자 |
|---|---|---|---|
| GATE-1 | _________ | 통합 테스트 PR + 게이트웨이 호출 로그 | _________ |
| GATE-2 | _________ | 운영 컨테이너 기동 로그 (RuntimeError 미발생) | _________ |
| GATE-3 | _________ | refresh 시 새 토큰 발급 + 기존 세션 폐기 테스트 | _________ |
| GATE-4 | _________ | 자동 마스킹 필터 단위 테스트 + 로그 샘플 검증 | _________ |
| GATE-5 | _________ | qa/53 회귀 결과 (P0 100%) | _________ |

### 4.3 최종 GO 결정

```
PM 서명: ____________________________
일자:    2026-__-__
운영 진입 일자: 2026-__-__
```

---

## 5. 점수 추이 (분기별 갱신)

| 분기 | 종합 점수 | 등급 | 주요 변동 |
|---|:---:|:---:|---|
| 2026 Q2 (현재) | 77 | B | 최초 평가, 9건 자동수정 |
| 2026 Q3 (목표) | 85 | B+ | GATE-1~5 + Vault + RS256 |
| 2026 Q4 (목표) | 90 | A- | mTLS, CSP Enforce, 외부 펜테스트 통과 |

---

## 6. 변경 이력

| 버전 | 일자 | 작성자 | 내용 |
|---|---|---|---|
| v1.0 | 2026-05-13 | QA (Security Review) | 최초 작성 - 종합 77점 (B), NO-GO 판정 |
