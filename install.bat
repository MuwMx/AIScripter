@echo off
chcp 65001 > nul
cls

:: =====================================================================
:: 1. USER CONFIGURATION (PASTE YOUR LINKS HERE)
:: =====================================================================
set "URL_PYTHON=https://www.python.org/ftp/python/3.13.1/python-3.13.1-embed-amd64.zip"
set "URL_PYTHON314=https://www.python.org/ftp/python/3.14.0/python-3.14.0-amd64.exe"
set "URL_GET_PIP=https://bootstrap.pypa.io/get-pip.py"

set "URL_FFMPEG=https://huggingface.co/muwmix/AIScripter-Assets/resolve/main/ffmpeg_shared.zip"
set "URL_BIREFNET_MODEL=https://huggingface.co/joelseytre/toonout/resolve/main/birefnet_finetuned_toonout.pth"
set "URL_RIFE=https://huggingface.co/muwmix/AIScripter-Assets/resolve/main/rife46.pth?download=true"
set "URL_DEPTH_BASE=https://huggingface.co/depth-anything/Depth-Anything-V2-Base/resolve/main/depth_anything_v2_vitb.pth"
set "URL_DEPTH_LARGE=https://huggingface.co/depth-anything/Depth-Anything-V2-Large/resolve/main/depth_anything_v2_vitl.pth"

:: =====================================================================
:: 2. AM I ADMIN? (REQUIRED FOR ADOBE CEP COPIES)
:: =====================================================================
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo [SYSTEM] Requesting Administrator privileges...
    powershell -Command "Start-Process '%~fnx0' -Verb RunAs"
    exit /b
)

cd /d "%~dp0"

:: =====================================================================
:: 3. TARGET PATHS CONFIGURATION
:: =====================================================================
set "ROAMING_TARGET=%APPDATA%\MyScripterAE"
set "AE_TARGET=C:\Program Files\Common Files\Adobe\CEP\extensions\ScripterPanel"
set "DV_TARGET=C:\Program Files\ScripterDavinci"

:: =====================================================================
:: 4. INTERACTIVE USER INTERFACE
:: =====================================================================
echo ========================================================
echo          AISCRIPTER MULTI-HOST PIPELINE INSTALLER
echo ========================================================
echo.
echo Select your deployment strategy:
echo [1] Full Deployment (After Effects + DaVinci Resolve + AI Core)
echo [2] After Effects Pipeline Only (+ AI Core)
echo [3] DaVinci Resolve Pipeline Only (+ AI Core)
echo [4] Exit Installation
echo.
set /p choice="Enter choice (1-4) and press Enter: "

if "%choice%"=="1" (
    call :install_core
    call :install_ae
    call :install_davinci
    goto finish
)
if "%choice%"=="2" (
    call :install_core
    call :install_ae
    goto finish
)
if "%choice%"=="3" (
    call :install_core
    call :install_davinci
    goto finish
)
if "%choice%"=="4" exit
goto error_input

:: =====================================================================
:: 5. INSTALLATION MODULES
:: =====================================================================

:install_core
echo.
echo === [STEP] INITIALIZING AI CORE ARCHITECTURE...
if not exist "%ROAMING_TARGET%" mkdir "%ROAMING_TARGET%"

echo Syncing core backend scripts from local directory...
xcopy /E /I /Y "Backend" "%ROAMING_TARGET%"

rem Deploy Isolated Python Engine for Core AI Backend
if not exist "%ROAMING_TARGET%\python.exe" (
    echo Downloading official Windows embeddable Python package...
    curl -L -o "%ROAMING_TARGET%\python_embed.zip" "%URL_PYTHON%"
    echo Extracting Python core...
    tar -xf "%ROAMING_TARGET%\python_embed.zip" -C "%ROAMING_TARGET%"
    del "%ROAMING_TARGET%\python_embed.zip"
    
    echo. >> "%ROAMING_TARGET%\python313._pth"
    echo import site >> "%ROAMING_TARGET%\python313._pth"
) else (
    echo [SKIP] Isolated Python core already configured.
)

rem Bootstrap Pip Manager and Core AI Stack
if not exist "%ROAMING_TARGET%\Scripts\pip.exe" (
    echo Bootstrapping pip package manager...
    curl -L -o "%ROAMING_TARGET%\get-pip.py" "%URL_GET_PIP%"
    "%ROAMING_TARGET%\python.exe" "%ROAMING_TARGET%\get-pip.py" --no-warn-script-location
    del "%ROAMING_TARGET%\get-pip.py"
    
    echo Installing required core libraries: torch, transformers, opencv, kornia...
    "%ROAMING_TARGET%\python.exe" -m pip install torch transformers opencv-python kornia --no-cache-dir
) else (
    echo [SKIP] Pip package environment already configured.
)

rem Deploy FFmpeg Binary Shared Stack via PowerShell
if not exist "%ROAMING_TARGET%\ffmpeg_shared\ffmpeg.exe" (
    echo Downloading production-ready FFmpeg build...
    curl -L -o "%ROAMING_TARGET%\ffmpeg.zip" "%URL_FFMPEG%"
    echo Deploying media encoders...
    if not exist "%ROAMING_TARGET%\ffmpeg_shared" mkdir "%ROAMING_TARGET%\ffmpeg_shared"
    powershell -Command "Expand-Archive -Path '%ROAMING_TARGET%\ffmpeg.zip' -DestinationPath '%ROAMING_TARGET%\ffmpeg_shared' -Force"
    
    if exist "%ROAMING_TARGET%\ffmpeg_shared\ffmpeg_shared" (
        xcopy /E /I /Y "%ROAMING_TARGET%\ffmpeg_shared\ffmpeg_shared\*" "%ROAMING_TARGET%\ffmpeg_shared\"
        rmdir /S /Q "%ROAMING_TARGET%\ffmpeg_shared\ffmpeg_shared"
    )
    del "%ROAMING_TARGET%\ffmpeg.zip"
) else (
    echo [SKIP] FFmpeg shared binaries already configured.
)

if "%choice%"=="1" call :download_all_weights
if "%choice%"=="2" call :download_ae_weights
if "%choice%"=="3" call :download_dv_weights
exit /b

:download_all_weights
if not exist "%ROAMING_TARGET%\weights\rife4.6" mkdir "%ROAMING_TARGET%\weights\rife4.6"
if not exist "%ROAMING_TARGET%\weights\depth" mkdir "%ROAMING_TARGET%\weights\depth"
if not exist "%ROAMING_TARGET%\weights\bg" mkdir "%ROAMING_TARGET%\weights\bg"

if not exist "%ROAMING_TARGET%\weights\rife4.6\rife46.pth" (
    echo Downloading RIFE 4.6 model file...
    curl -L -o "%ROAMING_TARGET%\weights\rife4.6\rife46.pth" "%URL_RIFE%"
) else (
    echo [SKIP] RIFE 4.6 model already exists.
)

if not exist "%ROAMING_TARGET%\weights\depth\vitb.pth" (
    echo Downloading Depth Anything V2 Base weights...
    curl -L -o "%ROAMING_TARGET%\weights\depth\vitb.pth" "%URL_DEPTH_BASE%"
) else (
    echo [SKIP] Depth Anything V2 Base weights already exist.
)

if not exist "%ROAMING_TARGET%\weights\depth\vitl.pth" (
    echo Downloading Depth Anything V2 Large weights...
    curl -L -o "%ROAMING_TARGET%\weights\depth\vitl.pth" "%URL_DEPTH_LARGE%"
) else (
    echo [SKIP] Depth Anything V2 Large weights already exist.
)

if not exist "%ROAMING_TARGET%\weights\bg\birefnet_finetuned_toonout.pth" (
    echo Downloading BiRefNet Background Extraction weights...
    curl -L -o "%ROAMING_TARGET%\weights\bg\birefnet_finetuned_toonout.pth" "%URL_BIREFNET_MODEL%"
) else (
    echo [SKIP] BiRefNet weights already exist.
)
exit /b

:download_ae_weights
if not exist "%ROAMING_TARGET%\weights\rife4.6" mkdir "%ROAMING_TARGET%\weights\rife4.6"
if not exist "%ROAMING_TARGET%\weights\depth" mkdir "%ROAMING_TARGET%\weights\depth"
if not exist "%ROAMING_TARGET%\weights\bg" mkdir "%ROAMING_TARGET%\weights\bg"

if not exist "%ROAMING_TARGET%\weights\rife4.6\rife46.pth" (
    echo Downloading RIFE 4.6 model file...
    curl -L -o "%ROAMING_TARGET%\weights\rife4.6\rife46.pth" "%URL_RIFE%"
) else (
    echo [SKIP] RIFE 4.6 model already exists.
)

if not exist "%ROAMING_TARGET%\weights\depth\vitb.pth" (
    echo Downloading Depth Anything V2 Base weights...
    curl -L -o "%ROAMING_TARGET%\weights\depth\vitb.pth" "%URL_DEPTH_BASE%"
) else (
    echo [SKIP] Depth Anything V2 Base weights already exist.
)

if not exist "%ROAMING_TARGET%\weights\depth\vitl.pth" (
    echo Downloading Depth Anything V2 Large weights...
    curl -L -o "%ROAMING_TARGET%\weights\depth\vitl.pth" "%URL_DEPTH_LARGE%"
) else (
    echo [SKIP] Depth Anything V2 Large weights already exist.
)

if not exist "%ROAMING_TARGET%\weights\bg\birefnet_finetuned_toonout.pth" (
    echo Downloading BiRefNet Background Extraction weights...
    curl -L -o "%ROAMING_TARGET%\weights\bg\birefnet_finetuned_toonout.pth" "%URL_BIREFNET_MODEL%"
) else (
    echo [SKIP] BiRefNet weights already exist.
)
exit /b

:download_dv_weights
if not exist "%ROAMING_TARGET%\weights\rife4.6" mkdir "%ROAMING_TARGET%\weights\rife4.6"

if not exist "%ROAMING_TARGET%\weights\rife4.6\rife46.pth" (
    echo Downloading RIFE 4.6 model file...
    curl -L -o "%ROAMING_TARGET%\weights\rife4.6\rife46.pth" "%URL_RIFE%"
) else (
    echo [SKIP] RIFE 4.6 model already exists.
)
exit /b

:install_ae
echo.
echo === [STEP] INTEGRATING AFTER EFFECTS EXTENSION PANEL...
if not exist "ScripterAE" (
    echo [CRITICAL ERROR] Source folder ScripterAE not found!
    pause
    exit /b
)
if not exist "%AE_TARGET%" mkdir "%AE_TARGET%"
xcopy /E /I /Y "ScripterAE" "%AE_TARGET%"
echo [OK] Extension registered successfully.
exit /b

:install_davinci
echo.
echo === [STEP] DEPLOYING STANDALONE DAVINCI RESOLVE APP...

rem Deploy Registered Global Python Engine for DaVinci Scripting API
py -3.14 -V >nul 2>&1
if %errorLevel% neq 0 (
    echo [SYSTEM] Python 3.14 not found. Preparing global environment for DaVinci...
    echo Downloading official Windows installer...
    curl -L -o "%TEMP%\python_installer.exe" "%URL_PYTHON314%"
    
    echo Installing Python 3.14 with global PATH and launcher...
    echo This process runs in the background and takes 1-2 minutes. Do NOT close the window.
    
    "%TEMP%\python_installer.exe" /quiet InstallAllUsers=1 PrependPath=1 Include_launcher=1 Include_test=0 SimpleInstall=1
    del "%TEMP%\python_installer.exe"
    
    set "PATH=%PATH%;C:\Program Files\Python314;C:\Program Files\Python314\Scripts"
    
    echo Installing PySide6 user interface framework for Python 3.14...
    py -3.14 -m pip install PySide6
) else (
    echo [SKIP] Global Python 3.14 environment already configured.
    echo Syncing PySide6 framework for Python 3.14...
    py -3.14 -m pip install PySide6
)

if not exist "ScripterResolve" (
    echo [CRITICAL ERROR] Source folder ScripterResolve not found!
    pause
    exit /b
)
if not exist "%DV_TARGET%" mkdir "%DV_TARGET%"
xcopy /E /I /Y "ScripterResolve" "%DV_TARGET%"
echo [OK] Application successfully configured at %DV_TARGET%.
exit /b

:: =====================================================================
:: 6. STATUS CODES & TERMINATION
:: =====================================================================

:error_input
echo.
echo [ERROR] Invalid selection. Aborting installation.
pause
exit

:finish
echo.
echo ========================================================
echo [SUCCESS] AIScripter environment deployment complete!
echo ========================================================
pause
exit