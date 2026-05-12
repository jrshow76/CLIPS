# Changelog

본 프로젝트의 모든 주목할 만한 변경 사항을 기록한다. 형식은 [Keep a Changelog](https://keepachangelog.com/ko/1.1.0/)를 따르며, 버전 체계는 [Semantic Versioning](https://semver.org/lang/ko/)을 따른다.

## [Unreleased]

## [0.1.0-phase1] - 2026-05-12

### Added
- **인프라**: Docker Compose 8 서비스(PostgreSQL15·Redis7·Kafka KRaft·Keycloak24·MinIO·MailHog·Prometheus·Grafana)
- **백엔드 모노레포**: Gradle 멀티프로젝트(Java 21, Spring Boot 3.3.5, Spring Cloud 2023.0.3) + 공통 라이브러리 6종(common-core/web/security/tenant/data/test)
- **프론트엔드 모노레포**: pnpm + Turborepo(Node 22, Next.js 15, TypeScript 5, Tailwind 4) + 공통 패키지 7종(design-tokens·ui·api-client·auth·config·tsconfig·eslint-config) + 앱 2종(admin·opac)
- **인증**: Keycloak realm `tulip` + BFF PKCE 인증(iam-service `/api/v1/auth/*` 8엔드포인트, JWS RS256, JTI Redis 블랙리스트, Refresh 회전)
- **API Gateway**: Spring Cloud Gateway(JWT 필터·테넌트 헤더 전파·Rate Limit·CORS) 라우팅 7종
- **마스터 서비스**: tenant(23 EP) · member(13 EP) · code-policy(12 EP) · iam(8 EP) · gateway(라우팅) — 총 56 엔드포인트
- **데이터**: Flyway 마이그레이션 9개, RLS 정책 72개, 글로벌 시드 코드 5그룹/20값
- **이벤트**: Outbox 패턴(SKIP LOCKED 폴링 5초·재시도 5회) → Kafka 토픽 20종(`tulip.{tenant,member,code,policy}.*`)
- **프론트엔드 UI**: 컴포넌트 30+개, admin 16라우트(대시보드 KPI·차트·활동피드·알림 풀 통합 + 회원/도서관/코드 관리), opac 8라우트
- **품질**: Playwright E2E 5종(auth·members·libraries·rls·opac), k6 부하 3종(auth 100 RPS·members 50 RPS·dashboard 30 RPS), RLS 누설 회귀 wrapper, 1만건 회귀 테스트
- **문서**: 아키텍처/서비스 분해/API 표준/에러 코드/보안 인증/코딩 표준/스프린트 분해/인프라 결정/종료 게이트/Phase 2 진입 준비/로컬 런북/릴리스 노트

### Security
- 멀티테넌트 RLS 강제(FORCE RLS, 4명령 정책), JWT 검증(JWKS), JTI 블랙리스트, ABAC TenantAccessVoter, Refresh 쿠키 HttpOnly+SameSite, CORS 화이트리스트, Rate Limit(익명 60/min·인증 300/min)

### Known Issues
- 대시보드 통계 전용 백엔드 엔드포인트 미구현 — mock 모드 또는 인접 API batch로 대체
- MFA/SSO Federation 인터페이스만 제공(스텁 501)
- 대규모 검색·서지 도메인은 Phase 2에서 다룸

[Unreleased]: https://example.com/tulip-plus/compare/v0.1.0-phase1...HEAD
[0.1.0-phase1]: https://example.com/tulip-plus/releases/tag/v0.1.0-phase1
