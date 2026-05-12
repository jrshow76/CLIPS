# =============================================================================
# Windows 작업스케줄러 등록 스크립트
# - 매일 08:00 (KST) TradePilot CREON Gateway 자동 기동
# - 시스템 부팅 시에도 자동 시작 (옵션)
#
# 관리자 권한 PowerShell에서 실행:
#   Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
#   .\register-task.ps1
# =============================================================================

param(
    [string]$TaskName = "TradePilotCreonGateway",
    [string]$TriggerTime = "08:00",
    [string]$ScriptPath = "C:\tradepilot\creon-gateway\scripts\start-gateway.ps1",
    [string]$RunAsUser  = "$env:USERNAME",
    [switch]$AlsoOnBoot = $false
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $ScriptPath)) {
    Write-Error "[ERROR] 기동 스크립트가 존재하지 않습니다: $ScriptPath"
    exit 1
}

# 기존 태스크 제거
$existing = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($existing) {
    Write-Host "[INFO] 기존 태스크 제거: $TaskName"
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
}

# Action
$action = New-ScheduledTaskAction `
    -Execute "powershell.exe" `
    -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$ScriptPath`""

# Trigger
$triggers = @()
$triggers += New-ScheduledTaskTrigger -Daily -At $TriggerTime
if ($AlsoOnBoot) {
    $triggers += New-ScheduledTaskTrigger -AtStartup
}

# 설정 (절전 중에도 실행, 5분간 재시도)
$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 5) `
    -ExecutionTimeLimit (New-TimeSpan -Hours 12)

# Principal (최고 권한)
$principal = New-ScheduledTaskPrincipal `
    -UserId $RunAsUser `
    -LogonType Interactive `
    -RunLevel Highest

# 등록
Register-ScheduledTask `
    -TaskName $TaskName `
    -Description "TradePilot CREON Gateway 자동 기동 (매일 $TriggerTime)" `
    -Action $action `
    -Trigger $triggers `
    -Settings $settings `
    -Principal $principal | Out-Null

Write-Host "[OK] 작업스케줄러 등록 완료: $TaskName ($TriggerTime 매일)"
if ($AlsoOnBoot) {
    Write-Host "[OK] 부팅 시 자동 시작도 활성화됨"
}
Write-Host ""
Write-Host "확인:"
Write-Host "  Get-ScheduledTask -TaskName $TaskName | Select-Object State, LastRunTime, NextRunTime"
