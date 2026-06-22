@echo off
chcp 65001 > nul
cls

:: =====================================================================
:: 1. AM I ADMIN? (REQUIRED TO DELETE FROM PROGRAM FILES)
:: =====================================================================
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo [SYSTEM] Requesting Administrator privileges...
    powershell -Command "Start-Process '%~fnx0' -Verb RunAs"
    exit /b
)

cd /d "%~dp0"

:: =====================================================================
:: 2. TARGET PATHS CONFIGURATION
:: =====================================================================
set "ROAMING_TARGET=%APPDATA%\BackendAI"
set "AE_TARGET=C:\Program Files\Common Files\Adobe\CEP\extensions\ScripterAE"
set "DV_TARGET=C:\Program Files\ScripterDavinci"

:: =====================================================================
:: 3. INTERACTIVE USER INTERFACE
:: =====================================================================
echo ========================================================
echo                  AISCRIPTER UNINSTALLER
echo ========================================================
echo.
echo Select your uninstallation strategy:
echo [1] Full Uninstall (After Effects + DaVinci Resolve + AI Core)
echo [2] Remove After Effects Panel Only
echo [3] Remove DaVinci Resolve App Only
echo [4] Exit
echo.
set /p choice="Enter choice (1-4) and press Enter: "

if "%choice%"=="1" goto remove_full
if "%choice%"=="2" goto remove_ae
if "%choice%"=="3" goto remove_dv
if "%choice%"=="4" exit
goto error_input

:remove_full
echo.
echo === [STEP] FULL UNINSTALLATION INITIALIZED...
call :delete_ae
call :delete_dv
call :delete_core
goto finish

:remove_ae
echo.
echo === [STEP] REMOVING AFTER EFFECTS PIPELINE...
call :delete_ae
:: Smart Check: If DaVinci isn't there, wipe the AI Core completely
if not exist "%DV_TARGET%" (
    echo No other pipeline hosts detected. Cleaning up AI Core...
    call :delete_core
) else (
    echo DaVinci Resolve pipeline detected. Keeping AI Core intact.
)
goto finish

:remove_dv
echo.
echo === [STEP] REMOVING DAVINCI RESOLVE PIPELINE...
call :delete_dv
:: Smart Check: If AE isn't there, wipe the AI Core completely
if not exist "%AE_TARGET%" (
    echo No other pipeline hosts detected. Cleaning up AI Core...
    call :delete_core
) else (
    echo After Effects pipeline detected. Keeping AI Core intact.
)
goto finish

:: =====================================================================
:: 4. DELETION MODULES
:: =====================================================================

:delete_ae
if exist "%AE_TARGET%" (
    echo Removing After Effects extension panel...
    rmdir /s /q "%AE_TARGET%"
) else (
    echo [SKIP] After Effects panel not found.
)
exit /b

:delete_dv
if exist "%DV_TARGET%" (
    echo Removing DaVinci Resolve app...
    rmdir /s /q "%DV_TARGET%"
) else (
    echo [SKIP] DaVinci Resolve app not found.
)
exit /b

:delete_core
if exist "%ROAMING_TARGET%" (
    echo Removing heavy AI core and model weights...
    rmdir /s /q "%ROAMING_TARGET%"
) else (
    echo [SKIP] AI core environment not found.
)
exit /b

:error_input
echo.
echo [ERROR] Invalid selection. Aborting.
pause
exit

:finish
echo.
echo ========================================================
echo [SUCCESS] Uninstallation process complete!
echo ========================================================
pause
exit