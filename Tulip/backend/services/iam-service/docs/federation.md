# IAM Federation 어댑터 설계 (Phase 1-B 스텁)

| 항목 | 내용 |
|---|---|
| 산출물 | Tulip+ IAM Service / Federation 모듈 |
| 작성 단계 | Phase 1-B (스텁만 구현) |
| 작성자 | BackendDev (1-B.9) |
| 입력 | `docs/04_dev_lead/05_security_and_auth.md` §5.3 |
| 후속 | Phase 3 실제 IdP 연동 |

---

## 1. 설계 의도

도서관 고객사(대학·학교·공공)는 학교 SSO·기관 SSO 연동이 사실상 필수다.
Phase 1-B 에서는 **연동 인터페이스(SPI)와 어댑터 스텁**만 마련하여,
Phase 3 에서 운영 정책·인증서·엔드포인트만 채우면 실제 연동이 가능하도록 한다.

- 모든 어댑터 호출은 Phase 1-B 동안 `TLP-AUT-FED-501` 로 종료된다.
- SPI 와 등록/라우팅 골격은 운영 준비되어 있다.
- DB 스키마(`tlp_aut_federation_provider`, `tlp_aut_federation_link`)는 V2 마이그레이션으로 선반영된다.

## 2. 모듈 구조

```
com.tulip.iam.federation
├── api            REST 컨트롤러 & 요청/응답 DTO
├── dto            SPI 입출력 record (FederationLoginContext 등)
├── error          IamErrorCode (TLP-AUT-FED-*)
├── persistence    IdP 등록 리포지토리 (Phase 1-B: InMemory)
├── provider       어댑터 스텁 3종 + 추상 베이스
├── registry       FederationProviderRegistry (type/providerId 라우팅)
└── spi            FederationProvider 인터페이스
```

## 3. SPI 사용법

```java
FederationProvider provider = registry.findByProviderId(providerId)
        .orElseThrow(() -> new NotFoundException(IamErrorCode.FEDERATION_PROVIDER_NOT_FOUND));

FederationAuthorizeRequest req = provider.buildAuthorizeRequest(
        new FederationLoginContext(tenantId, providerId, returnUri, state));
// req.redirectUrl 로 사용자를 리다이렉트
```

콜백:

```java
FederationUserProfile profile = provider.handleCallback(
        new FederationCallbackPayload(providerId, params));
// profile.externalId 로 매핑 조회 또는 JIT 프로비저닝
```

## 4. REST 엔드포인트

| Method | Path | 설명 |
|---|---|---|
| GET  | `/api/v1/auth/federation/providers?tenantId={}` | 테넌트의 활성 IdP 목록 |
| POST | `/api/v1/auth/federation/authorize`             | IdP 인가 요청 생성 (스텁: 501) |
| GET  | `/api/v1/auth/federation/callback/{providerId}` | IdP 콜백 처리 (스텁: 501) |

모든 응답은 `ApiResponse<T>` envelope 으로 표준화된다.

## 5. 에러 코드

| 코드 | HTTP | 의미 |
|---|---|---|
| `TLP-AUT-FED-501` | 501 | Federation 어댑터 미구현 (Phase 1-B 기본 응답) |
| `TLP-AUT-FED-404` | 404 | 등록되지 않은 IdP |
| `TLP-AUT-FED-400` | 400 | 콜백 페이로드 유효성 위반 |

## 6. Phase 3 활성화 체크리스트

- [ ] SAML: OpenSAML 의존성 추가, `SamlFederationProvider` 구현 교체, IdP 메타데이터 등록 절차
- [ ] OIDC: Spring Security OAuth2 Client 통합, ID Token 서명·issuer·audience 검증
- [ ] LDAP: Spring LDAP 의존성 추가, StartTLS 강제, bind/search DN 정책
- [ ] `iam_federation_provider` DB 백엔드 Repository 구현으로 InMemory 교체
- [ ] `iam_federation_link` 기반 JIT 프로비저닝 / 매핑 조회 구현
- [ ] `state` / `nonce` 발급·검증 (Redis 단명 저장)
- [ ] returnUri 화이트리스트 검증 (오픈 리다이렉트 방지)
- [ ] 콜백 성공 시 내부 JWT 발급 → HttpOnly Cookie 또는 클라이언트 redirect
- [ ] 환경변수로 어댑터 활성화: `TULIP_FEDERATION_{SAML|OIDC|LDAP}_ENABLED=true`
- [ ] 운영 콘솔에서 IdP 등록 CRUD UI/API 제공
- [ ] PII 마스킹: `iam_federation_link.attributes_json` 저장 전 정책 적용
- [ ] 감사 로그: 모든 외부 인증 시도(성공/실패) 기록
