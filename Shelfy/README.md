# Shelfy

> 당신의 선반을 세상에 공개하세요

자신의 물건을 선반(Shelf)에 등록하고, 다른 사용자가 둘러보며 구매하거나 구독할 수 있는 웹 애플리케이션입니다.

---

## 기술 스택

| 구분 | 기술 |
|---|---|
| Backend | Java 17, Spring Boot 3.x, MyBatis, JPA |
| Frontend | Next.js 14 (App Router), TypeScript, TanStack Query v5 |
| Database | PostgreSQL 15 |
| Infra | Docker, Docker Compose, GitHub Actions |

---

## 로컬 개발 환경 실행

### 사전 요구사항

- Docker Desktop 4.x 이상
- Java 17 (IntelliJ 또는 직접 실행 시)
- Node.js 20 (직접 실행 시)

### 환경변수 설정

```bash
cp .env.example .env
# .env 파일을 열어 필요한 값 설정
```

### Docker Compose 실행 (권장)

```bash
# 전체 서비스 실행
docker-compose up -d

# 로그 확인
docker-compose logs -f

# 서비스 종료
docker-compose down
```

### 개별 실행

**Backend**

```bash
cd backend
./gradlew bootRun
# http://localhost:8080
```

**Frontend**

```bash
cd frontend
npm install
npm run dev
# http://localhost:3000
```

---

## 서비스 접속 URL

| 서비스 | URL |
|---|---|
| Frontend | http://localhost:3000 |
| Backend API | http://localhost:8080/api/v1 |
| MinIO Console | http://localhost:9001 |
| PostgreSQL | localhost:5432 |

---

## 프로젝트 구조

```
Shelfy/
├── backend/              # Spring Boot 백엔드
│   ├── src/
│   │   └── main/
│   │       ├── java/com/shelfy/
│   │       └── resources/
│   ├── build.gradle
│   └── Dockerfile
├── frontend/             # Next.js 프론트엔드
│   ├── src/
│   │   └── app/
│   ├── package.json
│   └── Dockerfile
├── docs/                 # 프로젝트 문서
│   ├── pm/
│   ├── planner/
│   └── devlead/
├── docker-compose.yml
├── .gitignore
└── README.md
```

---

## 개발 가이드

- API 설계 규약: `docs/devlead/dev-standards.md`
- 기술 아키텍처: `docs/devlead/architecture.md`
- API 요구사항: `docs/planner/api-requirements.md`
- 데이터 모델: `docs/planner/data-model.md`
- 기능 명세서: `docs/planner/feature-spec.md`
- 프로젝트 계획: `docs/pm/project-plan.md`

---

## 브랜치 전략

```
main      - 운영 배포
develop   - 개발 통합
feature/* - 기능 개발
fix/*     - 버그 수정
hotfix/*  - 긴급 패치
```

PR은 반드시 DevLead 리뷰 후 develop으로 머지합니다.

---

## 마일스톤

| 마일스톤 | 기간 | 목표 |
|---|---|---|
| M0. 착수 및 설계 | 2026-05-11 ~ 05-29 | 아키텍처, DB 설계, 화면 설계 완료 |
| M1. 핵심 기능 개발 | 2026-06-01 ~ 07-03 | 인증, 상품 CRUD, 구독 기능 |
| M2. 부가 기능 개발 | 2026-07-06 ~ 07-31 | 구매, 검색, 알림, 관리자 |
| M3. 통합 테스트 | 2026-08-03 ~ 08-21 | QA, 버그 수정, 성능 점검 |
| M4. 배포 및 출시 | 2026-08-24 ~ 08-29 | 운영 배포, PM 승인, 서비스 오픈 |
