# =============================================================================
# Windows 작업스케줄러 등록 스크립트 (Kiwoom Gateway)
# - 매일 08:00 (KST) TradePilot Kiwoom Gateway 자동 기동
# - 시스템 부팅 시에도 자동 시작 (옵션)
#
# 관리자 권한 PowerShell에서 실행:
#   Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
#   .\register-task.ps1
# =============================================================================

param(
    [string]$TaskName = "TradePilotKiwoomGateway",
    [string]$TriggerTime = "08:00",
    [string]$ScriptPath = "C:\tradepilot\kiwoom-gateway\scripts\start-gateway.ps1",
    [string]$RunAsUser  = "$env:USERNAME",
    [switch]$AlsoOnBoot = $false
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $ScriptPath)) {
    Write-Error "[ERROR] 기동 스크립트가 존재하지 않습니다: $ScriptPath"
    exit 1
}

$existing = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($existing) {
    Write-Host "[INFO] 기존 태스크 제거: $TaskName"
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
}

$action = New-ScheduledTaskAction `
    -Execute "powershell.exe" `
    -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$ScriptPath`""

$triggers = @()
$triggers += New-ScheduledTaskTrigger -Daily -At $TriggerTime
if ($AlsoOnBoot) {
    $triggers += New-ScheduledTaskTrigger -AtStartup
}

$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 5) `
    -ExecutionTimeLimit (New-TimeSpan -Hours 12)

$principal = New-ScheduledTaskPrincipal `
    -UserId $RunAsUser `
    -LogonType Interactive `
    -RunLevel Highest

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $action `
    -Trigger $triggers `
    -Settings $settings `
    -Principal $principal | Out-Null

Write-Host "[OK] 작업 등록 완료: $TaskName (매일 $TriggerTime)"
if ($AlsoOnBoot) { Write-Host "[INFO] 부팅 시 자동 시작 트리거도 등록되었습니다." }
