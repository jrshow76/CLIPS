@echo off
REM =============================================================================
REM 키움 OpenAPI+ 자동 로그인 템플릿
REM (CREON cpStartup-template.bat 와 동일 이름 규칙 — kiwoomStartup.bat 로 복사 후 사용)
REM
REM 본 파일은 비밀이 들어가지 않은 템플릿이다.
REM 운영 환경에서는 kiwoomStartup.bat 로 복사 후 환경변수에서 비밀을 주입해 사용한다.
REM
REM 사용 변수 (사전에 시스템 환경변수로 설정):
REM   KIWOOM_LOGIN_ID         : 키움증권 ID
REM   KIWOOM_LOGIN_PW         : 키움 로그인 비밀번호 (DPAPI 보호 권장)
REM   KIWOOM_CERT_PW          : 공인인증서 비밀번호 (DPAPI 보호 권장)
REM
REM 키움 OpenAPI+ 자동 로그인은 KOA Studio 의 자동로그인 도구를 사용하는 것이
REM 표준이며, 본 .bat 는 KOA Studio 실행/모의-실거래 환경 분리 트리거용.
REM
REM 보안 권고:
REM   - 평문 비밀을 .bat 파일에 직접 기록하지 말 것.
REM   - 본 .bat 는 관리자만 접근 가능한 폴더에 두고 NTFS ACL 로 제한.
REM   - Windows 작업 스케줄러 "최고 권한" + "이 계정으로 실행" 사용.
REM =============================================================================

setlocal

REM ---- 사용자 환경에 맞게 수정 ----
set KIWOOM_INSTALL_DIR=C:\OpenAPI
set KIWOOM_EXE=%KIWOOM_INSTALL_DIR%\opstarter.exe

if not exist "%KIWOOM_EXE%" (
    echo [ERROR] 키움 OpenAPI 자동시작 파일이 없습니다: %KIWOOM_EXE%
    exit /b 1
)

if "%KIWOOM_LOGIN_ID%"=="" (
    echo [ERROR] 환경변수 KIWOOM_LOGIN_ID 미설정
    exit /b 2
)
if "%KIWOOM_LOGIN_PW%"=="" (
    echo [ERROR] 환경변수 KIWOOM_LOGIN_PW 미설정
    exit /b 3
)
if "%KIWOOM_CERT_PW%"=="" (
    echo [ERROR] 환경변수 KIWOOM_CERT_PW 미설정
    exit /b 4
)

tasklist /FI "IMAGENAME eq khopenapi.exe" 2>NUL | find /I "khopenapi.exe" >NUL
if "%ERRORLEVEL%"=="0" (
    echo [INFO] 키움 OpenAPI 이미 실행 중
    exit /b 0
)

echo [INFO] 키움 자동 로그인 시도...
start "" "%KIWOOM_EXE%" /id:%KIWOOM_LOGIN_ID% /pw:%KIWOOM_LOGIN_PW% /pwcert:%KIWOOM_CERT_PW% /autostart

REM 로그인 완료 대기
timeout /t 30 /nobreak >NUL

echo [DONE] 키움 자동 로그인 요청 완료
endlocal
exit /b 0
