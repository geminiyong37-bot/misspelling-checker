@echo off
setlocal

set SCRIPT_DIR=%~dp0
set STAGING=%SCRIPT_DIR%Output\_staging
set ISCC="C:\Program Files (x86)\Inno Setup 6\ISCC.exe"

echo [1/3] PyInstaller 빌드 중...
pyinstaller "%SCRIPT_DIR%build.spec" --noconfirm --distpath "%STAGING%"
if errorlevel 1 (
    echo PyInstaller 실패
    exit /b 1
)

echo [2/3] 설치 파일 생성 중...
%ISCC% "%SCRIPT_DIR%installer.iss"
if errorlevel 1 (
    echo Inno Setup 실패
    rmdir /s /q "%STAGING%"
    exit /b 1
)

echo [3/3] 임시 파일 정리 중...
rmdir /s /q "%STAGING%"

echo 완료: Output\AI_Word_Speller_Setup.exe
endlocal
