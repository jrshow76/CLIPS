# TradePilot PWA 가이드

> 문서 ID: 51_PWA_GUIDE
> 버전: v1.0
> 작성자: FrontendSenior
> 최종 수정일: 2026-05-14
> 관련 문서: `13_api_requirements.md` §14(알림), `22_frontend_structure.md`, `41_screen_inventory.md`(모바일 viewport)

본 문서는 TradePilot 의 PWA(Progressive Web App) 기능 — **홈 화면 설치, 오프라인 셸, Web Push 알림** — 구현 명세와 운영 가이드를 정리한다.

---

## 1. 개요

| 항목 | 내용 |
|---|---|
| 매니페스트 | `frontend/public/manifest.webmanifest` |
| Service Worker | `frontend/public/sw.js` (scope `/`) |
| 오프라인 fallback | `frontend/public/offline.html` |
| 등록 진입점 | `frontend/src/providers/PWAProvider.tsx` |
| 클라이언트 모듈 | `frontend/src/lib/pwa/` |
| UI 컴포넌트 | `frontend/src/components/pwa/` |
| 백엔드 채널 | `backend/app/integrations/notifications/webpush/` |
| API | `POST/DELETE /api/v1/notifications/push/*` |
| DB | `tp_user.push_subscriptions` (마이그레이션 2026_05) |

---

## 2. 설치 가이드 (사용자)

### 2.1 Android Chrome / Edge / Samsung Internet

1. TradePilot 웹앱을 방문한다 (https 필수).
2. 주소창 옆 메뉴(⋮) → **앱 설치** 를 선택하거나, 화면 하단 **앱 설치 안내 배너** 의 “지금 설치” 를 누른다.
3. 설치 후 홈 화면 아이콘에서 standalone 모드로 실행된다.

### 2.2 iOS Safari (16.4 이상 권장)

1. Safari 로 TradePilot 웹앱을 방문한다 (Chrome iOS 는 webview 라 미지원).
2. 하단 **공유** 아이콘(⬆️) 을 탭한다.
3. **홈 화면에 추가** 를 선택한다.
4. 홈 화면에서 standalone 으로 실행하면 **Web Push 가 활성화** 된다.
   - **iOS 16.4 미만**: 홈 추가는 가능하지만 푸시 알림은 동작하지 않음 → 이메일/SMS 채널로 자동 대체 발송.
   - 일반 Safari 탭에서는 Notification API 권한 자체가 default 로 고정될 수 있어 푸시 미지원.

### 2.3 데스크톱 Chrome / Edge

- 주소창 오른쪽 “설치” 아이콘 또는 “앱 설치” 버튼을 누른다.
- Windows / macOS / Linux 에서 standalone 윈도우로 실행된다.

---

## 3. Service Worker 캐시 전략

| 자원 종류 | 전략 | 보관 기간 | 참고 |
|---|---|---|---|
| 앱 셸 (HTML, `/`, `/dashboard`) | NetworkFirst → `offline.html` fallback | 무제한 (수명 = SW_VERSION) | `install` 시 precache |
| `/_next/static/*` | CacheFirst | 무제한 (불변 자산) | 빌드 해시 변경 시 새 캐시 키 |
| `/icons/*`, 이미지 | CacheFirst | 7일 (TTL) | sw-cached-at 헤더로 만료 판정 |
| `/api/v1/...` GET | StaleWhileRevalidate | 5분 | `/auth/`, `/notifications/push/` 는 제외 |
| 네비게이션 (text/html) | NetworkFirst → offline.html | - | 오프라인 시 캐시 또는 fallback |

**캐시 버전**: `sw.js` 상단 `SW_VERSION` 상수. 빌드/배포 시 갱신해 구 캐시를 일괄 폐기한다.

**수동 캐시 정리**: 설정 → 앱/푸시 → **캐시 비우기** 버튼. 내부적으로 `clients.controller.postMessage({ type: 'CLEAR_CACHES' })` 메시지로 SW 에 위임.

---

## 4. Web Push 흐름

### 4.1 시퀀스

```
[Client]                              [Backend]              [Push Service]
   |                                       |                        |
   |--- GET /push/vapid-public-key ------->|                        |
   |<------- public_key ---------------------|                       |
   |                                       |                        |
   |- Notification.requestPermission()     |                        |
   |- pushManager.subscribe(applicationServerKey)                   |
   |   (브라우저가 Push Service 에 endpoint 등록)                  |
   |                                       |                        |
   |--- POST /push/subscribe ------------->|                        |
   |   { endpoint, p256dh_key, auth_key }  |--- INSERT push_subscriptions
   |                                       |                        |
   |  (... 시그널 발생 ...)                  |                        |
   |                                       |--- WebPushChannel.send -->|
   |                                       |    (VAPID 서명 + 페이로드 암호화)
   |<------------------------ push event ----------------------------|
   |- self.addEventListener('push', e => showNotification(...))      |
   |- 사용자 클릭 → notificationclick → /chart/{code} 라우팅          |
```

### 4.2 VAPID 키 셋업

```bash
# 키 생성 (1회)
python scripts/generate_vapid_keys.py > .env.vapid

# .env 에 복사
VAPID_PUBLIC_KEY=BPub...
VAPID_PRIVATE_KEY=prv...
VAPID_SUBJECT=mailto:admin@tradepilot.example.com
```

- 운영/스테이징/개발 환경별로 키쌍을 분리한다.
- `VAPID_PRIVATE_KEY` 는 **시크릿 매니저** (AWS Secrets Manager, GCP Secret Manager, HashiCorp Vault) 에 저장 권장.
- 키 회전: 1년 주기 또는 누출 의심 시 즉시. 회전 시 모든 활성 구독이 무효화되므로 **사전 공지 + 재구독 안내** 필요.

### 4.3 페이로드 포맷 (서버 → SW)

```json
{
  "title": "[BUY] 삼성전자(005930) 매매 시그널",
  "body": "RSI Bullish — 신뢰도 HIGH, 기준가 71,000원",
  "severity": "INFO",
  "event_type": "SIGNAL",
  "notification_id": 12345,
  "url": "/chart/005930",
  "payload": { "stock_code": "005930", "action": "BUY" }
}
```

SW 는 `showNotification(title, options)` 에 다음을 매핑한다.

| 페이로드 | NotificationOptions |
|---|---|
| `title` | 제목 |
| `body` | 본문 |
| `event_type` | `tag` (동일 종류 알림 그룹) |
| `severity=CRITICAL` | `requireInteraction=true`, `renotify=true` |
| `url` | `data.url` → click 시 라우팅 |

### 4.4 알림 클릭 라우팅

| event_type | URL |
|---|---|
| SIGNAL | `/chart/{stock_code}` |
| ORDER_FILLED | `/auto-trading/orders` |
| KILL_SWITCH | `/auto-trading` |
| SECURITY | `/settings` |
| DAILY_REPORT | `/report` |
| 그 외 | `/notifications` |

이미 앱 윈도우가 열려 있으면 `client.postMessage({ type: 'NAVIGATE', url })` → `PWAProvider` 가 Next 라우터 `router.push(url)` 호출.

---

## 5. iOS PWA 제한 사항

| 제한 | 영향 | 대응 |
|---|---|---|
| iOS 16.3 이하 Web Push 미지원 | 푸시 수신 불가 | 이메일/SMS 채널 자동 폴백 (`notification_service.dispatch`) |
| Safari 탭에서는 PushManager 미지원 | 권한 default 고정 | 홈 화면 추가 후 standalone 모드 안내 |
| `beforeinstallprompt` 미발생 | "지금 설치" 버튼 동작 X | 공유 → 홈 화면 추가 텍스트 가이드 |
| `apple-touch-icon` 만 인식 | 매니페스트 maskable 무시 | `layout.tsx` 에 별도 `apple-touch-icon` PNG 지정 |
| SW 캐시 50MB 한도 (대략) | 대용량 자산 캐시 불가 | 정적 자산만 캐시, 이미지는 7일 TTL |
| 브라우저 종료 시 SW 강제 종료 가능 | 백그라운드 동기화 제한 | 백엔드 측 큐잉(WEBPUSH_TTL_SECONDS) 활용 |

---

## 6. 보안

### 6.1 HTTPS 강제

- SW 등록 / Push API / Notification API 는 모두 **HTTPS** 또는 `localhost` 에서만 동작.
- 운영 환경: TLS 종단 (Nginx / CloudFront / 클라우드 LB) 필수.

### 6.2 시크릿 관리

- `VAPID_PRIVATE_KEY` 는 절대 클라이언트에 노출 금지.
  - GET `/notifications/push/vapid-public-key` 는 **공개키만** 반환.
- `.env.example` 는 빈 문자열 placeholder 만 유지. 실제 키는 시크릿 매니저 또는 운영 환경변수.
- `gitleaks` pre-commit hook 이 VAPID_PRIVATE_KEY 패턴(43자 base64url) 누출을 차단.

### 6.3 구독 데이터 보호

- `tp_user.push_subscriptions` 에 저장되는 `p256dh_key` / `auth_key` 는 RFC 8291 상 **공개 정보** (Push Service 가 발급한 클라이언트 키). 추가 암호화 불필요.
- `endpoint` URL 자체가 추적 식별자가 되므로 DB 권한은 애플리케이션 롤만 접근 (관리자/감사 롤은 read-only 도 endpoint hash 만 노출 권장).
- 회원 탈퇴 시 `ON DELETE CASCADE` 로 동시 삭제.
- 410 Gone / 404 응답 시 **즉시** 행 삭제 (orphan 방지).

### 6.4 CSRF / 인증

- 모든 push API 는 JWT Bearer 인증 필수.
- `POST /push/subscribe` 의 endpoint 는 사용자별 UNIQUE → 다른 사용자가 동일 endpoint 를 가로채려는 시도는 UNIQUE 제약으로 차단.

---

## 7. 운영

### 7.1 모니터링 지표

- `notifications.webpush.sent` (성공)
- `notifications.webpush.failed` (실패 — error_code 별 라벨)
- `notifications.webpush.expired_cleaned` (410 자동 정리 건수)
- `push_subscriptions.active_count` (활성 구독 총량)

### 7.2 정리 잡

- `last_used_at` 이 90일 이상 지난 구독은 비활성화 (정리 잡, 후속 구현).
- `expires_at` 도래 시 즉시 삭제.

### 7.3 장애 대응

| 증상 | 원인 후보 | 대응 |
|---|---|---|
| SW 등록 실패 | HTTPS 미적용 / scope 충돌 | TLS 인증서 / scope 확인 |
| 알림 미수신 | VAPID 키 mismatch / endpoint 만료 | 사용자에게 재구독 요청 (설정 토글 OFF/ON) |
| 410 Gone 대량 발생 | 키 회전 직후 / 브라우저 정책 변경 | 자동 정리 동작 확인, 알림 발송 큐 백오프 |
| iOS 푸시만 미수신 | 16.3 이하 / 비 standalone | 이메일 폴백 동작 확인 |

---

## 8. 개발자 체크리스트

- [ ] `scripts/generate_vapid_keys.py` 실행 후 `.env` 갱신
- [ ] `database/migrations/2026_05_add_push_subscriptions.sql` 적용
- [ ] `pywebpush` 의존성 설치 (`pip install -e backend/`)
- [ ] `NEXT_PUBLIC_ENABLE_SW=true` (개발 시 SW 활성화 원할 때) 또는 production 빌드
- [ ] iOS 실기기 + 안드로이드 실기기에서 홈 화면 추가 → 푸시 수신 검증
- [ ] Lighthouse PWA 감사: Installable / Service Worker / HTTPS PASS
- [ ] 알림 클릭 → 정상 페이지 라우팅 (SIGNAL → `/chart/{code}`)
- [ ] 캐시 정리 / 새 버전 적용 토글 동작 확인
