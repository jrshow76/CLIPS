# Shelfy - 테스트 케이스 명세서

- 작성일: 2026-05-09
- 작성자: QA
- 버전: v1.0.0
- 기반 문서: feature-spec.md v1.0.0, api-requirements.md v1.0.0

---

## 목차

1. [인증 (AUTH)](#1-인증-auth)
2. [파일 업로드 (FILE)](#2-파일-업로드-file)
3. [상품 관리 (ITEM)](#3-상품-관리-item)
4. [탐색 및 검색 (BROWSE)](#4-탐색-및-검색-browse)
5. [구매 (ORDER)](#5-구매-order)
6. [구독 (SUB)](#6-구독-sub)
7. [프로필 (PROFILE)](#7-프로필-profile)

---

## 테스트 케이스 범례

| 구분 | 설명 |
|---|---|
| TC-ID | 테스트 케이스 식별자 |
| 분류 | Happy / Exception / Boundary |
| 우선순위 | Critical / High / Medium / Low |

---

## 1. 인증 (AUTH)

### 1-1. 회원가입 (AUTH-001)

---

**TC-AUTH-001** | 정상 회원가입
- 분류: Happy
- 우선순위: Critical
- 사전 조건: 서버 정상 동작, 미사용 이메일/닉네임 준비
- 테스트 단계:
  1. POST /auth/signup 호출
  2. email: "test_001@shelfy.io", password: "Test1234!", passwordConfirm: "Test1234!", nickname: "tester001", agreeTerms: true, agreePrivacy: true, agreeMarketing: false
- 예상 결과: HTTP 201, { success: true, data: { userId, email, nickname } }, 인증 이메일 발송

---

**TC-AUTH-002** | 이메일 중복 회원가입 차단
- 분류: Exception
- 우선순위: Critical
- 사전 조건: "dup@shelfy.io" 이메일이 이미 가입된 상태
- 테스트 단계:
  1. POST /auth/signup 호출 (email: "dup@shelfy.io", 나머지 유효한 값)
- 예상 결과: HTTP 409, error.code: "AUTH-E001", "이미 사용 중인 이메일입니다."

---

**TC-AUTH-003** | 닉네임 중복 회원가입 차단
- 분류: Exception
- 우선순위: Critical
- 사전 조건: "duplicateNick" 닉네임이 이미 사용 중인 상태
- 테스트 단계:
  1. POST /auth/signup 호출 (nickname: "duplicateNick", 나머지 유효한 값)
- 예상 결과: HTTP 409, error.code: "AUTH-E002", "이미 사용 중인 닉네임입니다."

---

**TC-AUTH-004** | 비밀번호 불일치
- 분류: Exception
- 우선순위: High
- 사전 조건: 없음
- 테스트 단계:
  1. POST /auth/signup 호출 (password: "Test1234!", passwordConfirm: "Test5678!")
- 예상 결과: HTTP 400, error.code: "AUTH-E003"

---

**TC-AUTH-005** | 이메일 형식 오류
- 분류: Exception
- 우선순위: High
- 사전 조건: 없음
- 테스트 단계:
  1. POST /auth/signup 호출 (email: "invalid-email")
- 예상 결과: HTTP 400, error.code: "AUTH-E004"

---

**TC-AUTH-006** | 비밀번호 규칙 위반 - 8자 미만
- 분류: Boundary
- 우선순위: High
- 사전 조건: 없음
- 테스트 단계:
  1. POST /auth/signup 호출 (password: "Te1!") → 4자
- 예상 결과: HTTP 400, error.code: "AUTH-E005"

---

**TC-AUTH-007** | 비밀번호 규칙 위반 - 21자 초과
- 분류: Boundary
- 우선순위: High
- 사전 조건: 없음
- 테스트 단계:
  1. POST /auth/signup 호출 (password: "TestPassword123456!XX") → 21자
- 예상 결과: HTTP 400, error.code: "AUTH-E005"

---

**TC-AUTH-008** | 비밀번호 규칙 위반 - 특수문자 미포함
- 분류: Exception
- 우선순위: High
- 사전 조건: 없음
- 테스트 단계:
  1. POST /auth/signup 호출 (password: "TestPass1234") → 특수문자 없음
- 예상 결과: HTTP 400, error.code: "AUTH-E005"

---

**TC-AUTH-009** | 필수 약관 미동의
- 분류: Exception
- 우선순위: High
- 사전 조건: 없음
- 테스트 단계:
  1. POST /auth/signup 호출 (agreeTerms: false)
- 예상 결과: HTTP 400, error.code: "AUTH-E006"

---

**TC-AUTH-010** | 닉네임 최소 길이 경계값 - 2자 허용
- 분류: Boundary
- 우선순위: Medium
- 테스트 단계:
  1. POST /auth/signup 호출 (nickname: "ab") → 2자
- 예상 결과: HTTP 201

---

**TC-AUTH-011** | 닉네임 최소 길이 경계값 - 1자 거부
- 분류: Boundary
- 우선순위: Medium
- 테스트 단계:
  1. POST /auth/signup 호출 (nickname: "a") → 1자
- 예상 결과: HTTP 400

---

**TC-AUTH-012** | 닉네임 최대 길이 경계값 - 20자 허용
- 분류: Boundary
- 우선순위: Medium
- 테스트 단계:
  1. POST /auth/signup 호출 (nickname: "abcdefghijklmnopqrst") → 20자
- 예상 결과: HTTP 201

---

**TC-AUTH-013** | 닉네임 최대 길이 경계값 - 21자 거부
- 분류: Boundary
- 우선순위: Medium
- 테스트 단계:
  1. POST /auth/signup 호출 (nickname: "abcdefghijklmnopqrstu") → 21자
- 예상 결과: HTTP 400

---

**TC-AUTH-014** | 닉네임 허용 외 특수문자 포함 거부
- 분류: Exception
- 우선순위: Medium
- 테스트 단계:
  1. POST /auth/signup 호출 (nickname: "test-user!") → 하이픈, 느낌표 포함
- 예상 결과: HTTP 400

---

### 1-2. 이메일 인증 (AUTH-002)

---

**TC-AUTH-020** | 정상 이메일 인증
- 분류: Happy
- 우선순위: Critical
- 사전 조건: 회원가입 완료 후 인증 토큰 수신
- 테스트 단계:
  1. GET /auth/verify-email?token={유효한_토큰}
- 예상 결과: HTTP 200, "이메일 인증이 완료되었습니다."

---

**TC-AUTH-021** | 만료된 인증 토큰
- 분류: Exception
- 우선순위: High
- 사전 조건: 24시간이 경과한 인증 토큰
- 테스트 단계:
  1. GET /auth/verify-email?token={만료_토큰}
- 예상 결과: HTTP 400, error.code: "AUTH-E010"

---

**TC-AUTH-022** | 유효하지 않은 인증 토큰
- 분류: Exception
- 우선순위: High
- 사전 조건: 없음
- 테스트 단계:
  1. GET /auth/verify-email?token=invalid-random-string
- 예상 결과: HTTP 400, error.code: "AUTH-E011"

---

**TC-AUTH-023** | 이미 인증 완료된 계정 재인증 시도
- 분류: Exception
- 우선순위: Medium
- 사전 조건: 이미 이메일 인증이 완료된 계정의 토큰
- 테스트 단계:
  1. GET /auth/verify-email?token={이미_사용된_토큰}
- 예상 결과: HTTP 409, error.code: "AUTH-E012"

---

**TC-AUTH-024** | 미인증 상태에서 셀러 기능 접근 차단
- 분류: Exception
- 우선순위: Critical
- 사전 조건: 회원가입 완료, 이메일 미인증 상태로 로그인
- 테스트 단계:
  1. POST /auth/login 성공 → accessToken 획득
  2. POST /items 호출 (이메일 미인증 계정의 토큰)
- 예상 결과: HTTP 403, error.code: "ITEM-E001"

---

### 1-3. 로그인 (AUTH-003)

---

**TC-AUTH-030** | 정상 로그인
- 분류: Happy
- 우선순위: Critical
- 사전 조건: 가입 완료된 계정 (이메일 인증 여부 무관)
- 테스트 단계:
  1. POST /auth/login (email: "test@shelfy.io", password: "Test1234!")
- 예상 결과: HTTP 200, { accessToken, tokenType: "Bearer", expiresIn: 3600 }, Set-Cookie: refreshToken (HttpOnly)

---

**TC-AUTH-031** | 존재하지 않는 이메일로 로그인
- 분류: Exception
- 우선순위: High
- 사전 조건: 없음
- 테스트 단계:
  1. POST /auth/login (email: "notexist@shelfy.io", password: "Test1234!")
- 예상 결과: HTTP 401, error.code: "AUTH-E020"

---

**TC-AUTH-032** | 비밀번호 불일치 로그인
- 분류: Exception
- 우선순위: High
- 사전 조건: 가입된 계정
- 테스트 단계:
  1. POST /auth/login (올바른 email, 틀린 password: "Wrong1234!")
- 예상 결과: HTTP 401, error.code: "AUTH-E020"

---

**TC-AUTH-033** | 5회 연속 로그인 실패 후 계정 잠금
- 분류: Exception
- 우선순위: Critical
- 사전 조건: 가입된 계정
- 테스트 단계:
  1. POST /auth/login (틀린 비밀번호) 1회 → HTTP 401
  2. 위 과정 5회 반복
  3. 6번째 POST /auth/login (올바른 비밀번호 포함)
- 예상 결과: 5회째 실패 시 또는 6회째 시도 시 HTTP 403, error.code: "AUTH-E021", "로그인 5회 실패로 계정이 잠금되었습니다."

---

**TC-AUTH-034** | 계정 잠금 후 30분 이내 재로그인 차단
- 분류: Exception
- 우선순위: Critical
- 사전 조건: 계정 잠금 상태
- 테스트 단계:
  1. 잠금 직후 POST /auth/login (올바른 비밀번호)
- 예상 결과: HTTP 403, error.code: "AUTH-E021"

---

**TC-AUTH-035** | 탈퇴된 계정 로그인 시도
- 분류: Exception
- 우선순위: High
- 사전 조건: 탈퇴 처리된 계정
- 테스트 단계:
  1. POST /auth/login (탈퇴된 계정 이메일/비밀번호)
- 예상 결과: HTTP 403, error.code: "AUTH-E022"

---

**TC-AUTH-036** | refreshToken이 HttpOnly 쿠키로 설정되는지 확인
- 분류: Happy
- 우선순위: High
- 사전 조건: 없음
- 테스트 단계:
  1. POST /auth/login 성공 응답 헤더 확인
- 예상 결과: Set-Cookie 헤더에 HttpOnly, Secure, SameSite=Strict 속성 포함, 응답 바디에 refreshToken 미포함

---

### 1-4. 로그아웃 (AUTH-004)

---

**TC-AUTH-040** | 정상 로그아웃
- 분류: Happy
- 우선순위: High
- 사전 조건: 로그인 상태
- 테스트 단계:
  1. POST /auth/logout (Authorization: Bearer {accessToken})
- 예상 결과: HTTP 204, refreshToken 쿠키 만료(Max-Age=0) 처리

---

**TC-AUTH-041** | 로그아웃 후 기존 refreshToken으로 갱신 시도
- 분류: Exception
- 우선순위: High
- 사전 조건: 로그아웃 완료된 상태
- 테스트 단계:
  1. POST /auth/token/refresh (로그아웃 전 refreshToken 쿠키 사용)
- 예상 결과: HTTP 401, error.code: "AUTH-E031"

---

**TC-AUTH-042** | 인증 토큰 없이 로그아웃 시도
- 분류: Exception
- 우선순위: Medium
- 테스트 단계:
  1. POST /auth/logout (Authorization 헤더 없음)
- 예상 결과: HTTP 401

---

### 1-5. 토큰 갱신 (AUTH-005)

---

**TC-AUTH-050** | 유효한 refreshToken으로 accessToken 갱신
- 분류: Happy
- 우선순위: Critical
- 사전 조건: 로그인 후 refreshToken 쿠키 보유
- 테스트 단계:
  1. POST /auth/token/refresh (refreshToken 쿠키 포함)
- 예상 결과: HTTP 200, 새로운 accessToken 반환

---

**TC-AUTH-051** | 만료된 refreshToken으로 갱신 시도
- 분류: Exception
- 우선순위: High
- 사전 조건: 14일이 경과한 refreshToken
- 테스트 단계:
  1. POST /auth/token/refresh (만료된 refreshToken 쿠키)
- 예상 결과: HTTP 401, error.code: "AUTH-E030"

---

**TC-AUTH-052** | 위변조된 refreshToken으로 갱신 시도
- 분류: Exception
- 우선순위: High
- 테스트 단계:
  1. POST /auth/token/refresh (조작된 토큰 값 쿠키)
- 예상 결과: HTTP 401, error.code: "AUTH-E031"

---

### 1-6. 비밀번호 재설정 (AUTH-006)

---

**TC-AUTH-060** | 비밀번호 재설정 요청 - 존재하는 이메일
- 분류: Happy
- 우선순위: High
- 사전 조건: 가입된 이메일
- 테스트 단계:
  1. POST /auth/forgot-password (email: "test@shelfy.io")
- 예상 결과: HTTP 200, "비밀번호 재설정 이메일을 발송했습니다."

---

**TC-AUTH-061** | 비밀번호 재설정 요청 - 존재하지 않는 이메일
- 분류: Exception
- 우선순위: High
- 사전 조건: 없음
- 테스트 단계:
  1. POST /auth/forgot-password (email: "notexist@shelfy.io")
- 예상 결과: HTTP 200 (보안상 동일 응답), "비밀번호 재설정 이메일을 발송했습니다."
- 검증 포인트: 이메일 존재 여부 정보 노출 금지

---

**TC-AUTH-062** | 정상 비밀번호 재설정
- 분류: Happy
- 우선순위: High
- 사전 조건: 재설정 토큰 보유 (1시간 이내)
- 테스트 단계:
  1. POST /auth/reset-password (token: 유효한 토큰, newPassword: "NewPass1!", newPasswordConfirm: "NewPass1!")
  2. POST /auth/login (새 비밀번호로 로그인 시도)
- 예상 결과: 재설정 HTTP 200, 이후 로그인 HTTP 200 성공

---

**TC-AUTH-063** | 만료된 재설정 토큰 사용
- 분류: Exception
- 우선순위: High
- 사전 조건: 1시간 이상 경과한 재설정 토큰
- 테스트 단계:
  1. POST /auth/reset-password (만료 토큰)
- 예상 결과: HTTP 400

---

**TC-AUTH-064** | 재설정 토큰 1회 사용 후 재사용 차단
- 분류: Exception
- 우선순위: High
- 사전 조건: 이미 사용된 재설정 토큰
- 테스트 단계:
  1. POST /auth/reset-password (1회 사용된 토큰으로 재시도)
- 예상 결과: HTTP 400

---

**TC-AUTH-065** | 기존과 동일한 비밀번호로 재설정 차단
- 분류: Exception
- 우선순위: Medium
- 사전 조건: 유효한 재설정 토큰
- 테스트 단계:
  1. POST /auth/reset-password (newPassword: 현재 비밀번호와 동일)
- 예상 결과: HTTP 400 또는 422, 동일 비밀번호 재설정 불가 오류

---

### 1-7. 회원 탈퇴 (AUTH-007)

---

**TC-AUTH-070** | 정상 회원 탈퇴
- 분류: Happy
- 우선순위: High
- 사전 조건: 로그인 상태, 활성 구독 없음, 미정산 수익 없음
- 테스트 단계:
  1. DELETE /auth/me (password: 현재 비밀번호)
- 예상 결과: HTTP 204, 이후 동일 계정 로그인 시 AUTH-E022 반환

---

**TC-AUTH-071** | 활성 구독 있는 상태에서 탈퇴 시도 차단
- 분류: Exception
- 우선순위: High
- 사전 조건: 활성 구독 1건 이상 보유
- 테스트 단계:
  1. DELETE /auth/me (올바른 비밀번호)
- 예상 결과: HTTP 422, 구독 해지 후 탈퇴 안내 메시지

---

**TC-AUTH-072** | 탈퇴 시 비밀번호 불일치
- 분류: Exception
- 우선순위: High
- 사전 조건: 로그인 상태
- 테스트 단계:
  1. DELETE /auth/me (password: "WrongPass1!")
- 예상 결과: HTTP 400 또는 401

---

**TC-AUTH-073** | 탈퇴 후 30일 이내 동일 이메일 재가입 차단
- 분류: Exception
- 우선순위: Medium
- 사전 조건: 탈퇴 처리된 계정 (30일 이내)
- 테스트 단계:
  1. POST /auth/signup (탈퇴한 이메일로 재가입 시도)
- 예상 결과: HTTP 409 또는 400, 재가입 불가 안내

---

## 2. 파일 업로드 (FILE)

---

**TC-FILE-001** | 정상 JPG 이미지 업로드
- 분류: Happy
- 우선순위: High
- 사전 조건: 로그인 상태
- 테스트 단계:
  1. POST /files/upload (file: 유효한 JPG, type: "ITEM_IMAGE")
- 예상 결과: HTTP 201, { imageId, url, fileName, fileSize, uploadedAt }

---

**TC-FILE-002** | 정상 PNG 이미지 업로드
- 분류: Happy
- 우선순위: Medium
- 테스트 단계:
  1. POST /files/upload (file: 유효한 PNG, type: "ITEM_IMAGE")
- 예상 결과: HTTP 201

---

**TC-FILE-003** | 정상 WEBP 이미지 업로드
- 분류: Happy
- 우선순위: Medium
- 테스트 단계:
  1. POST /files/upload (file: 유효한 WEBP, type: "ITEM_IMAGE")
- 예상 결과: HTTP 201

---

**TC-FILE-004** | 지원하지 않는 파일 형식 차단 (GIF)
- 분류: Exception
- 우선순위: High
- 테스트 단계:
  1. POST /files/upload (file: GIF 파일, type: "ITEM_IMAGE")
- 예상 결과: HTTP 400, error.code: "ITEM-E002"

---

**TC-FILE-005** | 이미지 확장자 스푸핑 차단 (Magic Bytes 검증)
- 분류: Exception
- 우선순위: Critical
- 사전 조건: 확장자는 .jpg이지만 실제 내용은 PHP 스크립트인 파일 준비
- 테스트 단계:
  1. POST /files/upload (file: 확장자 위조 파일 - test.jpg로 이름 변경된 악성 파일)
- 예상 결과: HTTP 400, error.code: "ITEM-E002"
- 검증 포인트: 서버가 Magic Bytes(파일 시그니처) 기반으로 실제 파일 형식을 검증하는지 확인
  - JPG: FF D8 FF
  - PNG: 89 50 4E 47
  - WEBP: 52 49 46 46 ... 57 45 42 50

---

**TC-FILE-006** | 파일 용량 10MB 초과 차단
- 분류: Boundary
- 우선순위: High
- 테스트 단계:
  1. POST /files/upload (file: 10MB + 1byte 이미지)
- 예상 결과: HTTP 400, error.code: "ITEM-E003"

---

**TC-FILE-007** | 파일 용량 정확히 10MB 허용
- 분류: Boundary
- 우선순위: Medium
- 테스트 단계:
  1. POST /files/upload (file: 정확히 10MB 이미지)
- 예상 결과: HTTP 201

---

**TC-FILE-008** | 인증 없이 파일 업로드 시도
- 분류: Exception
- 우선순위: High
- 테스트 단계:
  1. POST /files/upload (Authorization 헤더 없음)
- 예상 결과: HTTP 401

---

## 3. 상품 관리 (ITEM)

### 3-1. 상품 등록 (ITEM-001)

---

**TC-ITEM-001** | 정상 상품 등록 (PURCHASE 유형)
- 분류: Happy
- 우선순위: Critical
- 사전 조건: 이메일 인증 완료된 로그인 상태, 이미지 업로드 완료 후 imageId 보유
- 테스트 단계:
  1. POST /items (title: "테스트 상품", description: 10자 이상, category: "TEMPLATE", saleType: "PURCHASE", price: 5000, imageIds: ["img-uuid-001"], status: "PUBLISHED")
- 예상 결과: HTTP 201, { itemId }

---

**TC-ITEM-002** | 정상 상품 등록 (SUBSCRIBE 유형)
- 분류: Happy
- 우선순위: Critical
- 사전 조건: 이메일 인증 완료된 로그인 상태
- 테스트 단계:
  1. POST /items (saleType: "SUBSCRIBE", subscriptionPlans: [{planName: "Basic", period: "MONTHLY", planPrice: 3000}], imageIds: 포함)
- 예상 결과: HTTP 201, { itemId }

---

**TC-ITEM-003** | 정상 상품 등록 (BOTH 유형)
- 분류: Happy
- 우선순위: High
- 사전 조건: 이메일 인증 완료된 로그인 상태
- 테스트 단계:
  1. POST /items (saleType: "BOTH", price: 10000, subscriptionPlans: 1개 이상)
- 예상 결과: HTTP 201, { itemId }

---

**TC-ITEM-004** | 이메일 미인증 상태에서 상품 등록 차단
- 분류: Exception
- 우선순위: Critical
- 사전 조건: 이메일 미인증 계정으로 로그인
- 테스트 단계:
  1. POST /items (유효한 상품 정보)
- 예상 결과: HTTP 403, error.code: "ITEM-E001"

---

**TC-ITEM-005** | 가격 100원 미만 차단
- 분류: Boundary
- 우선순위: High
- 테스트 단계:
  1. POST /items (saleType: "PURCHASE", price: 99)
- 예상 결과: HTTP 400, error.code: "ITEM-E005"

---

**TC-ITEM-006** | 가격 정확히 100원 허용
- 분류: Boundary
- 우선순위: Medium
- 테스트 단계:
  1. POST /items (saleType: "PURCHASE", price: 100)
- 예상 결과: HTTP 201

---

**TC-ITEM-007** | 가격 10,000,000원 초과 차단
- 분류: Boundary
- 우선순위: High
- 테스트 단계:
  1. POST /items (saleType: "PURCHASE", price: 10000001)
- 예상 결과: HTTP 400, error.code: "ITEM-E005"

---

**TC-ITEM-008** | 가격 정확히 10,000,000원 허용
- 분류: Boundary
- 우선순위: Medium
- 테스트 단계:
  1. POST /items (saleType: "PURCHASE", price: 10000000)
- 예상 결과: HTTP 201

---

**TC-ITEM-009** | SUBSCRIBE 유형에 구독 플랜 미포함 시 차단
- 분류: Exception
- 우선순위: High
- 테스트 단계:
  1. POST /items (saleType: "SUBSCRIBE", subscriptionPlans: []) → 빈 배열
- 예상 결과: HTTP 400, error.code: "ITEM-E007"

---

**TC-ITEM-010** | 이미지 11장 초과 등록 차단
- 분류: Boundary
- 우선순위: High
- 테스트 단계:
  1. POST /items (imageIds: 11개)
- 예상 결과: HTTP 400, error.code: "ITEM-E004"

---

**TC-ITEM-011** | 유효하지 않은 카테고리 코드
- 분류: Exception
- 우선순위: Medium
- 테스트 단계:
  1. POST /items (category: "INVALID_CATEGORY")
- 예상 결과: HTTP 400, error.code: "ITEM-E006"

---

**TC-ITEM-012** | title 최소 길이 경계 - 2자 허용
- 분류: Boundary
- 우선순위: Medium
- 테스트 단계:
  1. POST /items (title: "ab") → 2자
- 예상 결과: HTTP 201

---

**TC-ITEM-013** | title 최소 길이 경계 - 1자 거부
- 분류: Boundary
- 우선순위: Medium
- 테스트 단계:
  1. POST /items (title: "a") → 1자
- 예상 결과: HTTP 400

---

**TC-ITEM-014** | description 최소 길이 경계 - 10자 허용
- 분류: Boundary
- 우선순위: Medium
- 테스트 단계:
  1. POST /items (description: "0123456789") → 10자
- 예상 결과: HTTP 201

---

**TC-ITEM-015** | description 최소 길이 경계 - 9자 거부
- 분류: Boundary
- 우선순위: Medium
- 테스트 단계:
  1. POST /items (description: "012345678") → 9자
- 예상 결과: HTTP 400

---

### 3-2. 상품 수정 (ITEM-002)

---

**TC-ITEM-020** | 본인 상품 정상 수정
- 분류: Happy
- 우선순위: High
- 사전 조건: 등록된 상품의 셀러로 로그인
- 테스트 단계:
  1. PUT /items/{itemId} (title: "수정된 상품명")
- 예상 결과: HTTP 200, { itemId, updatedAt }

---

**TC-ITEM-021** | 타인 상품 수정 시도 차단
- 분류: Exception
- 우선순위: Critical
- 사전 조건: 상품 소유자가 아닌 다른 사용자로 로그인
- 테스트 단계:
  1. PUT /items/{타인_itemId} (title: "해킹 시도")
- 예상 결과: HTTP 403, error.code: "ITEM-E020"

---

**TC-ITEM-022** | 존재하지 않는 상품 수정 시도
- 분류: Exception
- 우선순위: Medium
- 테스트 단계:
  1. PUT /items/99999999 (유효한 수정 데이터)
- 예상 결과: HTTP 404, error.code: "ITEM-E022"

---

**TC-ITEM-023** | 구독자 있는 플랜 가격 변경 차단
- 분류: Exception
- 우선순위: Critical
- 사전 조건: 해당 구독 플랜에 활성 구독자가 1명 이상 존재
- 테스트 단계:
  1. PUT /items/{itemId} (subscriptionPlans: [{planId: 기존플랜ID, planPrice: 기존가격+1000}])
- 예상 결과: HTTP 422, error.code: "ITEM-E021"

---

**TC-ITEM-024** | 구독자 없는 플랜 가격 변경 허용
- 분류: Happy
- 우선순위: Medium
- 사전 조건: 해당 플랜의 구독자가 0명인 상태
- 테스트 단계:
  1. PUT /items/{itemId} (구독자 없는 플랜의 planPrice 변경)
- 예상 결과: HTTP 200

---

**TC-ITEM-025** | PUBLISHED 상태 상품도 수정 가능
- 분류: Happy
- 우선순위: Medium
- 사전 조건: PUBLISHED 상태 상품
- 테스트 단계:
  1. PUT /items/{itemId} (status가 PUBLISHED인 상품 수정)
- 예상 결과: HTTP 200

---

### 3-3. 상품 삭제 (ITEM-003)

---

**TC-ITEM-030** | 정상 상품 삭제 (소프트 삭제)
- 분류: Happy
- 우선순위: High
- 사전 조건: 활성 구독자 없는 본인 상품
- 테스트 단계:
  1. DELETE /items/{itemId}
  2. GET /items/{itemId} 로 삭제 확인
- 예상 결과: HTTP 204, 이후 GET 시 HTTP 404 반환

---

**TC-ITEM-031** | 활성 구독자 있는 상품 삭제 차단
- 분류: Exception
- 우선순위: Critical
- 사전 조건: 해당 상품에 활성 구독자 1명 이상
- 테스트 단계:
  1. DELETE /items/{itemId}
- 예상 결과: HTTP 422, error.code: "ITEM-E030"

---

**TC-ITEM-032** | 타인 상품 삭제 시도 차단
- 분류: Exception
- 우선순위: Critical
- 테스트 단계:
  1. DELETE /items/{타인_itemId}
- 예상 결과: HTTP 403, error.code: "ITEM-E031"

---

**TC-ITEM-033** | 삭제된 상품 URL 접근 시 404 반환
- 분류: Exception
- 우선순위: Medium
- 사전 조건: 삭제된 상품
- 테스트 단계:
  1. GET /items/{삭제된_itemId}
- 예상 결과: HTTP 404, error.code: "BROWSE-E001"

---

**TC-ITEM-034** | 삭제 후 기존 구매 내역 유지 확인
- 분류: Happy
- 우선순위: Medium
- 사전 조건: 구매 내역이 있는 상품 삭제 후
- 테스트 단계:
  1. GET /orders (삭제된 상품의 주문 조회)
- 예상 결과: 주문 내역은 유지됨 (상품은 삭제 표시)

---

### 3-4. 상품 상태 변경 (ITEM-004)

---

**TC-ITEM-040** | DRAFT → PUBLISHED 전환
- 분류: Happy
- 우선순위: High
- 사전 조건: DRAFT 상태 본인 상품
- 테스트 단계:
  1. PATCH /items/{itemId}/status (status: "PUBLISHED")
- 예상 결과: HTTP 200, { itemId, status: "PUBLISHED" }

---

**TC-ITEM-041** | PUBLISHED → DRAFT 전환 (비공개)
- 분류: Happy
- 우선순위: High
- 사전 조건: PUBLISHED 상태 본인 상품
- 테스트 단계:
  1. PATCH /items/{itemId}/status (status: "DRAFT")
  2. GET /items/{itemId} (비로그인 또는 타인으로 접근)
- 예상 결과: 상태 변경 HTTP 200, 이후 비로그인 접근 시 HTTP 403

---

**TC-ITEM-042** | 비공개 상품을 본인이 조회 가능
- 분류: Happy
- 우선순위: Medium
- 사전 조건: DRAFT 상태 상품의 소유자로 로그인
- 테스트 단계:
  1. GET /items/{itemId} (본인 DRAFT 상품 조회)
- 예상 결과: HTTP 200 (본인에게는 정상 반환)

---

### 3-5. 내 상품 목록 조회 (ITEM-005)

---

**TC-ITEM-050** | 셀러 본인 상품 전체 조회 (ALL)
- 분류: Happy
- 우선순위: Medium
- 사전 조건: 상품 여러 건 등록된 상태
- 테스트 단계:
  1. GET /items/my (status: "ALL")
- 예상 결과: HTTP 200, 공개/비공개 상품 모두 포함된 페이지네이션 응답

---

**TC-ITEM-051** | 정렬 파라미터 검증 (title ASC)
- 분류: Happy
- 우선순위: Low
- 테스트 단계:
  1. GET /items/my (sort: "title", order: "ASC")
- 예상 결과: HTTP 200, title 기준 오름차순 정렬

---

**TC-ITEM-052** | size 최대 100 초과 시 처리
- 분류: Boundary
- 우선순위: Medium
- 테스트 단계:
  1. GET /items/my (size: 101)
- 예상 결과: HTTP 400 또는 size: 100으로 자동 보정

---

---

## 4. 탐색 및 검색 (BROWSE)

### 4-1. 상품 목록 탐색 (BROWSE-001)

---

**TC-BROWSE-001** | 비로그인 상태 상품 목록 조회
- 분류: Happy
- 우선순위: High
- 사전 조건: PUBLISHED 상품 존재
- 테스트 단계:
  1. GET /items (인증 헤더 없음)
- 예상 결과: HTTP 200, PUBLISHED 상품만 포함

---

**TC-BROWSE-002** | DRAFT / 삭제 상품 목록 미노출 확인
- 분류: Exception
- 우선순위: High
- 사전 조건: DRAFT 상품 및 삭제 상품 존재
- 테스트 단계:
  1. GET /items (비로그인)
- 예상 결과: DRAFT, 삭제 상품이 목록에 포함되지 않음

---

**TC-BROWSE-003** | 카테고리 필터 적용
- 분류: Happy
- 우선순위: Medium
- 테스트 단계:
  1. GET /items?category=TEMPLATE
- 예상 결과: HTTP 200, TEMPLATE 카테고리 상품만 반환

---

**TC-BROWSE-004** | 가격 범위 필터 적용
- 분류: Happy
- 우선순위: Medium
- 테스트 단계:
  1. GET /items?minPrice=1000&maxPrice=10000
- 예상 결과: HTTP 200, 1000~10000원 범위 상품만 반환

---

**TC-BROWSE-005** | size 최대 50 초과 시 처리
- 분류: Boundary
- 우선순위: Medium
- 테스트 단계:
  1. GET /items?size=51
- 예상 결과: HTTP 400 또는 size: 50으로 자동 보정

---

### 4-2. 상품 검색 (BROWSE-002)

---

**TC-BROWSE-010** | 정상 키워드 검색
- 분류: Happy
- 우선순위: High
- 테스트 단계:
  1. GET /items/search?q=포토샵
- 예상 결과: HTTP 200, 관련 상품 목록 반환

---

**TC-BROWSE-011** | 검색어 0자 입력 차단
- 분류: Boundary
- 우선순위: Medium
- 테스트 단계:
  1. GET /items/search?q= (빈 문자열)
- 예상 결과: HTTP 400

---

**TC-BROWSE-012** | 검색어 100자 초과 차단
- 분류: Boundary
- 우선순위: Medium
- 테스트 단계:
  1. GET /items/search?q={101자_문자열}
- 예상 결과: HTTP 400

---

**TC-BROWSE-013** | 셀러 닉네임으로 검색 가능 여부
- 분류: Happy
- 우선순위: Medium
- 사전 조건: 특정 닉네임의 셀러 상품 존재
- 테스트 단계:
  1. GET /items/search?q={셀러_닉네임}
- 예상 결과: HTTP 200, 해당 셀러의 상품 포함

---

### 4-3. 상품 상세 조회 (BROWSE-003)

---

**TC-BROWSE-020** | 정상 상품 상세 조회 (비로그인)
- 분류: Happy
- 우선순위: High
- 사전 조건: PUBLISHED 상품
- 테스트 단계:
  1. GET /items/{itemId} (인증 없음)
- 예상 결과: HTTP 200, 상품 전체 정보 (이미지, 구독플랜, 셀러정보, viewCount 등) 반환

---

**TC-BROWSE-021** | 존재하지 않는 상품 상세 조회
- 분류: Exception
- 우선순위: Medium
- 테스트 단계:
  1. GET /items/99999999
- 예상 결과: HTTP 404, error.code: "BROWSE-E001"

---

**TC-BROWSE-022** | 비공개 상품을 타인이 조회 시 차단
- 분류: Exception
- 우선순위: High
- 사전 조건: DRAFT 상태 상품, 다른 사용자로 로그인
- 테스트 단계:
  1. GET /items/{DRAFT_itemId} (타인 또는 비로그인)
- 예상 결과: HTTP 403, error.code: "BROWSE-E002"

---

---

## 5. 구매 (ORDER)

### 5-1. 단일 구매 (ORDER-001)

---

**TC-ORDER-001** | 정상 구매
- 분류: Happy
- 우선순위: Critical
- 사전 조건: PUBLISHED PURCHASE 유형 상품, 로그인 상태 (상품 소유자가 아닌 계정)
- 테스트 단계:
  1. POST /orders (itemId: 유효한 아이템 ID, paymentMethod: "CARD")
- 예상 결과: HTTP 201, { orderId, itemId, amount, paymentMethod, status: "COMPLETED", paidAt }

---

**TC-ORDER-002** | 본인 상품 구매 차단
- 분류: Exception
- 우선순위: Critical
- 사전 조건: 본인이 등록한 상품
- 테스트 단계:
  1. POST /orders (itemId: 본인 상품 ID)
- 예상 결과: HTTP 422, error.code: "ORDER-E001", "본인 상품은 구매할 수 없습니다."

---

**TC-ORDER-003** | 존재하지 않는 상품 구매 시도
- 분류: Exception
- 우선순위: High
- 테스트 단계:
  1. POST /orders (itemId: 99999999)
- 예상 결과: HTTP 404, error.code: "ORDER-E002"

---

**TC-ORDER-004** | 비공개(DRAFT) 상품 구매 시도
- 분류: Exception
- 우선순위: High
- 사전 조건: DRAFT 상태 상품
- 테스트 단계:
  1. POST /orders (itemId: DRAFT 상태 상품 ID)
- 예상 결과: HTTP 404, error.code: "ORDER-E002"

---

**TC-ORDER-005** | 구독 전용(SUBSCRIBE) 상품 단건 구매 차단
- 분류: Exception
- 우선순위: Critical
- 사전 조건: saleType이 SUBSCRIBE인 상품
- 테스트 단계:
  1. POST /orders (itemId: SUBSCRIBE 전용 상품 ID)
- 예상 결과: HTTP 422, error.code: "ORDER-E004", "해당 상품은 구독으로만 이용 가능합니다."

---

**TC-ORDER-006** | BOTH 유형 상품 단건 구매 허용
- 분류: Happy
- 우선순위: High
- 사전 조건: saleType이 BOTH인 상품
- 테스트 단계:
  1. POST /orders (itemId: BOTH 유형 상품 ID)
- 예상 결과: HTTP 201

---

**TC-ORDER-007** | 비로그인 상태 구매 시도
- 분류: Exception
- 우선순위: High
- 테스트 단계:
  1. POST /orders (Authorization 헤더 없음)
- 예상 결과: HTTP 401

---

**TC-ORDER-008** | 동일 상품 중복 구매 허용 (디지털 콘텐츠)
- 분류: Happy
- 우선순위: Medium
- 사전 조건: 이미 구매한 상품
- 테스트 단계:
  1. POST /orders (이미 구매한 itemId)
- 예상 결과: HTTP 201 (중복 구매 허용)

---

### 5-2. 구매 내역 조회 (ORDER-002)

---

**TC-ORDER-010** | 구매 내역 정상 조회
- 분류: Happy
- 우선순위: High
- 사전 조건: 구매 내역 1건 이상
- 테스트 단계:
  1. GET /orders
- 예상 결과: HTTP 200, 페이지네이션 응답

---

**TC-ORDER-011** | 날짜 범위 필터 조회
- 분류: Happy
- 우선순위: Medium
- 테스트 단계:
  1. GET /orders?startDate=2026-01-01&endDate=2026-05-09
- 예상 결과: HTTP 200, 해당 기간 내 구매 내역만 반환

---

**TC-ORDER-012** | 타인 구매 내역 접근 불가 확인
- 분류: Exception
- 우선순위: Critical
- 사전 조건: 사용자 A의 구매 내역, 사용자 B로 로그인
- 테스트 단계:
  1. GET /orders (사용자 B의 토큰으로 호출)
- 예상 결과: HTTP 200이나 본인 내역만 반환 (타인 내역 미포함)

---

### 5-3. 환불 (ORDER-003)

---

**TC-ORDER-020** | 정상 환불 (7일 이내, 미열람)
- 분류: Happy
- 우선순위: Critical
- 사전 조건: 구매 후 7일 이내, 콘텐츠 미열람
- 테스트 단계:
  1. POST /orders/{orderId}/cancel (reason: "단순 변심")
- 예상 결과: HTTP 200, { orderId, status: "REFUNDED", refundAmount, refundedAt }

---

**TC-ORDER-021** | 환불 기간 7일 초과 시 차단
- 분류: Exception
- 우선순위: Critical
- 사전 조건: 구매일로부터 8일 이상 경과한 주문
- 테스트 단계:
  1. POST /orders/{orderId}/cancel
- 예상 결과: HTTP 422, error.code: "ORDER-E010", "구매 후 7일이 경과하여 환불이 불가합니다."

---

**TC-ORDER-022** | 구매 후 정확히 7일째 환불 가능 경계 검증
- 분류: Boundary
- 우선순위: High
- 사전 조건: 구매 후 정확히 7일 = 168시간 시점
- 테스트 단계:
  1. 구매 시각 기준 168시간 이내 POST /orders/{orderId}/cancel
  2. 168시간 경과 후 POST /orders/{orderId}/cancel
- 예상 결과: 168시간 이내: HTTP 200, 168시간 초과: HTTP 422

---

**TC-ORDER-023** | 콘텐츠 열람 후 환불 차단
- 분류: Exception
- 우선순위: Critical
- 사전 조건: 콘텐츠 열람(다운로드) 이력이 있는 주문, 구매 7일 이내
- 테스트 단계:
  1. POST /orders/{orderId}/cancel
- 예상 결과: HTTP 422, error.code: "ORDER-E011", "콘텐츠 열람 이력이 있어 환불이 불가합니다."

---

**TC-ORDER-024** | 타인 주문 환불 시도 차단
- 분류: Exception
- 우선순위: High
- 사전 조건: 사용자 B의 주문 ID
- 테스트 단계:
  1. POST /orders/{사용자B_orderId}/cancel (사용자 A 토큰)
- 예상 결과: HTTP 403

---

---

## 6. 구독 (SUB)

### 6-1. 구독 신청 (SUB-001)

---

**TC-SUB-001** | 정상 구독 신청
- 분류: Happy
- 우선순위: Critical
- 사전 조건: PUBLISHED SUBSCRIBE 유형 상품, 로그인 상태 (상품 소유자가 아닌 계정)
- 테스트 단계:
  1. POST /subscriptions (itemId, planId, paymentMethod: "CARD")
- 예상 결과: HTTP 201, { subscriptionId, planName, nextBillingAt, status: "ACTIVE" }

---

**TC-SUB-002** | 본인 상품 구독 차단
- 분류: Exception
- 우선순위: Critical
- 사전 조건: 본인 등록 상품
- 테스트 단계:
  1. POST /subscriptions (itemId: 본인 상품 ID)
- 예상 결과: HTTP 422, error.code: "SUB-E002", "본인 상품은 구독할 수 없습니다."

---

**TC-SUB-003** | 중복 구독 방지 (이미 활성 구독 중)
- 분류: Exception
- 우선순위: Critical
- 사전 조건: 해당 상품 활성 구독 중
- 테스트 단계:
  1. POST /subscriptions (이미 구독 중인 itemId)
- 예상 결과: HTTP 409, error.code: "SUB-E001", "이미 해당 상품을 구독 중입니다."

---

**TC-SUB-004** | 중복 구독 방지 - Race Condition 테스트
- 분류: Exception
- 우선순위: Critical
- 사전 조건: 동일 사용자, 동일 상품으로 동시 구독 요청 환경 구성
- 테스트 단계:
  1. 동일 계정으로 POST /subscriptions 요청을 동시에 2건 발송 (병렬 요청)
- 예상 결과: 1건만 HTTP 201 성공, 나머지 1건은 HTTP 409 (SUB-E001) 반환
- 검증 포인트: DB에 중복 구독 레코드가 생성되지 않았는지 직접 확인 (DBA 협의)

---

**TC-SUB-005** | PURCHASE 전용 상품 구독 시도 차단
- 분류: Exception
- 우선순위: High
- 사전 조건: saleType이 PURCHASE인 상품
- 테스트 단계:
  1. POST /subscriptions (itemId: PURCHASE 전용 상품 ID)
- 예상 결과: HTTP 422, error.code: "SUB-E003", "해당 상품은 구독을 지원하지 않습니다."

---

**TC-SUB-006** | 다음 결제일 계산 정확성 검증 (MONTHLY)
- 분류: Happy
- 우선순위: High
- 사전 조건: MONTHLY 플랜 구독
- 테스트 단계:
  1. POST /subscriptions (period: "MONTHLY")
  2. 응답의 nextBillingAt 확인
- 예상 결과: nextBillingAt = 구독 시작일 + 1개월 (정확한 날짜)

---

**TC-SUB-007** | 다음 결제일 계산 정확성 검증 (QUARTERLY)
- 분류: Happy
- 우선순위: Medium
- 테스트 단계:
  1. POST /subscriptions (period: "QUARTERLY")
- 예상 결과: nextBillingAt = 구독 시작일 + 3개월

---

**TC-SUB-008** | 다음 결제일 계산 정확성 검증 (YEARLY)
- 분류: Happy
- 우선순위: Medium
- 테스트 단계:
  1. POST /subscriptions (period: "YEARLY")
- 예상 결과: nextBillingAt = 구독 시작일 + 1년

---

### 6-2. 구독 해지 (SUB-002)

---

**TC-SUB-010** | 정상 구독 해지 신청
- 분류: Happy
- 우선순위: Critical
- 사전 조건: 활성 구독 중
- 테스트 단계:
  1. POST /subscriptions/{subscriptionId}/cancel
- 예상 결과: HTTP 200, { status: "CANCEL_REQUESTED", cancelledAt, activeUntil }

---

**TC-SUB-011** | 해지 후 구독 기간 만료까지 서비스 이용 가능 확인
- 분류: Happy
- 우선순위: Critical
- 사전 조건: CANCEL_REQUESTED 상태, activeUntil 이전
- 테스트 단계:
  1. 구독 해지 신청 후 구독 내역 조회
  2. GET /subscriptions (status: "CANCEL_REQUESTED")
- 예상 결과: 상태 CANCEL_REQUESTED, activeUntil 날짜 정상 표시

---

**TC-SUB-012** | 구독 기간 만료 후 상태 CANCELLED 전환 확인
- 분류: Happy
- 우선순위: Critical
- 사전 조건: CANCEL_REQUESTED 상태이고 activeUntil이 경과된 구독
- 테스트 단계:
  1. GET /subscriptions (status: "ALL")
- 예상 결과: 해당 구독의 status가 "CANCELLED"로 변경됨
- 검증 포인트: 배치 또는 스케줄러가 정상 동작하는지 확인

---

**TC-SUB-013** | 타인 구독 해지 시도 차단
- 분류: Exception
- 우선순위: High
- 테스트 단계:
  1. POST /subscriptions/{타인_subscriptionId}/cancel
- 예상 결과: HTTP 403

---

**TC-SUB-014** | 이미 해지된 구독 재해지 시도
- 분류: Exception
- 우선순위: Medium
- 사전 조건: CANCELLED 상태 구독
- 테스트 단계:
  1. POST /subscriptions/{subscriptionId}/cancel (이미 해지된 구독)
- 예상 결과: HTTP 422 또는 409

---

### 6-3. 구독 해지 취소 (재활성화)

---

**TC-SUB-020** | 정상 구독 해지 취소 (재활성화)
- 분류: Happy
- 우선순위: High
- 사전 조건: CANCEL_REQUESTED 상태 (기간 만료 이전)
- 테스트 단계:
  1. POST /subscriptions/{subscriptionId}/reactivate
- 예상 결과: HTTP 200, { subscriptionId, status: "ACTIVE" }

---

**TC-SUB-021** | 기간 만료 후 CANCELLED 상태에서 재활성화 시도 차단
- 분류: Exception
- 우선순위: High
- 사전 조건: CANCELLED 상태 구독 (기간 만료 후)
- 테스트 단계:
  1. POST /subscriptions/{subscriptionId}/reactivate
- 예상 결과: HTTP 422 (재활성화 불가)

---

### 6-4. 구독 내역 조회 (SUB-003)

---

**TC-SUB-030** | 구독 내역 전체 조회
- 분류: Happy
- 우선순위: Medium
- 테스트 단계:
  1. GET /subscriptions (status: "ALL")
- 예상 결과: HTTP 200, 페이지네이션 응답

---

**TC-SUB-031** | 활성 구독만 필터 조회
- 분류: Happy
- 우선순위: Medium
- 테스트 단계:
  1. GET /subscriptions (status: "ACTIVE")
- 예상 결과: HTTP 200, ACTIVE 구독만 반환

---

---

## 7. 프로필 (PROFILE)

### 7-1. 셀러 공개 프로필 조회 (PROFILE-001)

---

**TC-PROFILE-001** | 공개 프로필 정상 조회 (비로그인)
- 분류: Happy
- 우선순위: High
- 사전 조건: 상품이 있는 셀러 닉네임
- 테스트 단계:
  1. GET /users/{nickname}/profile (인증 없음)
- 예상 결과: HTTP 200, { nickname, bio, profileImageUrl, itemCount, subscriberCount, joinedAt, items }

---

**TC-PROFILE-002** | 공개 프로필에서 PUBLISHED 상품만 노출
- 분류: Exception
- 우선순위: High
- 사전 조건: DRAFT 상품과 PUBLISHED 상품이 혼재한 셀러
- 테스트 단계:
  1. GET /users/{nickname}/profile
- 예상 결과: items에 PUBLISHED 상품만 포함

---

**TC-PROFILE-003** | 존재하지 않는 닉네임 조회
- 분류: Exception
- 우선순위: Medium
- 테스트 단계:
  1. GET /users/nonexistent_nick/profile
- 예상 결과: HTTP 404

---

### 7-2. 내 프로필 수정 (PROFILE-002)

---

**TC-PROFILE-010** | 정상 닉네임 변경
- 분류: Happy
- 우선순위: High
- 사전 조건: 로그인 상태
- 테스트 단계:
  1. PATCH /users/me (nickname: "new_nick_001")
- 예상 결과: HTTP 200, 변경된 프로필 반환

---

**TC-PROFILE-011** | 닉네임 중복 검사 (본인 제외)
- 분류: Exception
- 우선순위: Critical
- 사전 조건: 사용자 A (현재 닉네임: "user_a")와 사용자 B (닉네임: "user_b")
- 테스트 단계:
  1. 사용자 A가 PATCH /users/me (nickname: "user_b") → 타인 닉네임으로 변경 시도
- 예상 결과: HTTP 409, error.code: "AUTH-E002"

---

**TC-PROFILE-012** | 닉네임 중복 검사 - 본인 닉네임 재설정 허용
- 분류: Happy
- 우선순위: High
- 사전 조건: 사용자 A (현재 닉네임: "user_a")
- 테스트 단계:
  1. 사용자 A가 PATCH /users/me (nickname: "user_a") → 본인 현재 닉네임으로 요청
- 예상 결과: HTTP 200 (본인 닉네임은 중복으로 처리하지 않음)

---

**TC-PROFILE-013** | bio 최대 200자 경계 검증
- 분류: Boundary
- 우선순위: Medium
- 테스트 단계:
  1. PATCH /users/me (bio: 200자 문자열) → HTTP 200
  2. PATCH /users/me (bio: 201자 문자열) → HTTP 400 기대

---

**TC-PROFILE-014** | 프로필 이미지 정상 변경
- 분류: Happy
- 우선순위: Medium
- 사전 조건: 이미지 업로드 후 profileImageId 보유
- 테스트 단계:
  1. PATCH /users/me (profileImageId: "img-uuid-profile-001")
- 예상 결과: HTTP 200, 변경된 profileImageUrl 반환

---

### 7-3. 셀러 수익 현황 조회 (PROFILE-003)

---

**TC-PROFILE-020** | 셀러 수익 현황 정상 조회
- 분류: Happy
- 우선순위: Medium
- 사전 조건: 판매 내역이 있는 셀러로 로그인
- 테스트 단계:
  1. GET /users/me/revenue (year: 2026)
- 예상 결과: HTTP 200, { totalRevenue, totalFee, netRevenue, activeSubscribers, monthlyRevenue, itemRevenue }

---

**TC-PROFILE-021** | 수수료 10% 계산 정확성 검증
- 분류: Happy
- 우선순위: High
- 사전 조건: 100,000원 매출 발생
- 테스트 단계:
  1. GET /users/me/revenue
- 예상 결과: totalFee = totalRevenue * 0.1 (10%), netRevenue = totalRevenue - totalFee

---

**TC-PROFILE-022** | 타인 수익 현황 접근 불가
- 분류: Exception
- 우선순위: High
- 테스트 단계:
  1. GET /users/me/revenue (타인 토큰 → 본인 데이터만 반환되어야 함)
- 예상 결과: 본인 데이터만 반환 (API 설계상 /users/me로 본인 격리)

---

## 테스트 케이스 요약

| 기능 영역 | 총 케이스 수 | Critical | High | Medium | Low |
|---|---|---|---|---|---|
| 인증 (AUTH) | 37 | 9 | 18 | 8 | 2 |
| 파일 업로드 (FILE) | 8 | 1 | 5 | 2 | 0 |
| 상품 관리 (ITEM) | 26 | 7 | 12 | 6 | 1 |
| 탐색/검색 (BROWSE) | 13 | 0 | 5 | 7 | 1 |
| 구매 (ORDER) | 15 | 6 | 6 | 3 | 0 |
| 구독 (SUB) | 21 | 7 | 10 | 4 | 0 |
| 프로필 (PROFILE) | 13 | 1 | 7 | 5 | 0 |
| **합계** | **133** | **31** | **63** | **35** | **4** |

---

## 비즈니스 정책 커버리지 확인

| 비즈니스 정책 | 관련 TC | 커버 여부 |
|---|---|---|
| 본인 상품 구매 차단 | TC-ORDER-002 | 완료 |
| 구독 전용 상품 단건 구매 차단 | TC-ORDER-005 | 완료 |
| 환불 정책 (7일 이내, 미열람) | TC-ORDER-020~023 | 완료 |
| 구독 해지 후 기간 만료 동작 | TC-SUB-011, TC-SUB-012 | 완료 |
| 5회 로그인 실패 계정 잠금 | TC-AUTH-033, TC-AUTH-034 | 완료 |
| 이미지 확장자 스푸핑 차단 (Magic Bytes) | TC-FILE-005 | 완료 |
| 중복 구독 방지 (Race Condition) | TC-SUB-004 | 완료 |
| 닉네임 중복 검사 (본인 제외) | TC-PROFILE-011, TC-PROFILE-012 | 완료 |
| 이메일 미인증 셀러 기능 차단 | TC-AUTH-024, TC-ITEM-004 | 완료 |
| 본인 상품 구독 차단 | TC-SUB-002 | 완료 |
| 활성 구독자 있는 상품 삭제 차단 | TC-ITEM-031 | 완료 |
| 구독자 있는 플랜 가격 변경 차단 | TC-ITEM-023 | 완료 |
| 탈퇴 후 30일 이내 재가입 차단 | TC-AUTH-073 | 완료 |
