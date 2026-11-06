# ============================================================
# GitHub Auto Uploader Pro - Windows PowerShell Installer
# ============================================================
$ErrorActionPreference = "Stop"

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "🚀 GITHUB AUTO UPLOADER PRO - POWERSHELL INSTALLER" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

$InstallDir = "$env:USERPROFILE\.Github-Auto-Uploader"
$BinDir = "$env:USERPROFILE\.local\bin"
$MyEnvDir = "$env:USERPROFILE\myenv"

if (!(Test-Path $InstallDir)) { New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null }
if (!(Test-Path $BinDir)) { New-Item -ItemType Directory -Path $BinDir -Force | Out-Null }

# 1. Download or copy repo
Write-Host "==> Syncing files to $InstallDir..." -ForegroundColor Yellow
$TmpDir = [System.IO.Path]::Combine([System.IO.Path]::GetTempPath(), [System.IO.Path]::GetRandomFileName())
git clone --depth 1 https://github.com/Mr-Risov/GitHub-Auto-Uploader.git $TmpDir
Copy-Item -Path "$TmpDir\github_auto_uploader" -Destination $InstallDir -Recurse -Force
Copy-Item -Path "$TmpDir\github_uploader.py" -Destination $InstallDir -Force
Copy-Item -Path "$TmpDir\requirements.txt" -Destination $InstallDir -Force
Copy-Item -Path "$TmpDir\install.bat" -Destination $InstallDir -Force -ErrorAction SilentlyContinue
Copy-Item -Path "$TmpDir\README.md" -Destination $InstallDir -Force -ErrorAction SilentlyContinue
Remove-Item -Path $TmpDir -Recurse -Force

# 2. Check / Create Virtualenv
Write-Host "==> Checking virtual environment at $MyEnvDir..." -ForegroundColor Yellow
if (!(Test-Path "$MyEnvDir\Scripts\python.exe")) {
    Write-Host "==> Creating virtual environment at $MyEnvDir..." -ForegroundColor Cyan
    python -m venv $MyEnvDir
}

$VenvPython = "$MyEnvDir\Scripts\python.exe"
if (Test-Path $VenvPython) {
    Set-Content -Path "$InstallDir\.venv_path" -Value $MyEnvDir
    Write-Host "[✓] Virtual environment ready: $MyEnvDir" -ForegroundColor Green
} else {
    $VenvPython = "python"
}

# 3. Install requirements
Write-Host "==> Installing requirements..." -ForegroundColor Yellow
& $VenvPython -m pip install --upgrade pip setuptools wheel --quiet
& $VenvPython -m pip install -r "$InstallDir\requirements.txt" --quiet

# 4. Create launcher scripts in BinDir
$LauncherContent = @"
@echo off
set "GITHUB_UPLOADER_CWD=%CD%"
set "APP_DIR=$env:USERPROFILE\.Github-Auto-Uploader"
set "PYTHONPATH=%APP_DIR%;%PYTHONPATH%"
if exist "%APP_DIR%\.venv_path" (
    set /p VENV_DIR=<"%APP_DIR%\.venv_path"
    if exist "%VENV_DIR%\Scripts\activate.bat" call "%VENV_DIR%\Scripts\activate.bat"
    if exist "%VENV_DIR%\Scripts\python.exe" (
        "%VENV_DIR%\Scripts\python.exe" "%APP_DIR%\github_uploader.py" %*
        goto :eof
    )
)
if exist "$env:USERPROFILE\myenv\Scripts\python.exe" (
    call "$env:USERPROFILE\myenv\Scripts\activate.bat"
    "$env:USERPROFILE\myenv\Scripts\python.exe" "%APP_DIR%\github_uploader.py" %*
    goto :eof
)
python "%APP_DIR%\github_uploader.py" %*
"@

Set-Content -Path "$BinDir\github.bat" -Value $LauncherContent -Force

# Create typo commands
$TypoList = @("gthub", "gihub", "githb", "gitub", "ghub", "githup", "git-hub", "githubb")
foreach ($t in $TypoList) {
    $TypoContent = @"
@echo off
echo Typo detected: "%~n0". Launching github...
timeout /t 1 /nobreak >nul
call "$BinDir\github.bat" %*
"@
    Set-Content -Path "$BinDir\$t.bat" -Value $TypoContent -Force
}

# 5. Add to User Path
$UserPath = [Environment]::GetEnvironmentVariable("Path", "User")
if ($UserPath -notlike "*$BinDir*") {
    [Environment]::SetEnvironmentVariable("Path", "$BinDir;$UserPath", "User")
    $env:Path = "$BinDir;$env:Path"
}

Write-Host "============================================================" -ForegroundColor Green
Write-Host "✅ Installation Complete! Type 'github' anywhere to run." -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green

# Launch
& "$BinDir\github.bat"
