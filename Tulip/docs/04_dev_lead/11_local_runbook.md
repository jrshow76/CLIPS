# 로컬 개발자 런북 (Local Developer Runbook)

| 항목 | 내용 |
|---|---|
| 문서명 | Tulip+ 로컬 개발 환경 셋업 런북 |
| 문서 ID | DEV-11 |
| 버전 | v0.1 Draft |
| 작성일 | 2026-05-11 |
| 작성자 | DevLead Agent |
| 검토자 | BackendSenior, FrontendSenior, DBA, QA |
| 입력 | `04_dev_lead/08_infra_and_tooling_decisions.md`, `Tulip/backend/Makefile`, `Tulip/backend/docker-compose.yml`, `Tulip/frontend/Makefile`, 서비스별 README |
| 목표 | **신규 개발자가 git clone 후 20분 이내에 admin/opac 데모 화면에 진입** |
| 상태 | Phase 1 종료 시점 baseline |

---

## 1. 문서 목적

본 런북은 **신규 개발자(가상 페르소나: 첫날 오리엔테이션 직후)**가 Tulip+ 모노레포를 클론하여 로컬에서 **사서 로그인 → 회원 등록**까지 데모 가능한 상태로 만드는 절차를 단계별로 제공한다. 모든 명령은 **macOS / Linux (또는 WSL2 Ubuntu)** 기준이며, Windows native 환경은 docker desktop + WSL2 조합을 권장한다.

> 예상 소요 시간: **약 20분** (네트워크 양호, Docker 이미지 첫 pull 포함). 두 번째 셋업 이후는 5분 이내.

---

## 2. 필수 도구 사전 설치 (PreReq, 1단계)

| 도구 | 버전 | 확인 명령 | 설치 가이드 |
|---|---|---|---|
| Git | 2.40+ | `git --version` | `brew install git` / `apt install git` |
| **JDK 21 (Temurin)** | 21.0.x LTS | `java -version` | `brew install --cask temurin@21` / `sdkman install java 21.0.4-tem` |
| **Node.js** | 20 LTS | `node -v` (v20.x.x) | `nvm install 20 && nvm use 20` (`.nvmrc` 자동 인식) |
| **pnpm** | 9.15+ | `pnpm -v` | `corepack enable && corepack prepare pnpm@9.15.0 --activate` |
| **Docker** | 24.0+ | `docker --version` | Docker Desktop (macOS/Windows) or `docker-ce` (Linux) |
| Docker Compose v2 | 2.20+ | `docker compose version` | Docker Desktop 동봉 / Linux: `apt install docker-compose-plugin` |
| Make | GNU make 3.81+ | `make --version` | macOS 기본 / `apt install build-essential` |
| (선택) jq | 1.6+ | `jq --version` | `brew install jq` / `apt install jq` |
| (선택) httpie | 3.x | `http --version` | `brew install httpie` / `pip install httpie` |
| (선택) k6 | 0.50+ | `k6 version` | `brew install k6` (부하 테스트 시) |

### 2.1 사전 점검 스크립트 (제안)

```bash
# Tulip/scripts/check-prereq.sh (참고)
java -version 2>&1 | grep -E '"21\.' && echo "Java 21 OK" || echo "[FAIL] Java 21 필요"
node -v | grep -E '^v20\.'        && echo "Node 20 OK" || echo "[FAIL] Node 20 필요"
pnpm -v | grep -E '^9\.'          && echo "pnpm 9 OK"  || echo "[FAIL] pnpm 9 필요"
docker --version                  && echo "Docker OK"  || echo "[FAIL] Docker 미설치"
```

### 2.2 디스크·메모리 권장

| 항목 | 최소 | 권장 |
|---|---|---|
| 디스크 여유 | 15GB | 30GB |
| RAM | 8GB | 16GB |
| CPU | 4 core | 8 core |
| OS | macOS 13+, Ubuntu 22.04+, WSL2 (Win 11) | macOS 14+, Ubuntu 24.04 |

---

## 3. 백엔드 셋업 (2단계, 약 5분)

### 3.1 리포 클론

```bash
git clone https://github.com/<org>/CLIPS.git
cd CLIPS/Tulip/backend
```

> 모노레포 루트는 `CLIPS/`이며, 본 프로젝트는 `CLIPS/Tulip/`이다.

### 3.2 인프라 컨테이너 기동

```bash
make up
# 또는: docker compose up -d
```

`Tulip/backend/docker-compose.yml`이 다음 컨테이너를 백그라운드로 기동한다:

| 컨테이너 | 포트 | healthcheck |
|---|---|---|
| `tulip-postgres` | 5432 | `pg_isready` 5s 간격 |
| `tulip-redis` | 6379 | `redis-cli ping` |
| `tulip-kafka` (KRaft 모드) | 9092 | `kafka-topics --list` |
| `tulip-keycloak` | 8088 → 8080 | 미설정 (start-dev) |
| `tulip-minio` | 9000 / 9001 | (healthcheck 미설정) |
| `tulip-prometheus` | 9090 | - |
| `tulip-grafana` | 3001 | - |

상태 확인:

```bash
make ps
# 또는: docker compose ps
```

모든 컨테이너 `Up (healthy)` 또는 `Up`이 되면 성공. **Kafka 첫 기동은 20~30초 추가 소요**된다.

### 3.3 Gradle 빌드

```bash
./gradlew build
# 처음 1회: 약 3~5분 (의존성 다운로드), 이후: 1~2분 (캐시)
```

빌드 산출 확인:

```bash
ls services/*/build/libs/*.jar
# tenant-service-*.jar / iam-service-*.jar / member-service-*.jar
# code-policy-service-*.jar / api-gateway-*.jar
```

### 3.4 (선택) Flyway 마이그레이션 수동 적용

각 서비스 부팅 시 자동 적용되지만, DB만 초기화한 상태에서 검증할 때 사용:

```bash
make seed
# = docker compose exec postgres psql -U tulip -d tulip < db/migration/V1__init_common.sql
```

`psql` 직접 접속:

```bash
make psql
# tulip 데이터베이스의 prompt 진입
\dt
# tlp_cmn_tenant / tlp_cmn_library / tlp_cmn_audit_log 등 확인
```

---

## 4. 서비스 기동 (3단계, 약 5분)

### 4.1 권장 부팅 순서

각 서비스는 독립 부팅 가능하지만, **데모 흐름 검증을 위한 권장 순서**:

```
1) api-gateway     :9100
2) iam-service     :8101  ← Keycloak realm import 의존
3) tenant-service  :8102
4) member-service  :8103
5) code-policy-service :8104
```

### 4.2 부팅 명령 (5개 터미널 또는 백그라운드)

각각 별도 터미널에서:

```bash
# Terminal 1
./gradlew :services:api-gateway:bootRun

# Terminal 2
./gradlew :services:iam-service:bootRun

# Terminal 3
./gradlew :services:tenant-service:bootRun

# Terminal 4
./gradlew :services:member-service:bootRun

# Terminal 5
./gradlew :services:code-policy-service:bootRun
```

> **팁**: `tmux` 또는 IntelliJ "Compound Run Configuration"으로 한 번에 기동 가능. 백그라운드 일괄 실행은 `make dev`가 추가될 예정 (TD-Phase2)

### 4.3 헬스체크

```bash
curl -s http://localhost:9100/actuator/health | jq .  # gateway
curl -s http://localhost:8101/actuator/health | jq .  # iam
curl -s http://localhost:8102/actuator/health | jq .  # tenant
curl -s http://localhost:8103/actuator/health | jq .  # member
curl -s http://localhost:8104/actuator/health | jq .  # code-policy
```

모두 `{"status":"UP"}` 응답이면 성공. iam-service는 Keycloak 의존이므로 Keycloak 컨테이너의 realm import 완료를 기다린다 (`docker logs -f tulip-keycloak` 에서 `Imported realm 'tulip'` 출력 확인).

### 4.4 OpenAPI 문서 확인

```bash
open http://localhost:9100/swagger-ui.html
# Gateway가 iam/tenant OpenAPI를 집계
```

각 서비스 단독:

| 서비스 | Swagger UI | OpenAPI JSON |
|---|---|---|
| iam-service | http://localhost:8101/swagger-ui.html | /v3/api-docs |
| tenant-service | http://localhost:8102/swagger-ui.html | /v3/api-docs |
| member-service | http://localhost:8103/swagger-ui.html | /v3/api-docs |
| code-policy-service | http://localhost:8104/swagger-ui.html | /v3/api-docs |

---

## 5. 프론트엔드 셋업 (4단계, 약 5분)

### 5.1 의존성 설치

```bash
cd CLIPS/Tulip/frontend
make install
# 또는: pnpm install
# 첫 회: 약 60~80초
```

### 5.2 환경 변수 파일 생성

```bash
cp apps/admin/.env.example apps/admin/.env.local
cp apps/opac/.env.example  apps/opac/.env.local
```

`apps/admin/.env.local` 기본값:

```
NEXT_PUBLIC_API_BASE_URL=http://localhost:9100/api
NEXT_PUBLIC_KEYCLOAK_URL=http://localhost:8088
NEXT_PUBLIC_KEYCLOAK_REALM=tulip
NEXT_PUBLIC_KEYCLOAK_CLIENT_ID=admin-web
NEXT_PUBLIC_USE_MOCK=false
```

> `NEXT_PUBLIC_USE_MOCK=true`로 설정하면 백엔드 없이도 UI를 둘러볼 수 있다 (`@tulip/api-client` mock 모드).

### 5.3 개발 서버 기동

두 앱 동시 기동:

```bash
make dev
# = pnpm run dev (Turborepo가 admin:3000 + opac:3001 병렬)
```

개별 기동:

```bash
make dev-admin  # http://localhost:3000
make dev-opac   # http://localhost:3001
```

빌드 검증 (선택):

```bash
make build
# packages 빌드 → apps 빌드
```

---

## 6. 데모 시나리오 실행 (5단계, 약 3분)

### 6.1 Keycloak 데모 사용자

Phase 1 realm import에 포함된 기본 사용자:

| 사용자 | 비밀번호 | 역할 | 테넌트 |
|---|---|---|---|
| `librarian@demo-tenant-1` | `Tulip!2026` | TENANT_ADMIN, LIB_ADMIN, MEMBER_MANAGE | demo-tenant-1 |
| `librarian@demo-tenant-2` | `Tulip!2026` | TENANT_ADMIN, LIB_ADMIN | demo-tenant-2 |
| `sysadmin@platform` | `Tulip!2026` | SYS_ADMIN | (플랫폼 관리자) |
| `patron@demo-tenant-1` | `Tulip!2026` | PATRON | demo-tenant-1 |

> 실제 import 파일: `Tulip/backend/docker/keycloak/tulip-realm.json`

### 6.2 Admin 사서 로그인 → 회원 등록 시연

1. 브라우저: http://localhost:3000
2. 자동 리다이렉트: `/login`
3. "로그인" 클릭 → Keycloak `realms/tulip/protocol/openid-connect/auth`로 이동
4. `librarian@demo-tenant-1` / `Tulip!2026` 로그인
5. 콜백: `/auth/callback?code=...&state=...` → 토큰 발급 (HttpOnly Cookie + 메모리)
6. `/dashboard` 진입 — KPI 카드 4개 표시
7. 좌측 사이드바 **회원 관리** 클릭 → `/access/members`
8. **회원 등록** 버튼 → 모달 입력 → 저장 → 토스트 + 자동 새로고침
9. 검색·필터·정렬 시연
10. 회원 상세 진입 → 수정 → 저장
11. **로그아웃** → 토큰 무효화 (`/api/v1/auth/logout` → JTI 블랙리스트)

### 6.3 OPAC 시연 (보조)

1. 브라우저: http://localhost:3001
2. 메인 페이지 → 헤더·푸터·네비 렌더 확인
3. `/login` → `patron@demo-tenant-1` 로그인
4. `/search` 검색 placeholder (Phase 2에서 실제 검색 활성)
5. `/me` 마이라이브러리 placeholder

### 6.4 API 직접 호출 (curl 시연)

```bash
# 1) PKCE 시작
curl -s -X POST http://localhost:9100/api/v1/auth/login/initiate \
     -H 'Content-Type: application/json' -d '{}' | jq .

# 응답의 authorizeUrl을 브라우저에서 열어 로그인 → 콜백에서 code 수령

# 2) /api/v1/auth/login/callback → access_token, refresh_token

# 3) 토큰으로 내 프로필 조회
ACCESS_TOKEN=eyJ...
curl -s http://localhost:9100/api/v1/auth/me -H "Authorization: Bearer $ACCESS_TOKEN" | jq .

# 4) 회원 목록
curl -s http://localhost:9100/api/v1/members?limit=10 -H "Authorization: Bearer $ACCESS_TOKEN" | jq .

# 5) 테넌트 정보
curl -s http://localhost:9100/api/v1/tenants/me -H "Authorization: Bearer $ACCESS_TOKEN" | jq .
```

---

## 7. 관리자 콘솔 단축 링크

| 서비스 | URL | 계정 |
|---|---|---|
| Admin 앱 | http://localhost:3000 | (Keycloak) |
| OPAC | http://localhost:3001 | (Keycloak) |
| Gateway Swagger UI | http://localhost:9100/swagger-ui.html | (인증 후) |
| Keycloak Admin | http://localhost:8088 | `admin` / `admin` |
| Keycloak Realm | http://localhost:8088/admin/master/console/#/tulip | 동 |
| MinIO Console | http://localhost:9001 | `admin` / `admin12345` (compose env 기준) |
| Mailhog (있을 시) | http://localhost:8025 | - |
| Prometheus | http://localhost:9090 | - |
| Grafana | http://localhost:3001\* | `admin` / `admin` |
| PostgreSQL | localhost:5432 | `tulip` / `tulip` |

> \* Grafana는 Phase 1 docker-compose에서 admin 앱과 포트 충돌(3001)이 있을 수 있어 환경에 따라 3002로 매핑할 수 있음 — 트러블슈팅 §8.1 참조.

---

## 8. 트러블슈팅 FAQ

### 8.1 포트 충돌

증상: `Error starting userland proxy: listen tcp4 0.0.0.0:5432: bind: address already in use`

원인: 호스트에 이미 PostgreSQL/Redis가 떠있거나 Grafana(3001)와 OPAC 앱이 동일 포트 사용.

해결:
- **호스트 서비스 중지**: `brew services stop postgresql@15` 또는 `systemctl stop postgresql`
- **포트 변경**: `docker-compose.yml`에서 `"5432:5432"` → `"15432:5432"`로 변경하고 `application.yml`의 `spring.datasource.url` 동기화
- **Grafana 포트 충돌**: docker-compose에서 grafana 매핑을 `3001:3000` → `3002:3000`으로 변경

### 8.2 Keycloak realm import 실패

증상: iam-service 부팅 시 `401 Unauthorized from Keycloak` 또는 사용자 로그인 시 `Invalid user credentials`

원인:
- Keycloak이 `start-dev --import-realm`으로 부팅되지만, 이미 realm이 존재하면 import 스킵
- `tulip-realm.json` 파일이 마운트되지 않음

해결:

```bash
# 1) Keycloak 컨테이너 데이터 초기화
docker compose down
docker volume rm tulip_keycloak-data
docker compose up -d keycloak

# 2) import 로그 확인
docker logs -f tulip-keycloak | grep -i "import"

# 3) 수동 import (UI 사용)
# http://localhost:8088 → admin/admin → Realm → "Create Realm" → JSON 업로드
```

### 8.3 Flyway 마이그레이션 오류

증상: `FlywayException: Validate failed: Detected resolved migration not applied to database`

원인: 마이그레이션 파일이 변경되었거나 체크섬 불일치.

해결:

```bash
# 개발 환경에서만 허용 — 운영 절대 금지
./gradlew :services:tenant-service:flywayRepair
# 또는 DB 초기화
make nuke && make up
```

### 8.4 Kafka 토픽 생성 안 됨

증상: Outbox publisher가 `UnknownTopicOrPartitionException`

원인: `KAFKA_CFG_AUTO_CREATE_TOPICS_ENABLE: "true"` 설정에도 KRaft 모드 초기화 지연.

해결:

```bash
# 토픽 수동 생성
docker exec -it tulip-kafka kafka-topics.sh \
  --bootstrap-server kafka:9092 --create \
  --topic tulip.tenant.tenant.created --partitions 3 --replication-factor 1

# 토픽 목록 확인
docker exec -it tulip-kafka kafka-topics.sh --bootstrap-server kafka:9092 --list
```

### 8.5 JWT 검증 실패 (Gateway 401)

증상: `Invalid JWT signature` 또는 `Invalid audience`

원인:
- iam-service가 발급한 토큰의 issuer/audience가 Gateway 설정과 불일치
- Keycloak realm key가 회전됨

해결:

```bash
# 1) 현재 토큰 디코딩 (jwt.io 또는 다음 명령)
echo $ACCESS_TOKEN | cut -d. -f2 | base64 -d 2>/dev/null | jq .

# 2) Gateway 설정 확인
grep -A5 'expected-audiences' Tulip/backend/services/api-gateway/src/main/resources/application.yml

# 3) JWKS 캐시 무효화 (Gateway 재시작)
./gradlew :services:api-gateway:bootRun --rerun-tasks
```

### 8.6 RLS로 회원 0건 응답

증상: 로그인은 성공하지만 회원 목록이 비어 있음

원인: JWT의 `tenantId` claim 누락 또는 Gateway가 `X-Tenant-Id` 헤더를 다운스트림에 전파하지 못함.

해결:

```bash
# 1) Gateway 로그에서 헤더 전파 확인
docker logs -f <gateway> | grep "X-Tenant-Id"

# 2) iam-service의 토큰 발급 시 claim 확인
# /api/v1/auth/me 응답에 tenantId 포함 여부

# 3) 수동으로 SET 후 psql 검증
make psql
SELECT set_config('app.current_tenant', '1', false);
SELECT * FROM mbr_member LIMIT 5;
```

### 8.7 프론트엔드 hot-reload 안 됨

증상: 파일 수정해도 브라우저 갱신 안 됨.

원인: WSL2 + Windows 파일 시스템 watching 한계.

해결:

```bash
# packages 빌드 watch 모드
cd packages/ui && pnpm dev

# Next.js polling 모드 활성화
# apps/admin/next.config.mjs에 watchOptions.pollInterval=1000 추가
```

### 8.8 `pnpm install` 느림 / 실패

증상: 설치가 5분 이상 또는 `EHOSTUNREACH`.

해결:

```bash
# 1) 캐시 클린
pnpm store prune

# 2) 사내 registry 사용 시 .npmrc 확인
cat Tulip/frontend/.npmrc

# 3) 재시도
pnpm install --frozen-lockfile
```

### 8.9 Gradle 빌드 OOM

증상: `OutOfMemoryError: Java heap space`

해결: `Tulip/backend/gradle.properties`:

```
org.gradle.jvmargs=-Xmx4g -XX:MaxMetaspaceSize=1g
org.gradle.parallel=true
org.gradle.caching=true
```

### 8.10 Apple Silicon (arm64) 이미지 호환

증상: `image platform (linux/amd64) does not match the expected target platform`

해결: `docker-compose.yml` 각 service에 `platform: linux/amd64` 추가하거나, 호스트 OS 설정에서 Rosetta 에뮬레이션 활성화.

---

## 9. 종료·정리

| 명령 | 효과 |
|---|---|
| `make down` | 컨테이너 정지 (볼륨 유지, 다음 기동 시 데이터 보존) |
| `make nuke` | 컨테이너 + 볼륨 모두 제거 (DB 데이터 초기화) |
| `make clean` | Gradle 빌드 산출물 제거 |
| `cd Tulip/frontend && make reset` | node_modules + .next + .turbo 모두 초기화 |

---

## 10. 부록 — 자주 쓰는 명령 요약

```bash
# 백엔드 인프라
cd Tulip/backend
make up                          # 컨테이너 기동
make ps                          # 상태
make logs                        # 로그 follow
make down                        # 정지
make nuke                        # 완전 초기화
make psql                        # PostgreSQL psql 접속

# 백엔드 빌드·테스트
./gradlew build                  # 전체 빌드 + 테스트
./gradlew test                   # 테스트만
./gradlew :services:tenant-service:bootRun  # 단일 서비스 부팅
./gradlew :services:tenant-service:integrationTest  # Testcontainers 통합 테스트

# 프론트엔드
cd Tulip/frontend
make install                     # pnpm install
make dev                         # admin + opac 동시 dev
make build                       # 전체 빌드
make lint                        # 전체 lint
make typecheck                   # 타입 체크

# 데이터·진단
docker exec -it tulip-postgres pg_isready
docker exec -it tulip-redis redis-cli ping
docker exec -it tulip-kafka kafka-topics.sh --bootstrap-server kafka:9092 --list
```

---

## 11. 변경 이력

| 버전 | 일자 | 변경 내용 | 작성자 |
|---|---|---|---|
| v0.1 | 2026-05-11 | Phase 1 종료 baseline — 20분 셋업 가이드 + 트러블슈팅 10건 | DevLead Agent |
