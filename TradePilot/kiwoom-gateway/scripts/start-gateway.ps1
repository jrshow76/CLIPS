# =============================================================================
# TradePilot Kiwoom Gateway 자동 기동 스크립트 (PowerShell 5+)
# =============================================================================
# 동작 순서:
#   1. 키움 OpenAPI+ 자동 로그인 (KOA Studio / 자체 자동로그인 도구)
#   2. 키움 프로세스 기동 대기 (최대 60초)
#   3. 가상환경(32-bit Python) 활성화
#   4. uvicorn 으로 게이트웨이 기동 (포트 9101)
#   5. 헬스 확인 (/healthz, /readyz)
#
# 사용법:
#   .\start-gateway.ps1 [-Foreground] [-NoLogin]
# =============================================================================

param(
    [switch]$Foreground = $false,
    [switch]$NoLogin = $false
)

$ErrorActionPreference = "Stop"

# ---- 환경 설정 (사용자 환경에 맞게 수정) ----
$GATEWAY_HOME = "C:\tradepilot\kiwoom-gateway"
# 키움 OCX 는 32-bit Python 필요
$VENV_PATH    = "C:\tradepilot\.venv-x86\Scripts"
$KIWOOM_AUTOLOGIN_BAT = "$GATEWAY_HOME\scripts\kiwoomStartup.bat"   # 운영자 별도 작성
$GATEWAY_PORT = 9101
$HEALTH_URL   = "http://127.0.0.1:$GATEWAY_PORT/healthz"
$READY_URL    = "http://127.0.0.1:$GATEWAY_PORT/readyz"
$LOG_DIR      = "C:\tradepilot\logs"

# ---- 사전 점검 ----
if (-not (Test-Path $GATEWAY_HOME)) {
    Write-Error "[ERROR] 게이트웨이 디렉토리가 존재하지 않습니다: $GATEWAY_HOME"
    exit 1
}
if (-not (Test-Path "$VENV_PATH\python.exe")) {
    Write-Error "[ERROR] 32-bit Python 가상환경이 존재하지 않습니다: $VENV_PATH"
    exit 1
}
if (-not (Test-Path $LOG_DIR)) { New-Item -ItemType Directory -Path $LOG_DIR | Out-Null }

# ---- 1. 키움 OpenAPI+ 자동 로그인 ----
if (-not $NoLogin) {
    if (Test-Path $KIWOOM_AUTOLOGIN_BAT) {
        Write-Host "[INFO] 키움 자동 로그인 실행 중..."
        Start-Process -FilePath $KIWOOM_AUTOLOGIN_BAT -WindowStyle Hidden
    } else {
        Write-Warning "[WARN] kiwoomStartup.bat 가 없습니다. KOA Studio 자동로그인 또는 수동 로그인 필요."
    }
}

# ---- 2. 키움 프로세스 대기 ----
Write-Host "[INFO] 키움 OpenAPI 프로세스 대기..."
$timeout = 60
$start = Get-Date
$kwReady = $false
while ((Get-Date) - $start -lt [TimeSpan]::FromSeconds($timeout)) {
    $proc = Get-Process -Name "khopenapi" -ErrorAction SilentlyContinue
    if (-not $proc) {
        $proc = Get-Process -Name "opstarter" -ErrorAction SilentlyContinue
    }
    if ($proc) {
        $kwReady = $true
        Write-Host "[OK] 키움 OpenAPI 프로세스 감지 (PID=$($proc.Id))"
        break
    }
    Start-Sleep -Seconds 2
}
if (-not $kwReady) {
    Write-Warning "[WARN] 키움 프로세스 미감지. mock 모드로 동작할 수 있습니다."
}

# ---- 3. 게이트웨이 기동 ----
$logFile = Join-Path $LOG_DIR "kiwoom_gateway_$(Get-Date -Format yyyyMMdd).log"
Write-Host "[INFO] 키움 게이트웨이 기동 ($logFile)..."

$pythonExe = Join-Path $VENV_PATH "python.exe"
$args = @(
    "-m", "uvicorn",
    "kiwoom_gateway.main:app",
    "--host", "0.0.0.0",
    "--port", "$GATEWAY_PORT"
)

Push-Location $GATEWAY_HOME
try {
    if ($Foreground) {
        & $pythonExe @args 2>&1 | Tee-Object -FilePath $logFile -Append
    } else {
        $proc = Start-Process -FilePath $pythonExe -ArgumentList $args `
            -WorkingDirectory $GATEWAY_HOME `
            -RedirectStandardOutput $logFile `
            -RedirectStandardError "$logFile.err" `
            -WindowStyle Hidden -PassThru
        Write-Host "[OK] 게이트웨이 PID=$($proc.Id)"
    }
} finally {
    Pop-Location
}

# ---- 4. 헬스 확인 ----
Write-Host "[INFO] 헬스 확인 중..."
$healthOk = $false
for ($i = 0; $i -lt 30; $i++) {
    Start-Sleep -Seconds 1
    try {
        $resp = Invoke-RestMethod -Uri $HEALTH_URL -TimeoutSec 2
        if ($resp.ok) {
            $healthOk = $true
            break
        }
    } catch {
        # 아직 기동 중
    }
}

if ($healthOk) {
    Write-Host "[OK] /healthz 응답 정상"
    try {
        $ready = Invoke-RestMethod -Uri $READY_URL -TimeoutSec 5
        Write-Host "[INFO] /readyz : connected=$($ready.connected) account_loaded=$($ready.account_loaded) trade_env=$($ready.trade_env)"
    } catch {
        Write-Warning "[WARN] /readyz 호출 실패: $_"
    }
} else {
    Write-Error "[ERROR] 30초 내에 게이트웨이 헬스 응답 없음. 로그: $logFile"
    exit 2
}

Write-Host "[DONE] 키움 게이트웨이 기동 완료. trade_env=$($resp.trade_env)"
