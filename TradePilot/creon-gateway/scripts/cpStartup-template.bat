@echo off
REM =============================================================================
REM CREON Plus 자동 로그인 템플릿
REM
REM 본 파일은 비밀이 들어가지 않은 템플릿이다.
REM 운영 환경에서는 cpStartup.bat 로 복사 후 환경변수에서 비밀을 주입해 사용한다.
REM
REM 사용 변수 (사전에 시스템 환경변수로 설정):
REM   CREON_LOGIN_ID         : 대신증권 ID
REM   CREON_LOGIN_PW         : 대신증권 로그인 비밀번호 (DPAPI 보호 권장)
REM   CREON_CERT_PW          : 공인인증서 비밀번호 (DPAPI 보호 권장)
REM
REM CREON 자동 로그인 인자 포맷 (대신증권 공식):
REM   coStarter.exe /prj:cp /id:[ID] /pwd:[PW] /pwdcert:[CERT_PW] /autostart
REM
REM 보안 권고:
REM   - 평문 비밀을 .bat 파일에 직접 기록하지 말 것.
REM   - 본 .bat 는 관리자만 접근 가능한 폴더에 두고 NTFS ACL 로 제한.
REM   - Windows 작업 스케줄러 "최고 권한" + "이 계정으로 실행" 사용.
REM =============================================================================

setlocal

REM ---- 사용자 환경에 맞게 수정 ----
set CREON_INSTALL_DIR=C:\CREON\STARTER
set CREON_EXE=%CREON_INSTALL_DIR%\coStarter.exe

if not exist "%CREON_EXE%" (
    echo [ERROR] CREON 자동시작 실행파일이 없습니다: %CREON_EXE%
    exit /b 1
)

if "%CREON_LOGIN_ID%"=="" (
    echo [ERROR] 환경변수 CREON_LOGIN_ID 미설정
    exit /b 2
)
if "%CREON_LOGIN_PW%"=="" (
    echo [ERROR] 환경변수 CREON_LOGIN_PW 미설정
    exit /b 3
)
if "%CREON_CERT_PW%"=="" (
    echo [ERROR] 환경변수 CREON_CERT_PW 미설정
    exit /b 4
)

REM 이미 실행 중인지 확인
tasklist /FI "IMAGENAME eq DwCpStart.exe" 2>NUL | find /I "DwCpStart.exe" >NUL
if "%ERRORLEVEL%"=="0" (
    echo [INFO] CREON Plus 이미 실행 중
    exit /b 0
)

echo [INFO] CREON Plus 자동 로그인 시도...
start "" "%CREON_EXE%" /prj:cp /id:%CREON_LOGIN_ID% /pwd:%CREON_LOGIN_PW% /pwdcert:%CREON_CERT_PW% /autostart

REM 로그인 완료 대기
timeout /t 30 /nobreak >NUL

echo [DONE] CREON Plus 자동 로그인 요청 완료
endlocal
exit /b 0
