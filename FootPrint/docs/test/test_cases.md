# 테스트 케이스 문서

- **프로젝트명**: 발자국 (Foot-Print)
- **문서 버전**: v1.0.0
- **작성일**: 2026-05-09
- **작성자**: QA
- **참조 문서**: SRS.md, api_requirements.md, screen_definition.md

---

## 목차

1. [인증 (AUTH)](#1-인증-auth)
2. [장소 CRUD (PLACE)](#2-장소-crud-place)
3. [카테고리 (CATEGORY)](#3-카테고리-category)
4. [통계 (STATS)](#4-통계-stats)
5. [필터/검색 (SEARCH)](#5-필터검색-search)

---

## 우선순위 기준

| 우선순위 | 기준 |
|---------|------|
| P1 | 핵심 기능 — 실패 시 서비스 불가 |
| P2 | 주요 기능 — 실패 시 사용자 경험 저하 |
| P3 | 부가 기능 — 실패 시 불편하지만 서비스 유지 가능 |

---

## 1. 인증 (AUTH)

### 1.1 정상 흐름

| TC-ID | 테스트 케이스명 | 전제조건 | 테스트 단계 | 입력 데이터 | 기대 결과 | 우선순위 |
|-------|--------------|---------|-----------|-----------|---------|---------|
| TC-AUTH-001 | 정상 회원가입 | 가입되지 않은 이메일 | 1. `/register` 접속<br>2. 이메일 입력<br>3. 닉네임 입력<br>4. 비밀번호 입력<br>5. 비밀번호 확인 입력<br>6. 회원가입 버튼 클릭 | email: `qa_test@example.com`<br>nickname: `테스트유저`<br>password: `Test1234!`<br>passwordConfirm: `Test1234!` | 1. HTTP 201 응답<br>2. 성공 토스트 "회원가입이 완료되었습니다." 표시<br>3. `/login` 페이지로 이동 | P1 |
| TC-AUTH-002 | 정상 로그인 | 가입된 사용자 존재 | 1. `/login` 접속<br>2. 이메일 입력<br>3. 비밀번호 입력<br>4. 로그인 버튼 클릭 | email: `qa_test@example.com`<br>password: `Test1234!` | 1. HTTP 200 응답<br>2. Access Token 발급<br>3. Refresh Token 쿠키 저장<br>4. `/map` 페이지로 이동 | P1 |
| TC-AUTH-003 | 정상 로그아웃 | 로그인 상태 | 1. GNB 프로필 드롭다운 클릭<br>2. 로그아웃 클릭 | - | 1. HTTP 200 응답<br>2. Refresh Token 쿠키 삭제<br>3. `/login` 페이지로 이동 | P1 |
| TC-AUTH-004 | Access Token 자동 갱신 | Access Token 만료 상태, 유효한 Refresh Token 존재 | 1. 만료된 Access Token으로 API 호출<br>2. 401 TOKEN_EXPIRED 수신<br>3. `/api/v1/auth/refresh` 자동 호출 | Refresh Token 쿠키 유효 | 1. 새 Access Token 발급<br>2. 원래 API 요청 재시도 성공<br>3. 사용자는 로그인 유지 상태 | P1 |
| TC-AUTH-005 | 내 정보 조회 | 로그인 상태 | 1. `GET /api/v1/users/me` 호출 | Authorization: Bearer {accessToken} | 1. HTTP 200 응답<br>2. `data.userId`, `data.email`, `data.nickname` 필드 포함 | P1 |

### 1.2 예외 흐름

| TC-ID | 테스트 케이스명 | 전제조건 | 테스트 단계 | 입력 데이터 | 기대 결과 | 우선순위 |
|-------|--------------|---------|-----------|-----------|---------|---------|
| TC-AUTH-006 | 중복 이메일 회원가입 | 동일 이메일로 기가입된 계정 존재 | 1. `/register` 접속<br>2. 기존 가입자와 동일한 이메일 입력<br>3. 폼 작성 완료<br>4. 회원가입 버튼 클릭 | email: `qa_test@example.com` (기존 가입) | 1. HTTP 409 응답, code: `EMAIL_DUPLICATED`<br>2. 이메일 필드 하단에 "이미 사용 중인 이메일입니다." 오류 메시지 표시<br>3. 페이지 이동 없음 | P1 |
| TC-AUTH-007 | 잘못된 이메일 형식 회원가입 | - | 1. `/register` 접속<br>2. 이메일 형식이 아닌 값 입력<br>3. 다른 필드로 포커스 이동 | email: `notanemail` | 1. 클라이언트 사이드 유효성 검사 즉시 실행<br>2. "올바른 이메일 형식을 입력해 주세요." 인라인 오류 표시<br>3. 회원가입 버튼 비활성화 | P1 |
| TC-AUTH-008 | 비밀번호 강도 미달 회원가입 | - | 1. `/register` 접속<br>2. 강도 미달 비밀번호 입력<br>3. 다른 필드로 포커스 이동 | password: `12345678` (특수문자, 영문 없음) | 1. "비밀번호는 8~20자, 영문·숫자·특수문자를 포함해야 합니다." 인라인 오류 표시 | P1 |
| TC-AUTH-009 | 비밀번호 확인 불일치 회원가입 | - | 1. `/register` 접속<br>2. 비밀번호 입력<br>3. 다른 값 비밀번호 확인 입력 | password: `Test1234!`<br>passwordConfirm: `Test5678!` | 1. "비밀번호가 일치하지 않습니다." 인라인 오류 표시<br>2. 회원가입 버튼 비활성화 | P1 |
| TC-AUTH-010 | 잘못된 비밀번호로 로그인 | 가입된 사용자 존재 | 1. `/login` 접속<br>2. 올바른 이메일 입력<br>3. 틀린 비밀번호 입력<br>4. 로그인 버튼 클릭 | email: `qa_test@example.com`<br>password: `WrongPass!1` | 1. HTTP 401 응답, code: `AUTH_FAILED`<br>2. 오류 토스트 "이메일 또는 비밀번호가 올바르지 않습니다." 표시<br>3. 계정 존재 여부 노출 없음 | P1 |
| TC-AUTH-011 | Refresh Token 만료 시 강제 로그아웃 | Refresh Token 만료 상태 | 1. 만료된 Access Token으로 API 호출<br>2. `/api/v1/auth/refresh` 자동 호출<br>3. Refresh Token도 만료 | 만료된 Refresh Token 쿠키 | 1. HTTP 401 응답, code: `REFRESH_TOKEN_EXPIRED`<br>2. `/login` 페이지로 강제 이동<br>3. 세션 만료 안내 메시지 표시 | P1 |
| TC-AUTH-012 | 비인증 상태로 보호 라우트 접근 | 미로그인 상태 | 1. 브라우저에서 `/map` 직접 접속 | - | 1. `/login` 페이지로 리다이렉트<br>2. 원래 접근하려 했던 URL 유지 또는 파라미터 전달 | P1 |

---

## 2. 장소 CRUD (PLACE)

### 2.1 정상 흐름

| TC-ID | 테스트 케이스명 | 전제조건 | 테스트 단계 | 입력 데이터 | 기대 결과 | 우선순위 |
|-------|--------------|---------|-----------|-----------|---------|---------|
| TC-PLACE-001 | 장소 등록 — 필수 필드만 | 로그인 상태, 카테고리 1개 이상 존재 | 1. `/places/new` 접속<br>2. 장소명 입력<br>3. 카테고리 선택<br>4. 방문일 선택 (오늘)<br>5. 지도에서 위치 핀 설정<br>6. 등록하기 버튼 클릭 | name: `테스트 장소`<br>categoryIds: [1]<br>visitedAt: `2026-05-09`<br>latitude: `37.5665`<br>longitude: `126.9780` | 1. HTTP 201 응답<br>2. 성공 토스트 "장소가 등록되었습니다." 표시<br>3. 등록된 장소 상세 페이지(`/places/{id}`)로 이동<br>4. 응답 `data.placeId` 값 반환 | P1 |
| TC-PLACE-002 | 장소 등록 — 선택 필드 포함 전체 필드 | 로그인 상태, 카테고리 존재 | 1. `/places/new` 접속<br>2. 모든 필드 입력 (사진 제외)<br>3. 등록하기 버튼 클릭 | name: `을지로 순대국`<br>categoryIds: [1, 5]<br>visitedAt: `2026-05-01`<br>latitude: `37.5665`<br>longitude: `126.9780`<br>address: `서울 중구 을지로 123`<br>memo: `국물이 진하다`<br>rating: `4`<br>tags: `["혼밥", "순대국"]` | 1. HTTP 201 응답<br>2. 응답 data에 입력한 모든 필드값 일치 확인<br>3. 상세 페이지에서 메모, 평점, 태그 모두 표시 | P1 |
| TC-PLACE-003 | 장소 상세 조회 | 등록된 장소 존재, 로그인 상태 | 1. `GET /api/v1/places/{placeId}` 호출 | 본인 소유 placeId | 1. HTTP 200 응답<br>2. `data.placeId`, `data.name`, `data.visitedAt`, `data.latitude`, `data.longitude` 포함<br>3. `data.categories`, `data.tags`, `data.photos` 배열 포함 | P1 |
| TC-PLACE-004 | 장소 수정 성공 | 등록된 장소 존재, 로그인 상태 | 1. `/places/{id}/edit` 접속<br>2. 기존 데이터가 폼에 자동 입력된 것 확인<br>3. 장소명 수정<br>4. 수정하기 버튼 클릭 | name: `수정된 장소명`<br>(나머지 필드 유지) | 1. HTTP 200 응답<br>2. 성공 토스트 "장소가 수정되었습니다." 표시<br>3. `/places/{id}` 상세 페이지로 이동<br>4. 상세 페이지에서 수정된 장소명 확인 | P1 |
| TC-PLACE-005 | 장소 삭제 — 소프트 딜리트 | 등록된 장소 존재, 로그인 상태 | 1. `/places/{id}` 상세 페이지 접속<br>2. 삭제 버튼 클릭<br>3. 삭제 확인 모달에서 삭제 클릭 | 본인 소유 placeId | 1. HTTP 200 응답<br>2. 성공 토스트 "장소가 삭제되었습니다." 표시<br>3. `/places` 목록 페이지로 이동<br>4. 목록에서 해당 장소 미표시 확인<br>5. DB에서 deleted_at 컬럼 값 설정 확인 (소프트 딜리트) | P1 |

### 2.2 예외 흐름

| TC-ID | 테스트 케이스명 | 전제조건 | 테스트 단계 | 입력 데이터 | 기대 결과 | 우선순위 |
|-------|--------------|---------|-----------|-----------|---------|---------|
| TC-PLACE-006 | 타인 장소 상세 조회 시도 | 사용자 A, B 각각 로그인 가능, A가 등록한 장소 존재 | 1. 사용자 B로 로그인<br>2. `GET /api/v1/places/{A의 placeId}` 호출 | A의 placeId | 1. HTTP 403 응답, code: `FORBIDDEN`<br>2. "접근 권한이 없습니다." 메시지 | P1 |
| TC-PLACE-007 | 타인 장소 수정 시도 | 사용자 A, B 각각 로그인 가능, A가 등록한 장소 존재 | 1. 사용자 B로 로그인<br>2. `PUT /api/v1/places/{A의 placeId}` 호출 | A의 placeId, 수정 데이터 | 1. HTTP 403 응답, code: `FORBIDDEN`<br>2. "본인의 장소만 수정할 수 있습니다." | P1 |
| TC-PLACE-008 | 타인 장소 삭제 시도 | 사용자 A, B 각각 로그인 가능, A가 등록한 장소 존재 | 1. 사용자 B로 로그인<br>2. `DELETE /api/v1/places/{A의 placeId}` 호출 | A의 placeId | 1. HTTP 403 응답, code: `FORBIDDEN` | P1 |
| TC-PLACE-009 | 미래 방문일 입력 | 로그인 상태 | 1. `/places/new` 접속<br>2. 방문일에 내일 날짜 입력 시도 | visitedAt: `2026-05-10` (내일) | 1. 클라이언트: 날짜 피커에서 미래 날짜 선택 불가 처리<br>2. API 직접 호출 시 HTTP 400 응답, code: `FUTURE_DATE`<br>3. "방문일은 오늘 이전 날짜를 선택해 주세요." 메시지 | P1 |
| TC-PLACE-010 | 존재하지 않는 카테고리 ID로 장소 등록 | 로그인 상태 | 1. `POST /api/v1/places` API 직접 호출 | categoryIds: [99999] (존재하지 않는 ID) | 1. HTTP 404 응답, code: `CATEGORY_NOT_FOUND`<br>2. "카테고리를 찾을 수 없습니다." 메시지 | P1 |
| TC-PLACE-011 | 존재하지 않는 장소 ID 조회 | 로그인 상태 | 1. `GET /api/v1/places/99999` 호출 | placeId: 99999 (미존재) | 1. HTTP 404 응답, code: `PLACE_NOT_FOUND`<br>2. "장소를 찾을 수 없습니다." 메시지 | P1 |
| TC-PLACE-012 | 장소명 빈 값으로 등록 시도 | 로그인 상태 | 1. `/places/new` 접속<br>2. 장소명 미입력<br>3. 다른 필수 필드 모두 입력<br>4. 등록하기 버튼 클릭 시도 | name: `` (빈 문자열) | 1. 클라이언트 유효성 검사 실패<br>2. "장소명을 입력해 주세요." 인라인 오류 표시<br>3. 등록하기 버튼 비활성화 | P1 |
| TC-PLACE-013 | 좌표 범위 초과 값으로 장소 등록 | 로그인 상태 | 1. `POST /api/v1/places` API 직접 호출 | latitude: `91.0`<br>longitude: `181.0` | 1. HTTP 400 응답, code: `INVALID_COORDINATE`<br>2. "유효하지 않은 위치 정보입니다." 메시지 | P2 |

---

## 3. 카테고리 (CATEGORY)

### 3.1 정상 흐름

| TC-ID | 테스트 케이스명 | 전제조건 | 테스트 단계 | 입력 데이터 | 기대 결과 | 우선순위 |
|-------|--------------|---------|-----------|-----------|---------|---------|
| TC-CAT-001 | 카테고리 목록 조회 | 로그인 상태, 기본 카테고리 8개 존재 | 1. `GET /api/v1/categories` 호출 | Authorization 헤더 | 1. HTTP 200 응답<br>2. `data.defaultCategories` 배열에 기본 카테고리 8개 포함<br>3. `data.userCategories` 배열 포함<br>4. `data.totalCount`, `data.limitCount: 20` 확인 | P1 |
| TC-CAT-002 | 사용자 카테고리 생성 성공 | 로그인 상태, 기존 카테고리 19개 이하 | 1. `/categories` 접속<br>2. 카테고리 추가 버튼 클릭<br>3. 이름, 색상, 아이콘 입력<br>4. 저장 클릭 | name: `산책코스`<br>color: `#4CAF50`<br>icon: `walk` | 1. HTTP 201 응답<br>2. 생성된 카테고리 목록에 표시<br>3. `data.isDefault: false` 확인<br>4. `data.placeCount: 0` 확인 | P2 |
| TC-CAT-003 | 사용자 카테고리 수정 성공 | 로그인 상태, 사용자 정의 카테고리 존재 | 1. `/categories` 접속<br>2. 수정 대상 카테고리의 수정 버튼 클릭<br>3. 이름 수정<br>4. 저장 클릭 | name: `수정된카테고리명`<br>color: `#FF5722` | 1. HTTP 200 응답<br>2. 목록에서 수정된 이름 확인<br>3. 해당 카테고리를 사용하는 장소에도 변경사항 반영 | P2 |
| TC-CAT-004 | 사용자 카테고리 삭제 성공 | 로그인 상태, 장소에 사용되지 않는 사용자 카테고리 존재 | 1. `/categories` 접속<br>2. 삭제 대상 카테고리의 삭제 버튼 클릭<br>3. 삭제 확인 | 삭제할 categoryId (placeCount: 0) | 1. HTTP 200 응답<br>2. 목록에서 해당 카테고리 삭제 확인<br>3. 카테고리 수(`totalCount`) 1 감소 | P2 |

### 3.2 예외 흐름

| TC-ID | 테스트 케이스명 | 전제조건 | 테스트 단계 | 입력 데이터 | 기대 결과 | 우선순위 |
|-------|--------------|---------|-----------|-----------|---------|---------|
| TC-CAT-005 | 기본 카테고리 수정 시도 (UI) | 로그인 상태 | 1. `/categories` 접속<br>2. 기본 카테고리 항목 확인 | - | 1. 기본 카테고리 행에 수정 버튼 미표시 또는 비활성화<br>2. [편집 불가] 레이블 표시 | P1 |
| TC-CAT-006 | 기본 카테고리 수정 시도 (API) | 로그인 상태 | 1. `PUT /api/v1/categories/{기본 카테고리 ID}` 직접 호출 | 기본 카테고리 ID | 1. HTTP 403 응답, code: `FORBIDDEN`<br>2. "기본 카테고리는 수정하거나 삭제할 수 없습니다." | P1 |
| TC-CAT-007 | 기본 카테고리 삭제 시도 (API) | 로그인 상태 | 1. `DELETE /api/v1/categories/{기본 카테고리 ID}` 직접 호출 | 기본 카테고리 ID | 1. HTTP 403 응답, code: `FORBIDDEN` | P1 |
| TC-CAT-008 | 카테고리 20개 초과 생성 시도 | 로그인 상태, 기본 8개 + 사용자 12개 = 총 20개 상태 | 1. `/categories` 접속<br>2. 카테고리 추가 버튼 클릭 시도 | - | 1. 카테고리 추가 버튼 비활성화 또는 안내 메시지 표시<br>2. API 직접 호출 시 HTTP 413, code: `CATEGORY_LIMIT_EXCEEDED`<br>3. "카테고리는 최대 20개까지 생성 가능합니다." | P1 |
| TC-CAT-009 | 중복 카테고리명 생성 시도 | 로그인 상태, `산책코스` 카테고리 이미 존재 | 1. 카테고리 추가 모달 열기<br>2. 기존과 동일한 이름 입력<br>3. 저장 클릭 | name: `산책코스` (중복) | 1. HTTP 409 응답, code: `CATEGORY_NAME_DUPLICATED`<br>2. "이미 사용 중인 카테고리 이름입니다." 오류 표시 | P2 |
| TC-CAT-010 | 장소에서 사용 중인 카테고리 삭제 시도 | 로그인 상태, 해당 카테고리에 속한 장소 1개 이상 존재 | 1. `/categories` 접속<br>2. placeCount > 0 인 카테고리의 삭제 버튼 클릭 | 사용 중인 categoryId | 1. HTTP 409 응답, code: `CATEGORY_IN_USE`<br>2. 안내 다이얼로그: "해당 카테고리에 등록된 장소가 있어 삭제할 수 없습니다." | P1 |

---

## 4. 통계 (STATS)

### 4.1 정상 흐름

| TC-ID | 테스트 케이스명 | 전제조건 | 테스트 단계 | 입력 데이터 | 기대 결과 | 우선순위 |
|-------|--------------|---------|-----------|-----------|---------|---------|
| TC-STAT-001 | 요약 통계 카드 조회 | 로그인 상태, 장소 1개 이상 등록 | 1. `/stats` 접속 | - | 1. HTTP 200 응답<br>2. 요약 카드 4개 표시 (총 방문 장소 수, 이번 달 방문 수, 총 카테고리 수, 최다 방문 카테고리)<br>3. `data.totalPlaces` 실제 등록 건수와 일치 | P2 |
| TC-STAT-002 | 월별 방문 통계 조회 | 로그인 상태, 최근 12개월 내 방문 장소 존재 | 1. `GET /api/v1/stats/monthly` 호출 | - | 1. HTTP 200 응답<br>2. 배열 반환 (최대 12개 항목)<br>3. 각 항목 `year`, `month`, `count` 필드 포함<br>4. 화면에서 막대 차트 렌더링 확인 | P2 |
| TC-STAT-003 | 카테고리별 분포 통계 조회 | 로그인 상태, 카테고리별 장소 존재 | 1. `GET /api/v1/stats/category` 호출 | - | 1. HTTP 200 응답<br>2. 각 항목 `categoryId`, `name`, `color`, `count`, `ratio` 포함<br>3. `ratio` 합계 100% 근사치 (부동소수점 오차 허용)<br>4. 화면에서 도넛 차트 렌더링 확인 | P2 |

### 4.2 경계값

| TC-ID | 테스트 케이스명 | 전제조건 | 테스트 단계 | 입력 데이터 | 기대 결과 | 우선순위 |
|-------|--------------|---------|-----------|-----------|---------|---------|
| TC-STAT-004 | 신규 사용자 — 데이터 없을 때 요약 통계 | 방금 가입하여 장소가 0개인 상태 | 1. `/stats` 접속 | - | 1. HTTP 200 응답<br>2. `data.totalPlaces: 0`, `data.thisMonthPlaces: 0`<br>3. `data.topCategory: null` 또는 빈 값<br>4. 차트 영역에 "데이터가 없습니다" 안내 문구 표시 | P2 |
| TC-STAT-005 | 신규 사용자 — 데이터 없을 때 월별 통계 | 방금 가입하여 장소가 0개인 상태 | 1. `GET /api/v1/stats/monthly` 호출 | - | 1. HTTP 200 응답<br>2. 빈 배열 `[]` 반환 (에러 아님)<br>3. 화면에서 "등록된 방문 기록이 없습니다" 안내 표시 | P2 |

---

## 5. 필터/검색 (SEARCH)

### 5.1 정상 흐름

| TC-ID | 테스트 케이스명 | 전제조건 | 테스트 단계 | 입력 데이터 | 기대 결과 | 우선순위 |
|-------|--------------|---------|-----------|-----------|---------|---------|
| TC-SEARCH-001 | 키워드로 장소명 검색 | 로그인 상태, "순대국"이 포함된 장소명 존재 | 1. `/places` 접속<br>2. 검색창에 키워드 입력 후 대기 | keyword: `순대국` | 1. 300ms debounce 후 API 재호출<br>2. 장소명에 "순대국" 포함된 결과만 표시<br>3. 결과 건수 올바르게 표시 | P1 |
| TC-SEARCH-002 | 카테고리 필터링 | 로그인 상태, 맛집 카테고리 장소 존재 | 1. `/places` 접속<br>2. 필터 패널에서 "맛집" 체크<br>3. 적용 클릭 | categoryIds: [맛집 categoryId] | 1. 맛집 카테고리 장소만 목록 표시<br>2. 다른 카테고리 장소 미표시 | P1 |
| TC-SEARCH-003 | 평점 필터링 — 4점 이상 | 로그인 상태, 다양한 평점 장소 존재 | 1. `/places` 접속<br>2. 평점 필터에서 "4점 이상" 선택<br>3. 적용 클릭 | minRating: 4 | 1. 평점 4 이상 장소만 표시<br>2. 평점 1~3 장소 미표시<br>3. 평점 미입력(null) 장소 미표시 | P1 |
| TC-SEARCH-004 | 방문일 범위 필터링 | 로그인 상태, 다양한 방문일 장소 존재 | 1. `/places` 접속<br>2. 방문일 시작일, 종료일 입력<br>3. 적용 클릭 | visitedFrom: `2026-01-01`<br>visitedTo: `2026-03-31` | 1. 2026년 1월~3월 사이 방문 장소만 표시<br>2. 범위 외 장소 미표시 | P1 |

### 5.2 경계값

| TC-ID | 테스트 케이스명 | 전제조건 | 테스트 단계 | 입력 데이터 | 기대 결과 | 우선순위 |
|-------|--------------|---------|-----------|-----------|---------|---------|
| TC-SEARCH-005 | 검색 결과 0건 | 로그인 상태 | 1. `/places` 접속<br>2. 결과가 없는 키워드 검색 | keyword: `존재하지않는장소명XYZ123` | 1. HTTP 200 응답, `data.page.totalElements: 0`<br>2. 목록 영역에 "등록된 장소가 없습니다." 안내 문구 표시<br>3. 오류 화면으로 전환 없음 | P1 |
| TC-SEARCH-006 | 페이지 크기 경계값 — size=1 | 로그인 상태, 장소 2개 이상 존재 | 1. `GET /api/v1/places?size=1&page=0` 호출 | size: 1, page: 0 | 1. HTTP 200 응답<br>2. `data.content` 배열 길이 1<br>3. `data.page.totalPages` 올바르게 계산됨<br>4. `data.page.last: false` (장소 2개 이상이므로) | P2 |
| TC-SEARCH-007 | 여러 필터 동시 적용 (복합 필터) | 로그인 상태, 다양한 장소 존재 | 1. `/places` 접속<br>2. 카테고리 + 방문일 범위 + 평점 동시 설정<br>3. 적용 클릭 | categoryIds: [1]<br>visitedFrom: `2026-01-01`<br>visitedTo: `2026-05-09`<br>minRating: 3 | 1. 세 조건 모두 AND로 적용된 결과만 표시<br>2. 쿼리 파라미터에 모든 필터 포함 확인<br>3. 결과 건수 정확성 확인 | P2 |

---

*문서 끝 - QA 팀 작성, 배포 전 전체 TC 통과 여부 확인 필수*
