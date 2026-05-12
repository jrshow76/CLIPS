# RLS 누설 회귀 테스트

`Tulip/backend/db/test/rls/*.sql` 시나리오를 모아 실행하는 wrapper.

## 사전 준비

- PostgreSQL client(`psql`) 설치
- Flyway 마이그레이션이 적용된 데이터베이스 1개
- 시드 데이터는 각 SQL 시나리오가 자체 INSERT (테넌트 2개, 회원 1만건)

## 실행

```bash
# 로컬 docker compose
cd Tulip/backend && make up
cd tests/rls && ./run-rls-tests.sh

# 임의 DB 지정
PGURL="postgres://user:pass@host:5432/db" ./run-rls-tests.sh
```

종료 코드 0 = 모든 시나리오 통과. 1 이상 = 누설/오류 발생.

## 시나리오 목록

| 파일 | 설명 |
|---|---|
| `01_member_isolation_test.sql` | 2개 테넌트 회원 1만건 격리 + 명시적 cross-tenant 조회 차단 |

신규 도메인 추가 시 `Tulip/backend/db/test/rls/`에 `NN_<domain>_isolation_test.sql` 형태로 파일을 추가하면 자동으로 실행된다.

## CI 통합

`Tulip/backend/.github/workflows/backend-ci.yml`의 `rls` 잡이 본 스크립트를 호출하도록 구성.
