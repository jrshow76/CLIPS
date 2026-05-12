# Tulip+ 부하 테스트 (k6)

Phase 1-D 단계 부하 회귀 스크립트 모음.

## 사전 준비

1. k6 설치: <https://k6.io/docs/getting-started/installation/>
2. 로컬 인프라 기동: `cd Tulip/backend && make up`
3. iam-service, api-gateway, member-service 등 대상 서비스 기동
4. Keycloak realm `tulip`에 부하 테스트용 사용자 존재 확인

## 환경변수

| 변수 | 기본값 |
|---|---|
| `BASE_URL` | `http://localhost:8080` (API Gateway) |
| `IAM_BASE_URL` | `BASE_URL` |
| `TEST_USERNAME` | `librarian@demo-tenant-1` |
| `TEST_PASSWORD` | `changeit` |
| `TEST_TENANT_ID` | `demo-tenant-1` |
| `K6_KEYCLOAK_REALM` | `tulip` |
| `K6_KEYCLOAK_CLIENT` | `tulip-admin` |

## 스크립트

| 스크립트 | 목표 | 임계치 |
|---|---|---|
| `auth.js` | 로그인 100 RPS, 1분 | `p99 < 200ms`, 실패율 < 1% |
| `members.js` | 회원 검색 50 RPS, 1분 | `p99 < 300ms`, 실패율 < 1% |
| `dashboard.js` | 대시보드 초기 로드 30 RPS, 1분 | `p99 < 400ms`, 실패율 < 1% |

## 실행

```bash
cd Tulip/backend/tests/load
k6 run auth.js
k6 run members.js
k6 run dashboard.js
```

실행 후 `summary.html`이 생성된다.

## 결과 해석

- `http_req_duration` p95/p99 임계치 위반 시 ❌
- `checks` 통과율 99% 미만이면 ❌ (응답 본문 형식 결함)
- 실패 시: 로그·DB 트레이스·서비스 메트릭(Prometheus/Grafana) 점검

## 한계

- Direct Grant 흐름은 운영 비허용. 부하 테스트 전용.
- 대시보드 통계 전용 엔드포인트는 Phase 2에서 도입 예정. 현재는 인접 API 4종 batch 호출로 초기 로드 부하를 근사한다.
