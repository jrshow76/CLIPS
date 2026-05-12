# CREON Gateway 운영 스크립트 (Windows)

본 디렉토리의 스크립트는 **Windows 호스트**에서 게이트웨이를 자동으로 기동하기 위한 보조 도구다. 
Linux/Mac 개발 환경에서는 사용하지 않는다.

---

## 파일 목록

| 파일 | 용도 | 실행 시점 |
|---|---|---|
| `cpStartup-template.bat` | CREON Plus 자동 로그인 템플릿 (비밀 값은 환경변수) | start-gateway.ps1 에서 호출 |
| `start-gateway.ps1` | CREON Plus 로그인 + 게이트웨이 기동 + 헬스 확인 | 수동 또는 작업스케줄러 |
| `register-task.ps1` | Windows 작업스케줄러에 매일 08:00 자동 기동 등록 | 1회만 (관리자 PowerShell) |

---

## 사용 절차

### 1. 사전 준비

1. CREON Plus 설치 (대신증권 홈페이지).
2. 모의투자 신청 (대신증권 사이트 → 모의투자 메뉴 → 신청).
3. 모의투자 계좌 발급 확인.
4. 32-bit Python 3.11 + pywin32 설치.
5. 가상환경 생성 + `pip install -e .[windows]`.
6. `.env` 파일 설정 (`CREON_TRADE_ENV=SIM` 부터 시작).

### 2. CREON 자동 로그인 설정

```powershell
# 비밀 값을 시스템 환경변수로 설정 (관리자 PowerShell)
[Environment]::SetEnvironmentVariable("CREON_LOGIN_ID",  "your_id",         "Machine")
[Environment]::SetEnvironmentVariable("CREON_LOGIN_PW",  "your_password",   "Machine")
[Environment]::SetEnvironmentVariable("CREON_CERT_PW",   "your_cert_pw",    "Machine")

# 템플릿을 운영 파일로 복사
Copy-Item .\cpStartup-template.bat .\cpStartup.bat
```

> 보안: `cpStartup.bat` 는 `.gitignore` 에 포함되어야 한다. 비밀이 평문으로 들어가지 않도록 환경변수만 참조한다.

### 3. 수동 기동 (개발/점검)

```powershell
.\start-gateway.ps1                # 백그라운드 기동
.\start-gateway.ps1 -Foreground    # 콘솔 출력으로 기동 (디버깅)
.\start-gateway.ps1 -NoLogin       # CREON 로그인 생략 (이미 로그인 상태)
```

### 4. 작업스케줄러 등록 (운영)

```powershell
# 관리자 PowerShell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\register-task.ps1 -AlsoOnBoot
```

기본 트리거: 매일 08:00 (KST). 시간 변경:

```powershell
.\register-task.ps1 -TriggerTime "07:30"
```

### 5. 운영 확인

```powershell
# 작업 상태
Get-ScheduledTask -TaskName TradePilotCreonGateway | Select-Object State, LastRunTime, LastTaskResult

# 게이트웨이 응답
Invoke-RestMethod http://localhost:9100/healthz
Invoke-RestMethod http://localhost:9100/readyz
```

---

## 운영 체크포인트

- [ ] `CREON_TRADE_ENV=SIM` 으로 시작 (실거래 전환은 별도 절차)
- [ ] `.env` 파일이 관리자 전용 NTFS 권한으로 제한됨
- [ ] `cpStartup.bat` 가 `.gitignore` 에 포함됨
- [ ] Windows 절전 모드 OFF
- [ ] Windows 자동 업데이트 장중 비활성
- [ ] 안티바이러스에 CREON 프로세스 예외 등록
- [ ] 작업스케줄러 "최고 권한" 옵션 활성

---

## 트러블슈팅

| 증상 | 원인 | 대처 |
|---|---|---|
| `pywin32_unavailable` 로그 | 32-bit Python에 pywin32 미설치 | `pip install pywin32==306` |
| `/readyz` ok=false, com_connected=false | CREON Plus 로그인 안 됨 | CREON Plus GUI에서 수동 로그인 후 재기동 |
| `TradeInit 실패` | 비밀번호 미입력 / 잘못됨 | CREON GUI에서 매매 비밀번호 입력 |
| 자동 로그인 실패 | coStarter.exe 인자 변경됨 | 대신증권 공지 확인 + .bat 인자 갱신 |
| 게이트웨이 응답은 있는데 주문 거부 | SIM/REAL 계좌 접두사 불일치 | `.env` 의 `CREON_ACCOUNT_PREFIX_*` 확인 |
