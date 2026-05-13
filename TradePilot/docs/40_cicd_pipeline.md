# 40. CI/CD 파이프라인 (TradePilot)

본 문서는 TradePilot 의 GitHub Actions 기반 CI/CD 파이프라인 구성, 트리거 조건,
필요 시크릿, 머지/배포 정책, 브랜치 전략을 정의한다.

> 워크플로우는 워크스페이스 루트 `/.github/workflows/` 에 위치하며,
> 모두 `paths: ['TradePilot/**']` 또는 그 하위 경로로 트리거를 한정한다.
> 워크스페이스의 다른 프로젝트(FootPrint / Shelfy / photomosaic / sand-pixel)에는 영향이 없다.

---

## 1. 워크플로우 한눈에 보기

| # | 파일 | 주요 트리거 | 주요 Job | 목표 SLA(소요) |
|---|---|---|---|---|
| 1 | `tradepilot-backend-ci.yml` | PR + main push (`backend/**`, `creon-gateway/**`) | `backend-test`, `gateway-test` | < 15 분 |
| 2 | `tradepilot-frontend-ci.yml` | PR + main push (`frontend/**`) | `frontend-build` | < 8 분 |
| 3 | `tradepilot-e2e-ci.yml` | PR (`frontend/**`, `qa/e2e/**`), 수동 | `playwright` | < 20 분 |
| 4 | `tradepilot-security.yml` | 매주 월 09:00 UTC, 수동, PR | `dependency-scan`, `secret-scan` | < 15 분 |
| 5 | `tradepilot-build-images.yml` | main push (`backend/`, `frontend/`), 수동 | `build-and-push` (matrix) | < 20 분 (env 승인 대기 별도) |
| 6 | `tradepilot-release.yml` | tag push `tradepilot-v*.*.*` | `prepare`, `publish-images`, `github-release` | < 25 분 |

---

## 2. 워크플로우 상세

### 2.1 `tradepilot-backend-ci.yml` — 백엔드 CI

- **목적**: backend / creon-gateway 코드 변경 시 lint + 단위 + 통합 + QA 회귀 테스트.
- **Job 1 backend-test**:
  - Python 3.11, postgres:15-alpine + redis:7-alpine 서비스 컨테이너 (헬스체크 포함).
  - 단계: checkout → setup-python → pip 캐시(`hashFiles('TradePilot/backend/pyproject.toml')`) → `pip install -e ".[dev]"` → ruff → black --check → 서비스 헬스 대기 → pytest unit → pytest integration → pytest qa.
  - 환경 변수: 테스트용 mock JWT/AES 키, 컨테이너 DB/Redis 접속 URL.
  - 아티팩트: `backend-test-reports` (junit xml, coverage xml).
- **Job 2 gateway-test**:
  - Linux 환경에서는 `pywin32` 미지원이므로 base 의존성만 설치.
  - 단계: checkout → setup-python → pip 캐시 → `pip install -e .` → pytest tests.
- **Concurrency**: 동일 ref 신규 push 시 이전 실행 자동 취소.

### 2.2 `tradepilot-frontend-ci.yml` — 프런트엔드 CI

- **목적**: ESLint, TypeScript 타입 체크, Next.js 프로덕션 빌드.
- **단계**: checkout → setup-node@v4 (npm 캐시, lock 기반) → `npm ci` → `npm run lint` → `npx tsc --noEmit` → `npm run build`.
- **Mock 환경**: `NEXT_PUBLIC_USE_MOCK=true` 로 백엔드 의존 없이 빌드.
- **아티팩트**: `frontend-build-report` (`.next` 사이즈 / `BUILD_REPORT.md`).

### 2.3 `tradepilot-e2e-ci.yml` — E2E (Playwright)

- **목적**: 회귀 시나리오 자동화 (chromium / firefox / webkit / 768·모바일 viewport).
- **단계**: checkout → setup-node → frontend `npm ci` → frontend `npm run build` → e2e 의존성 설치 → Playwright 브라우저 캐시 복원 → `npx playwright install --with-deps` → frontend `npm start` 백그라운드 → 헬스 대기(`scripts/ci/wait-for.sh`) → `npx playwright test --reporter=github,list,html,junit`.
- **실패 시**: `playwright-report/`, `reports/`, `test-results/` 업로드 (trace 포함).
- **수동 dispatch**: `project` 입력으로 특정 프로젝트만 실행 가능.

### 2.4 `tradepilot-security.yml` — 보안 스캔

- **트리거**: 매주 월 09:00 UTC (KST 18:00) + PR(`TradePilot/**`) + 수동.
- **Job 1 dependency-scan**:
  - `pip-audit` (backend, creon-gateway) → JSON 산출.
  - `npm audit --audit-level=moderate` (frontend) → JSON 산출.
  - `aquasecurity/trivy-action@0.20.0` 으로 `TradePilot` 파일시스템 SARIF 스캔 → Code Scanning 업로드.
- **Job 2 secret-scan**: `gitleaks/gitleaks-action@v2` 전체 히스토리 점검.
- **정책**: 신규 HIGH/CRITICAL 취약점은 PR 머지 차단 검토 (수동), Code Scanning 알림은 DevLead 가 매주 트리아지.

### 2.5 `tradepilot-build-images.yml` — 이미지 빌드 & 푸시

- **트리거**: main push (`backend/`, `frontend/`) + 수동.
- **Job build-and-push** (matrix: backend / frontend):
  - `environment: production` 승인 게이트.
  - `docker/setup-qemu-action@v3`, `docker/setup-buildx-action@v3`, `docker/login-action@v3`.
  - `docker/metadata-action@v5` 로 `sha-<short>`, `latest`(default branch), branch 태그 생성.
  - `docker/build-push-action@v5` 로 GHCR 푸시 (`ghcr.io/jrshow76/tradepilot-{backend,frontend}`).
  - `provenance: true`, `sbom: true` 빌트인 + `anchore/sbom-action@v0` 로 syft SPDX 별도 첨부.
  - Trivy 이미지 스캔 SARIF 업로드 (실패해도 빌드 자체는 성공).
- **수동 dispatch**: `target` 입력(`backend`/`frontend`/`both`).

### 2.6 `tradepilot-release.yml` — 릴리스

- **트리거**: tag push `tradepilot-v*.*.*` (예: `tradepilot-v1.0.0`).
- **prepare**: 직전 `tradepilot-v*` 태그 추출.
- **publish-images** (matrix, production 승인 게이트): 동일 이미지 빌드를 release 태그(`tradepilot-vX.Y.Z`, `vX.Y.Z`, `latest`, `sha-<short>`)로 푸시 + SBOM 첨부.
- **github-release**:
  - 직전 태그 ~ 현재 사이의 `TradePilot/` 경로 커밋만 변경 로그로 추출.
  - `softprops/action-gh-release@v2` 로 Release 발행 (SBOM, CHANGELOG 첨부).
  - 태그명에 `-rc` / `-beta` 포함 시 prerelease 로 마킹.

---

## 3. 필요한 GitHub Secrets / Variables

### 3.1 Repository / Organization Secrets

| 이름 | 용도 | 사용 워크플로우 |
|---|---|---|
| `GITHUB_TOKEN` | 기본 토큰 (자동 제공) | 전부 |
| `GHCR_TOKEN` | GHCR 푸시 (PAT, `write:packages`). 미설정 시 `GITHUB_TOKEN` fallback | build-images, release |
| `STAGING_SSH_KEY` | (장래) 스테이징 SSH 배포용 | 배포 워크플로우 추가 시 |
| `PROD_SSH_KEY` | (장래) 운영 SSH 배포용 | 배포 워크플로우 추가 시 |

> 실거래에 사용되는 시크릿(`JWT_SECRET`, `AES_KEY`, `CREON_GATEWAY_API_KEY`, DB 비밀번호 등)은 **CI 에 절대 주입하지 않는다**.
> CI 의 `JWT_SECRET`/`AES_KEY` 는 테스트 전용 mock 값으로 워크플로우 내부에 평문 명시되어 있다.
> 운영 환경 시크릿은 환경별 환경변수 또는 Vault / SOPS 연동을 통해 배포 시점에만 주입한다.

### 3.2 Environments

- **production**
  - `tradepilot-build-images.yml`, `tradepilot-release.yml` 의 푸시 단계가 의존.
  - 보호 규칙: 필수 리뷰어 = PM + DevLead, wait timer 옵션 활용 권장.
  - 배포용 시크릿은 본 환경 전용 시크릿으로만 보관 (`PROD_*`).

---

## 4. 머지 정책 (main 브랜치 보호 규칙)

권장 GitHub branch protection 설정 (`Settings → Branches → main`):

- **Require a pull request before merging**: ✅
  - Required approvals: **2** (Code Owner 1 + 일반 리뷰어 1)
  - Dismiss stale reviews on new commits: ✅
  - Require review from Code Owners: ✅ (`.github/CODEOWNERS` 사용)
- **Require status checks to pass before merging**: ✅
  - 필수 체크:
    - `tradepilot-backend-ci / backend (lint + unit + integration)`
    - `tradepilot-backend-ci / creon-gateway (unit)` (gateway 변경 시)
    - `tradepilot-frontend-ci / frontend (lint + type-check + build)`
    - `tradepilot-e2e-ci / e2e (playwright)` (frontend / e2e 변경 시)
  - Require branches to be up to date: ✅
- **Require conversation resolution before merging**: ✅
- **Require signed commits**: 권장 (운영 정책)
- **Require linear history**: 권장 (squash 머지 통일)
- **Restrict who can push to matching branches**: 관리자만
- **Do not allow bypassing the above settings**: ✅

매매 정책 변경(`docs/14_exception_policy.md`, `docs/15_trading_policy.md`, `docs/30_operations_runbook.md`,
주문 라우터 / 한도 / 킬스위치 코드)은 PR 템플릿 체크박스 + CODEOWNERS 매칭으로 PM + DevLead 승인을 강제한다.

---

## 5. 브랜치 전략

권장: **Trunk-based + 단명 feature 브랜치**.

| 브랜치 | 용도 | 보호 |
|---|---|---|
| `main` | 항상 배포 가능 상태. release 태그 발행 기준. | 보호(위 4절) |
| `feature/<issue>-<요약>` | 일반 기능 / 버그 수정. 평균 수명 < 3일. | 미보호 |
| `hotfix/<issue>` | 운영 핫픽스 (P0/P1). PR 후 즉시 main 머지 → 즉시 release 태그. | 미보호 |
| `release/x.y.z` | (선택) 릴리스 안정화가 필요할 때만 단명 사용. | 미보호 |

**머지 방식**: `Squash and merge` 통일. PR 제목 = squash 커밋 메시지가 되므로,
`<scope>: <요약>` 형식 (예: `backend(orders): idempotency 키 검증 추가`) 권장.

**태그 규칙**:
- 릴리스 태그: `tradepilot-v<MAJOR>.<MINOR>.<PATCH>` (예: `tradepilot-v1.2.0`).
- pre-release: `tradepilot-v1.2.0-rc.1`, `tradepilot-v1.2.0-beta.1` (release 워크플로우가 자동 prerelease 표기).

---

## 6. 캐시 / 성능 전략

| 캐시 대상 | 키 | 효과 |
|---|---|---|
| pip (backend) | `${{ runner.os }}-pip-backend-3.11-${{ hashFiles('TradePilot/backend/pyproject.toml') }}` | 의존성 설치 1~2분 → 30초 |
| pip (gateway) | `${{ runner.os }}-pip-gateway-${{ hashFiles('TradePilot/creon-gateway/pyproject.toml') }}` | 동일 |
| npm | `setup-node@v4` 빌트인, `package-lock.json` 해시 기반 | `npm ci` 가속 |
| Playwright 브라우저 | `~/.cache/ms-playwright` ← `hashFiles('TradePilot/qa/e2e/package.json')` | 브라우저 다운로드 회피 |
| Docker layer | `type=gha,scope=tradepilot-<component>` | 베이스 레이어 재사용 |

---

## 7. 보안 / 매매 안전 가드

- **CI 환경에 운영 시크릿 절대 주입 금지** (테스트 mock 값만 사용).
- **dependency-scan**: 정기 + PR 양쪽에서 동작. SARIF 는 GitHub Security 탭으로 통합.
- **secret-scan**: 모든 PR 에 대해 전체 히스토리 점검 (gitleaks).
- **이미지 스캔**: 빌드/릴리스 단계에서 Trivy HIGH/CRITICAL 점검 후 SARIF 업로드.
- **production environment 승인 게이트**: 이미지 푸시 / 릴리스 단계에서 PM/DevLead 수동 승인 필요.
- **PR 템플릿의 매매 정책 영향 체크박스**: 작성자 누락 시 리뷰어가 반려.

---

## 8. 로컬에서 동일 실행

CI 와 동일한 명령을 로컬에서 그대로 사용할 수 있도록 헬퍼 스크립트를 제공한다.

```bash
# 백엔드 (DB/Redis 가 docker-compose 로 떠 있다고 가정)
./TradePilot/scripts/ci/run-backend-tests.sh        # 전체
./TradePilot/scripts/ci/run-backend-tests.sh unit
./TradePilot/scripts/ci/run-backend-tests.sh lint

# 프런트엔드
./TradePilot/scripts/ci/run-frontend-tests.sh       # lint + type + build
./TradePilot/scripts/ci/run-frontend-tests.sh build

# E2E (frontend 자동 빌드 + 기동까지 처리)
./TradePilot/scripts/ci/run-e2e.sh
./TradePilot/scripts/ci/run-e2e.sh chromium

# 헬스 대기 유틸
./TradePilot/scripts/ci/wait-for.sh localhost 5432 60
```

---

## 9. 향후 확장 (TODO)

- [ ] 스테이징 자동 배포 (compose / k8s) 워크플로우 추가 (`STAGING_SSH_KEY` 활용).
- [ ] k6 부하 테스트(`qa/load/k6_orders_burst.js`) 야간 정기 워크플로우 분리.
- [ ] 백엔드 ML 모델 산출물(SAGE / SBOM) 별도 릴리스 채널.
- [ ] Slack / Telegram CI 결과 알림 (현재는 GitHub 이메일/노티에만 의존).
- [ ] CodeQL JavaScript / Python 분석 워크플로우 추가.
