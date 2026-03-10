@echo off
setlocal enabledelayedexpansion

REM --- Setup ANSI color codes ---
for /f %%e in ('powershell -NoProfile -Command "[char]27"') do set "E=%%e"
set "R=!E![0m"
set "RED=!E![91m"
set "GRN=!E![92m"
set "YEL=!E![93m"
set "CYN=!E![96m"
set "BLD=!E![1m"
set "DIM=!E![90m"

echo.
echo   !CYN!============================================!R!
echo   !BLD!     LiteWing Library Installer!R!
echo   !CYN!============================================!R!
echo.

REM --- Configuration ---
set "PYTHON_VERSION=3.11.9"
set "PYTHON_INSTALLER=python-%PYTHON_VERSION%-amd64.exe"
set "PYTHON_URL=https://www.python.org/ftp/python/%PYTHON_VERSION%/%PYTHON_INSTALLER%"
set "PYTHON_INSTALL_DIR=%LOCALAPPDATA%\Programs\Python\Python311"

REM =========================================
REM  STEP 1: Verify System Date and Time
REM =========================================
echo   !BLD![Step 1/3]!R! System date and time:
echo.
echo            !BLD!%DATE%  %TIME%!R!
echo.
echo   !YEL!Make sure the above date and time is correct!!R!
echo   !DIM!Wrong date/time will cause download errors!R!
echo.

REM =========================================
REM  STEP 2: Check / Install Python 3.11
REM =========================================
echo   !BLD![Step 2/3]!R! Checking for Python 3.11...

set "PY311_CMD="

REM Method 1: py launcher
py -3.11 --version >nul 2>&1
if not errorlevel 1 (
    set "PY311_CMD=py -3.11"
    goto :python_found
)

REM Method 2: default python command
for /f "tokens=2 delims= " %%v in ('python --version 2^>^&1') do (
    echo %%v | findstr /b "3.11" >nul
    if not errorlevel 1 (
        set "PY311_CMD=python"
        goto :python_found
    )
)

REM Method 3: common install path
if exist "%PYTHON_INSTALL_DIR%\python.exe" (
    set "PY311_CMD=%PYTHON_INSTALL_DIR%\python.exe"
    goto :python_found
)

REM --- Not found - download and install ---
echo   !YEL![!] Python 3.11 not found. Installing automatically...!R!
echo.

call :download_file "%PYTHON_URL%" "%TEMP%\%PYTHON_INSTALLER%" "Python %PYTHON_VERSION%"
if errorlevel 1 (
    echo.
    echo   !RED![ERROR] Python download failed!!R!
    echo.
    echo   Possible causes:
    echo     - No internet connection
    echo     - System date/time is wrong - causes SSL errors
    echo.
    echo   Manual download: https://www.python.org/downloads/release/python-3119/
    echo.
    pause
    exit /b 1
)

echo.
echo   Installing Python %PYTHON_VERSION%...
echo   !DIM!This takes 1-2 minutes, please wait...!R!
echo.

"%TEMP%\%PYTHON_INSTALLER%" /quiet InstallAllUsers=0 PrependPath=1 Include_test=0 Include_launcher=1

if errorlevel 1 (
    echo   !RED![ERROR] Python installation failed!!R!
    echo   Try running the installer manually: %TEMP%\%PYTHON_INSTALLER%
    echo.
    pause
    exit /b 1
)

echo   !GRN![OK] Python %PYTHON_VERSION% installed!!R!
echo.
del "%TEMP%\%PYTHON_INSTALLER%" >nul 2>&1

REM Refresh PATH for this session
set "PATH=%PYTHON_INSTALL_DIR%;%PYTHON_INSTALL_DIR%\Scripts;%PATH%"
set "PY311_CMD=%PYTHON_INSTALL_DIR%\python.exe"

:python_found
echo   !GRN![OK]!R! Python: !PY311_CMD!
for /f "tokens=*" %%v in ('!PY311_CMD! --version 2^>^&1') do echo        !DIM!%%v!R!
echo.

REM =========================================
REM  STEP 3: Install LiteWing Library
REM =========================================
echo   !BLD![Step 3/3]!R! Installing LiteWing library...
echo   !DIM!Downloads cflib + matplotlib = may take a few minutes!R!
echo.

!PY311_CMD! -m pip install --upgrade pip >nul 2>&1
!PY311_CMD! -m pip install .

if errorlevel 1 (
    echo.
    echo   !RED![ERROR] LiteWing installation failed!!R!
    echo.
    echo   Possible causes:
    echo     - No internet connection
    echo     - System date/time is wrong - causes SSL errors
    echo       !YEL!Fix: Right-click clock, Adjust date/time, Set time automatically!R!
    echo.
    echo   Try manually: !PY311_CMD! -m pip install . --verbose
    echo.
    pause
    exit /b 1
)

REM =========================================
REM  Verify
REM =========================================
echo.
!PY311_CMD! -c "from litewing import LiteWing; print('  \033[92m[OK] LiteWing library imported successfully!\033[0m')" 2>nul
if errorlevel 1 (
    echo   !YEL![WARN] LiteWing installed but import check failed.!R!
)

echo.
echo   !GRN!============================================!R!
echo   !GRN!!BLD!       Installation Complete!  !R!
echo   !GRN!============================================!R!
echo.
echo   !GRN![OK]!R! Python 3.11
echo   !GRN![OK]!R! LiteWing library
echo   !GRN![OK]!R! cflib + matplotlib
echo.
echo   !BLD!To fly your drone:!R!
echo     1. Turn on the drone
echo     2. Connect to the drone's WiFi network
echo     3. Run: !CYN!!PY311_CMD! examples\level_1\01_battery_voltage.py!R!
echo.
pause
exit /b 0

REM =========================================
REM  Helper: Download a file using PowerShell
REM  Usage: call :download_file "URL" "OUTPUT_PATH" "LABEL"
REM =========================================
:download_file
set "DL_URL=%~1"
set "DL_OUT=%~2"
set "DL_LABEL=%~3"

echo   Downloading %DL_LABEL%...

REM Write PowerShell script to temp file to avoid escaping issues
set "PS_SCRIPT=%TEMP%\litewing_download.ps1"

echo [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12 > "%PS_SCRIPT%"
echo $url = '%DL_URL%' >> "%PS_SCRIPT%"
echo $out = '%DL_OUT%' >> "%PS_SCRIPT%"
echo Write-Host '  Downloading...' -ForegroundColor Cyan >> "%PS_SCRIPT%"
echo try { >> "%PS_SCRIPT%"
echo     Invoke-WebRequest -Uri $url -OutFile $out -UseBasicParsing >> "%PS_SCRIPT%"
echo     Write-Host '  Download complete!' -ForegroundColor Green >> "%PS_SCRIPT%"
echo } catch { >> "%PS_SCRIPT%"
echo     Write-Host ('  Error: ' + $_.Exception.Message) -ForegroundColor Red >> "%PS_SCRIPT%"
echo     exit 1 >> "%PS_SCRIPT%"
echo } >> "%PS_SCRIPT%"

powershell -NoProfile -ExecutionPolicy Bypass -File "%PS_SCRIPT%"
set "DL_RESULT=%ERRORLEVEL%"

del "%PS_SCRIPT%" >nul 2>&1

if not exist "%DL_OUT%" exit /b 1
if %DL_RESULT% NEQ 0 exit /b 1
exit /b 0
