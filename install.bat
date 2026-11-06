@echo off
setlocal enabledelayedexpansion

echo ============================================================
echo  GITHUB AUTO UPLOADER PRO - WINDOWS INSTALLER
echo ============================================================

set "INSTALL_DIR=%USERPROFILE%\.Github-Auto-Uploader"
set "BIN_DIR=%USERPROFILE%\.local\bin"
set "MYENV_DIR=%USERPROFILE%\myenv"

:: 1. Check Python
where python >nul 2>&1
if %errorlevel% neq 0 (
    where py >nul 2>&1
    if %errorlevel% neq 0 (
        echo [ERROR] Python 3 is not installed or not in PATH.
        echo Please install Python from https://www.python.org/downloads/
        echo Make sure to check "Add Python to PATH" during installation.
        pause
        exit /b 1
    ) else (
        set "BASE_PY=py -3"
    )
) else (
    set "BASE_PY=python"
)

echo [✓] Using Python: %BASE_PY%

:: 2. Setup ~/.Github-Auto-Uploader
if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"
if not exist "%BIN_DIR%" mkdir "%BIN_DIR%"

echo ==> Copying files into %INSTALL_DIR%...
set "SCRIPT_SRC=%~dp0"
if exist "%SCRIPT_SRC%github_uploader.py" (
    xcopy /y /e /i "%SCRIPT_SRC%github_auto_uploader" "%INSTALL_DIR%\github_auto_uploader" >nul
    copy /y "%SCRIPT_SRC%github_uploader.py" "%INSTALL_DIR%\" >nul
    copy /y "%SCRIPT_SRC%requirements.txt" "%INSTALL_DIR%\" >nul
    copy /y "%SCRIPT_SRC%README.md" "%INSTALL_DIR%\" >nul 2>nul
    if exist "%SCRIPT_SRC%config.json" if not exist "%INSTALL_DIR%\config.json" (
        copy /y "%SCRIPT_SRC%config.json" "%INSTALL_DIR%\" >nul
    )
) else (
    echo ==> Downloading from GitHub...
    git clone --depth 1 https://github.com/Mr-Risov/GitHub-Auto-Uploader.git "%TEMP%\gh_clone"
    xcopy /y /e /i "%TEMP%\gh_clone\github_auto_uploader" "%INSTALL_DIR%\github_auto_uploader" >nul
    copy /y "%TEMP%\gh_clone\github_uploader.py" "%INSTALL_DIR%\" >nul
    copy /y "%TEMP%\gh_clone\requirements.txt" "%INSTALL_DIR%\" >nul
    copy /y "%TEMP%\gh_clone\README.md" "%INSTALL_DIR%\" >nul 2>nul
    rmdir /s /q "%TEMP%\gh_clone"
)

:: 3. Detect or Auto-Create %USERPROFILE%\myenv
echo ==> Detecting virtual environment...
if exist "%MYENV_DIR%\Scripts\python.exe" (
    echo [✓] Found existing virtual environment: %MYENV_DIR%
) else (
    echo ==> Creating virtual environment at %MYENV_DIR%...
    %BASE_PY% -m venv "%MYENV_DIR%"
)

set "VENV_PY=%MYENV_DIR%\Scripts\python.exe"
if not exist "%VENV_PY%" (
    echo [!] Virtualenv creation failed. Falling back to base Python.
    set "VENV_PY=%BASE_PY%"
) else (
    echo %MYENV_DIR% > "%INSTALL_DIR%\.venv_path"
    echo [✓] Virtual environment ready: %MYENV_DIR%
)

:: 4. Install Requirements
echo ==> Upgrading pip and installing requirements...
"%VENV_PY%" -m pip install --upgrade pip setuptools wheel --quiet >nul 2>&1
"%VENV_PY%" -m pip install -r "%INSTALL_DIR%\requirements.txt" --quiet

:: 5. Create launcher batch files in %BIN_DIR%
echo ==> Creating github command launcher...
(
echo @echo off
echo set "GITHUB_UPLOADER_CWD=%%CD%%"
echo set "APP_DIR=%USERPROFILE%\.Github-Auto-Uploader"
echo set "PYTHONPATH=%%APP_DIR%%;%%PYTHONPATH%%"
echo if exist "%%APP_DIR%%\.venv_path" ^(
echo     set /p VENV_DIR=^<"%%APP_DIR%%\.venv_path"
echo     if exist "%%VENV_DIR%%\Scripts\activate.bat" call "%%VENV_DIR%%\Scripts\activate.bat"
echo     if exist "%%VENV_DIR%%\Scripts\python.exe" ^(
echo         "%%VENV_DIR%%\Scripts\python.exe" "%%APP_DIR%%\github_uploader.py" %%*
echo         goto :eof
echo     ^)
echo ^)
echo if exist "%USERPROFILE%\myenv\Scripts\python.exe" ^(
echo     call "%USERPROFILE%\myenv\Scripts\activate.bat"
echo     "%USERPROFILE%\myenv\Scripts\python.exe" "%%APP_DIR%%\github_uploader.py" %%*
echo     goto :eof
echo ^)
echo python "%%APP_DIR%%\github_uploader.py" %%*
) > "%BIN_DIR%\github.bat"

:: Typo launchers
for %%T in (gthub gihub githb gitub ghub githup git-hub githubb) do (
    (
    echo @echo off
    echo echo Typo detected: "%%~n0". Launching github...
    echo timeout /t 1 /nobreak ^>nul
    echo call "%BIN_DIR%\github.bat" %%*
    ) > "%BIN_DIR%\%%T.bat"
)

:: 6. Ensure %BIN_DIR% is in User PATH
echo %PATH% | find /i "%BIN_DIR%" >nul 2>&1
if %errorlevel% neq 0 (
    echo ==> Adding %BIN_DIR% to User PATH...
    for /f "tokens=2*" %%a in ('reg query "HKCU\Environment" /v Path 2^>nul') do set "CUR_PATH=%%b"
    if defined CUR_PATH (
        setx PATH "%BIN_DIR%;%CUR_PATH%" >nul 2>&1
    ) else (
        setx PATH "%BIN_DIR%" >nul 2>&1
    )
    set "PATH=%BIN_DIR%;%PATH%"
)

echo.
echo ============================================================
echo [✓] Installation Complete!
echo [✓] Source Directory: %INSTALL_DIR%
echo [✓] Virtual Environment: %MYENV_DIR%
echo [✓] Type 'github' anywhere in Command Prompt or PowerShell!
echo ============================================================
echo.
echo ==> Launching GitHub Auto Uploader Pro...
call "%BIN_DIR%\github.bat"
