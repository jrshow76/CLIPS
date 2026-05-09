# 버그 리포트 양식

- **프로젝트명**: 발자국 (Foot-Print)
- **문서 버전**: v1.0.0
- **작성일**: 2026-05-09
- **작성자**: QA

---

## 심각도 (Severity) 기준

| 심각도 | 설명 | 예시 |
|-------|------|------|
| Critical | 서비스 전체 또는 핵심 기능이 동작 불가 | 로그인 불가, 데이터 손실, 보안 취약점 |
| Major | 주요 기능이 비정상 동작하나 우회 방법 존재 | 장소 등록 실패, 잘못된 필터 결과 |
| Minor | 기능은 동작하나 UX/UI 문제 또는 비정상 표시 | 오류 메시지 내용 부정확, 레이아웃 깨짐 |
| Trivial | 서비스 영향 없는 경미한 문제 | 오탈자, 색상 미세 차이, 주석 오류 |

## 우선순위 (Priority) 기준

| 우선순위 | 설명 |
|---------|------|
| Urgent | 즉시 수정 필요 (배포 블로커) |
| High | 다음 스프린트 이전 수정 필요 |
| Medium | 예정된 일정 내 수정 |
| Low | 여유 일정에 수정 |

---

## 버그 리포트 양식

```
버그 ID       : BUG-[YYYYMMDD]-[순번]    (예: BUG-20260509-001)
제목          : [모듈] 한 문장으로 현상 요약
심각도        : Critical / Major / Minor / Trivial
우선순위      : Urgent / High / Medium / Low
상태          : Open / In Progress / Resolved / Closed / Won't Fix
담당자(개발)  : 
보고자(QA)   : 
발견일        : YYYY-MM-DD
수정 목표일   : YYYY-MM-DD
수정 완료일   : YYYY-MM-DD
```

---

## 재현 환경

```
OS          : 
브라우저    : Chrome 버전 / Firefox 버전 / Safari 버전
해상도      : PC (1920×1080) / 태블릿 (1024×768) / 모바일 (390×844)
환경        : 로컬 / 스테이징 / 운영
Backend     : localhost:8080 / staging URL
Frontend    : localhost:3000 / staging URL
DB          : PostgreSQL 16
관련 TC-ID  : TC-[모듈]-[번호]
```

---

## 재현 단계

```
전제조건:
- (예: 로그인 상태, 장소 1개 이상 등록됨)

단계:
1. 
2. 
3. 
```

---

## 기대 결과

```
(SRS, API 명세, 화면 정의서 기준으로 정상 동작이어야 할 내용 기술)
```

---

## 실제 결과

```
(현재 비정상 동작 내용 정확히 기술)
- HTTP 상태 코드:
- 응답 body:
- 화면 현상:
```

---

## 첨부파일

```
- 스크린샷: 
- 동영상: 
- 네트워크 로그 (HAR 파일): 
- 브라우저 콘솔 로그: 
- 서버 에러 로그: 
```

---

## 비고

```
(추가 참고사항, 관련 코드 위치, 임시 우회 방법 등)
```

---

## 작성 예시

```
버그 ID       : BUG-20260509-001
제목          : [AUTH] 만료된 Refresh Token으로 갱신 요청 시 500 에러 반환
심각도        : Critical
우선순위      : Urgent
상태          : Open
담당자(개발)  : BackendSenior
보고자(QA)   : QA담당자
발견일        : 2026-05-09
수정 목표일   : 2026-05-10
수정 완료일   :

재현 환경:
- OS: Windows 11
- 브라우저: Chrome 124
- 환경: 로컬 (localhost:8080)
- 관련 TC-ID: TC-AUTH-011

전제조건:
- 만료된 Refresh Token 쿠키 보유 (직접 쿠키 만료 시간 조작)

단계:
1. 만료된 Access Token으로 GET /api/v1/places 호출
2. 401 TOKEN_EXPIRED 응답 수신
3. 자동으로 POST /api/v1/auth/refresh 호출 (만료된 Refresh Token 포함)

기대 결과:
- HTTP 401 응답, code: REFRESH_TOKEN_EXPIRED
- 로그인 페이지로 강제 이동

실제 결과:
- HTTP 500 응답, code: SERVER_ERROR
- 로그인 페이지 이동 없음, 사용자 화면 블랭크 처리

첨부파일:
- 스크린샷: bug_20260509_001_network.png
- 서버 에러 로그: NullPointerException at RefreshTokenService.java:42
```

---

## 버그 상태 전이도

```
Open
  ↓ (개발자 할당)
In Progress
  ↓ (수정 완료)
Resolved
  ↓ (QA 검증 통과)
Closed
  또는
  ↓ (QA 검증 실패 — 재오픈)
Open

Won't Fix: 의도적 기획 결정 또는 수정 범위 외 판단 시
```

---

*본 양식은 Jira 이슈 생성 시 설명(Description) 필드에 마크다운 형식으로 붙여넣어 사용한다.*
