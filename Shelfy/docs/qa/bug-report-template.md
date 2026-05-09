# 버그 리포트 표준 양식

- 양식 버전: v1.0.0
- 작성일: 2026-05-09
- 작성자: QA

---

## 버그 리포트 작성 규칙

1. **제목**: `[우선순위][기능영역] 한 줄 요약` 형식으로 작성
   - 예: `[Critical][AUTH] 5회 실패 후에도 계정이 잠금되지 않는 현상`
2. **모든 필드는 빠짐없이 작성**한다. 미확인 항목은 `확인 필요` 기재
3. **재현 단계**는 1:1 대응 가능한 수준으로 구체적으로 작성
4. **스크린샷 / 로그**는 반드시 첨부 (API 테스트는 응답 전체 캡처)
5. **우선순위 기준**:
   - Critical: 서비스 불가, 보안 취약, 데이터 손실
   - High: 핵심 기능 오동작, 비즈니스 정책 위반
   - Medium: 부분 기능 오동작, UX 저해
   - Low: 미관 문제, 오탈자, 개선 요청

---

## 버그 리포트 양식

```
---
버그 ID: BUG-[기능코드]-[순번]
  예: BUG-AUTH-001, BUG-ORDER-003

제목: [우선순위][기능영역] 한 줄 요약

---
## 기본 정보

| 항목 | 내용 |
|---|---|
| 버그 ID | BUG-[코드]-[번호] |
| 발견 일시 | YYYY-MM-DD HH:mm |
| 발견자 | QA 담당자명 |
| 우선순위 | Critical / High / Medium / Low |
| 심각도 | Blocker / Critical / Major / Minor / Trivial |
| 상태 | Open / In Progress / Fixed / Verified / Closed / Won't Fix |
| 담당 개발자 | (버그 배분 후 기입) |
| 관련 기능 ID | 예: AUTH-003, ORDER-001 |
| 관련 TC-ID | 예: TC-AUTH-033 |
| 발견 환경 | 개발(dev) / 스테이징(staging) / 운영(prod) |
| 브라우저/OS | 예: Chrome 125 / Windows 11 |
| API 버전 | v1.0.0 |

---
## 재현 환경

- **테스트 환경**: 개발 서버 (https://api-dev.shelfy.io/api/v1)
- **계정 정보**: (테스트 계정 ID 또는 이메일, 비밀번호는 별도 공유)
- **사전 데이터**: (재현에 필요한 DB 상태, 예: "userId: 1001, 5회 실패 기록 있는 계정")

---
## 재현 단계 (Steps to Reproduce)

1. [구체적인 첫 번째 단계]
2. [구체적인 두 번째 단계]
3. [계속...]

**API 테스트인 경우:**
- Endpoint: `POST /auth/login`
- Request Header:
  ```
  Content-Type: application/json
  ```
- Request Body:
  ```json
  {
    "email": "test@shelfy.io",
    "password": "WrongPass1!"
  }
  ```

---
## 기대 결과 (Expected Result)

[정상 동작 시 어떤 결과가 반환되어야 하는지 명확히 기술]

예:
- HTTP 403 반환
- 응답 바디: `{ "error": { "code": "AUTH-E021", "message": "로그인 5회 실패로 계정이 잠금되었습니다." } }`

---
## 실제 결과 (Actual Result)

[실제로 발생한 결과를 정확히 기술]

예:
- HTTP 200 반환 (로그인 성공)
- 응답 바디: `{ "data": { "accessToken": "..." } }`

---
## 영향도 분석

- **영향 기능**: [버그로 인해 영향받는 다른 기능 목록]
- **영향 사용자**: [셀러 전체 / 바이어 전체 / 특정 조건 사용자]
- **데이터 영향**: [데이터 정합성 문제 발생 여부, DBA 협의 필요 여부]
- **보안 영향**: [인증/인가 우회, 데이터 노출 등 보안 위험 여부]

---
## 첨부 자료

- [ ] 스크린샷 / 화면 녹화
- [ ] API 응답 전체 캡처 (요청/응답 헤더 포함)
- [ ] 서버 에러 로그 (timestamp 포함)
- [ ] 관련 DB 쿼리 결과 (DBA 협의 후 첨부)
- [ ] 재현 동영상

---
## 수정 요청 사항

[개발자에게 전달할 구체적인 수정 방향 또는 참고 정책 문서]

예:
- feature-spec.md AUTH-003 항목 참조: "5회 연속 로그인 실패 시 30분 계정 잠금"
- DB의 `user_login_attempts` 테이블의 잠금 상태 업데이트 로직 확인 필요

---
## 변경 이력

| 날짜 | 변경자 | 내용 |
|---|---|---|
| YYYY-MM-DD | QA | 버그 등록 |
| YYYY-MM-DD | 개발자 | 수정 완료 (커밋: abc1234) |
| YYYY-MM-DD | QA | 검증 완료 / 재오픈 |
```

---

## 작성 예시 (샘플)

---
버그 ID: BUG-AUTH-001

제목: [Critical][AUTH] 5회 실패 후에도 계정 잠금이 적용되지 않는 현상

---
### 기본 정보

| 항목 | 내용 |
|---|---|
| 버그 ID | BUG-AUTH-001 |
| 발견 일시 | 2026-05-09 14:30 |
| 발견자 | QA |
| 우선순위 | Critical |
| 심각도 | Blocker |
| 상태 | Open |
| 담당 개발자 | BackendSenior |
| 관련 기능 ID | AUTH-003 |
| 관련 TC-ID | TC-AUTH-033 |
| 발견 환경 | 개발(dev) |
| 브라우저/OS | Postman / Windows 11 |
| API 버전 | v1.0.0 |

### 재현 환경

- 테스트 환경: https://api-dev.shelfy.io/api/v1
- 계정: test_lock_001@shelfy-test.io (별도 공유)

### 재현 단계

1. POST /auth/login (email: test_lock@shelfy.io, password: "WrongPass1!") 5회 반복
2. POST /auth/login (email: test_lock@shelfy.io, password: "OldCorrectPass1!") 호출

### 기대 결과

HTTP 403, `{ "error": { "code": "AUTH-E021" } }`

### 실제 결과

HTTP 200 로그인 성공, accessToken 발급됨

### 영향도 분석

- 영향 기능: 인증 보안 전체
- 영향 사용자: 전체 사용자
- 보안 영향: 브루트포스 공격 방어 미작동 - 즉각 조치 필요

---

## 버그 우선순위별 SLA (해결 목표 기간)

| 우선순위 | 목표 해결 기간 |
|---|---|
| Critical | 당일 수정 완료 (운영 핫픽스 포함) |
| High | 3 영업일 이내 |
| Medium | 다음 스프린트 내 |
| Low | 백로그 등록, 여유 시 처리 |
