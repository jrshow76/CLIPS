# 알림 채널 가이드 (46_notification_guide)

> 문서 ID: 46_NOTIFICATION_GUIDE
> 버전: v1.0
> 작성자: BackendDev
> 최초 작성일: 2026-05-14
> 검토자: DevLead, BackendSenior, QA, PM

본 문서는 TradePilot 의 다중 알림 채널(이메일/카카오 알림톡/SMS/인앱) 운영 및
개발 가이드를 제공한다.

## 1. 채널 개요

| 채널 | 어댑터 | 용도 | 비용 | 옵트인 필요 |
|---|---|---|---|---|
| INAPP | `app.services.notification_service.NotificationService.notify_user` | 웹 알림센터, 실시간 토스트 | 무료 | 기본 활성 |
| EMAIL | `integrations.notifications.email.smtp_channel.SmtpEmailChannel` | 시그널/체결/리포트/보안 | 무료(SMTP 발신비) | 기본 활성, 가입 시 이메일 인증 |
| KAKAO | `integrations.notifications.kakao.biz_message_channel.KakaoBizMessageChannel` | Kill Switch/보안 즉시 알림 | 건당 과금 | 필수 (`/settings/notifications/kakao/optin`) |
| SMS | `integrations.notifications.sms.channel.SmsChannel` | 카카오 실패 시 fallback, 백업 | 건당 과금 | 휴대폰 번호 등록 |

## 2. 알림 종류 → 기본 채널 매핑

`NotificationService._DEFAULT_EVENT_CHANNELS` 에 정의되어 있으며, 사용자 설정으로 일부 비활성화 가능.

| 이벤트 종류 | 기본 채널 | 비고 |
|---|---|---|
| `SIGNAL` (매매 시그널) | INAPP + EMAIL | 알림톡은 사용자 옵트인 시 추가 |
| `ORDER_FILLED` (체결) | INAPP + EMAIL | 정보성 |
| `KILL_SWITCH` (비상정지) | INAPP + EMAIL + KAKAO + SMS | CRITICAL - 모든 채널 강제 |
| `SECURITY` (보안 이벤트) | INAPP + EMAIL + KAKAO | 리프레시 토큰 재사용/로그인 실패 등 |
| `DAILY_REPORT` (일일 리포트) | EMAIL + KAKAO | 매일 18:00 KST Celery Beat |
| `SYSTEM` (시스템) | INAPP | 관리자 알림 등 |

## 3. 채널별 사전 준비

### 3.1 이메일 (SMTP)

운영 진입 전 도메인 측에서 SPF/DKIM/DMARC 레코드를 등록한다.

```
# DNS TXT 레코드 예시 (도메인: tradepilot.example.com)
@           IN  TXT  "v=spf1 include:_spf.google.com -all"
default._domainkey  IN  TXT  "v=DKIM1; k=rsa; p=MIIBIj..."
_dmarc      IN  TXT  "v=DMARC1; p=quarantine; rua=mailto:dmarc@tradepilot.example.com"
```

환경 변수 (`.env`):
```
SMTP_HOST=smtp.gmail.com         # 또는 자체 메일 서버
SMTP_PORT=587                    # 465 (SSL) / 587 (STARTTLS)
SMTP_USER=noreply@tradepilot.example.com
SMTP_PASSWORD=<강한 시크릿>
SMTP_FROM=TradePilot <noreply@tradepilot.example.com>
SMTP_FROM_EMAIL=noreply@tradepilot.example.com
SMTP_USE_TLS=true
```

### 3.2 카카오 알림톡 (NHN Cloud Notification Service)

운영 절차:
1. 카카오비즈 채널 생성 + 운영자 인증
2. NHN Cloud 콘솔에서 알림톡 프로젝트 생성
3. 발신 프로필(SenderKey) 등록
4. 템플릿 등록 (`integrations/notifications/kakao/templates_registry.py` 의 5종)
   - SIGNAL_ALERT / EXECUTION_ALERT / KILL_SWITCH / SECURITY_ALERT / DAILY_REPORT
5. 카카오 비즈 콘솔에서 템플릿 승인 대기 (영업일 2~3일)
6. 승인 완료 후 `template_id` 를 `templates_registry.py` 의 실제 값으로 교체

환경 변수:
```
KAKAO_BIZ_API_URL=https://api-alimtalk.cloud.toast.com/alimtalk/v2.3
KAKAO_BIZ_APP_KEY=<NHN Cloud AppKey>
KAKAO_BIZ_SECRET=<NHN Cloud SecretKey>
KAKAO_BIZ_SENDER_KEY=<발신 프로필 SenderKey>
KAKAO_BIZ_USE_OAUTH=false
```

### 3.3 SMS

#### 옵션 A: NHN Cloud SMS (기본)
1. NHN Cloud 콘솔에서 SMS 프로젝트 생성
2. 발신번호 사전 등록(통신사 인증, 1~3 영업일)
3. AppKey/SecretKey 발급

```
SMS_PROVIDER=nhn_cloud
SMS_FROM_NUMBER=0212345678      # 사전 등록된 번호
SMS_NHN_APP_KEY=...
SMS_NHN_SECRET=...
```

#### 옵션 B: AWS SNS
1. IAM 사용자 생성 + SNS 권한 부여
2. (KR) Spend limit 상향 신청 필요

```
SMS_PROVIDER=aws_sns
SMS_AWS_ACCESS_KEY=...
SMS_AWS_SECRET_KEY=...
SMS_AWS_REGION=ap-northeast-2
```

> 추가 의존성: `boto3` (선택 설치). 미설치 시 SMS 어댑터는 `BOTO3_MISSING` 으로 응답.

## 4. 사용자 옵트인 절차

1. 사용자가 회원가입 후 `POST /api/v1/settings/notifications/email/verify` 로 이메일 인증 OTP 발급
2. 메일로 받은 코드를 `POST /api/v1/settings/notifications/email/verify` (확인 모드)로 입력 → 검증 완료
3. 카카오 알림톡 사용 시: `POST /api/v1/settings/notifications/kakao/optin` 으로 전화번호 + 수신 동의 등록
4. 채널 토글: `PUT /api/v1/settings/notifications` 에서 inapp/email/kakao/sms on-off

### 4.1 약관/동의 보관

카카오 비즈메시지는 정보통신망법상 사전 수신 동의가 필수다. 옵트인 시 다음을 감사 로그에 기록 권장:
- 동의 시각 (UTC)
- IP 주소
- User-Agent
- 동의 약관 버전

## 5. 야간 조용 모드 (Quiet Hours)

`NotificationService._is_quiet_hours()` 에서 결정. v1 은 글로벌 기본 비활성이며,
후속 마이그레이션으로 `notification_channels` 에 `quiet_start/end` 컬럼을 추가하면 활성화된다.

정책:
- 22:00 ~ 08:00 KST: `priority='HIGH'` 이외 모든 외부 채널 발송 무음
- INAPP 는 항상 발송 (DB 저장 + WebSocket)
- `KILL_SWITCH`/`SECURITY` 는 무음 정책 무시(즉시 발송)

## 6. 실패 시 Fallback

```
INAPP (DB 저장 + WS push)     # 항상 시도
  ↓
EMAIL (SMTP)
  ↓
KAKAO (알림톡)
  ↓ 실패 시 (KAKAO_TIMEOUT / HTTP_4xx / TEMPLATE_REJECTED)
SMS (백업 채널)
```

- 채널별 1회 호출 후 실패 시 즉시 fallback (긴 재시도는 회피)
- 모든 채널 발송 결과는 `notifications.payload.delivery[]` JSONB 에 누적 저장
- Celery 태스크 레벨에서 추가 재시도(max 3회, 지수 백오프 30/120/300초)

## 7. 트리거 통합 위치

| 트리거 이벤트 | 호출 위치 | 호출 메서드 |
|---|---|---|
| 매매 시그널 생성 | `services/signal_service.py::persist_signal` | `send_signal_alert` |
| 주문 체결 | `services/order_service.py::create` (status==FILLED) | `send_execution_alert` |
| Kill Switch 발동 | `services/kill_switch_service.py::trigger` | `send_kill_switch_alert` |
| Refresh replay 탐지 | `services/auth_service.py::refresh` | `send_security_alert` |
| 일일 리포트 | `workers/tasks/notification_tasks.py::daily_report_all` (Beat 18:00) | `send_daily_report` |

알림 발송 실패는 절대 원래 흐름(체결/시그널/Kill Switch)을 차단하지 않으며,
WARN 로그만 남긴다.

## 8. 템플릿 관리

### 8.1 이메일 (jinja2)

위치: `backend/app/integrations/notifications/email/templates/`

- `_base.html`: 공통 레이아웃 (반응형, 한글 폰트)
- `signal_alert.html` / `execution_alert.html` / `kill_switch.html`
- `daily_report.html` / `security_alert.html` / `welcome.html`

자동 escape 활성화되어 있어 사용자 입력이 본문에 포함되어도 XSS 위험 없음.

### 8.2 카카오 알림톡

위치: `backend/app/integrations/notifications/kakao/templates_registry.py`

- 변수는 `#{key}` 형식
- 콘솔 등록 시 `sample_content` 와 정확히 일치해야 승인됨
- 변경 시: 콘솔 재신청 → 승인 → `template_id` 갱신

## 9. 관측/모니터링

- 로그 이벤트 이름:
  - `email_sent` / `email_send_failed`
  - `kakao_sent` / `kakao_send_http_error`
  - `sms_sent_nhn` / `sms_sent_aws`
  - `dispatch_failed` / `kakao_fallback_to_sms`
- Prometheus 메트릭(후속): `notifications_sent_total{channel, event_type, ok}` 카운터
- `notifications.payload.delivery[]` 에서 사용자별 발송 이력 추적

## 10. 운영 체크리스트

배포 전:
- [ ] SMTP 발신 도메인 SPF/DKIM/DMARC 검증 (mail-tester.com)
- [ ] 카카오 알림톡 5종 템플릿 콘솔 승인 완료
- [ ] `templates_registry.py` 의 template_id 가 실제 값으로 갱신됨
- [ ] SMS 발신번호 사전 등록 완료
- [ ] `.env` 의 채널 시크릿 32자 이상 + 엔트로피 16 이상 (운영은 fail-fast)
- [ ] 테스트 사용자 1명으로 4채널 전수 테스트 (`/settings/notifications/test`)
- [ ] Celery Beat 에 `notifications-daily-report` 활성 확인
- [ ] 동의 약관/개인정보 처리방침 카카오 알림톡 항목 포함

## 11. 변경 이력

| 버전 | 일자 | 작성자 | 내용 |
|---|---|---|---|
| v1.0 | 2026-05-14 | BackendDev | 최초 작성. 이메일/카카오 알림톡/SMS 3채널 어댑터 + NotificationService dispatch + Celery beat + 5개 이벤트 트리거 통합. |
