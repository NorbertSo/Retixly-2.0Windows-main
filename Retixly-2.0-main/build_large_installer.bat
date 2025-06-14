@echo off
echo ==========================================
echo    RETIXLY LARGE INSTALLER BUILD
echo ==========================================
echo.

echo [1/5] Sprawdzanie aplikacji...
if not exist "dist\Retixly\Retixly.exe" (
    echo BLAD: Aplikacja nie istnieje
    echo Uruchom najpierw: python -m PyInstaller build_config.spec
    pause
    exit /b 1
)

for /f %%i in ('powershell -command "(Get-ChildItem -Path 'dist\Retixly' -Recurse | Measure-Object -Property Length -Sum).Sum / 1MB"') do set APP_SIZE=%%i
echo       Aplikacja gotowa: %APP_SIZE% MB

echo.
echo [2/5] Sprawdzanie NSIS...
set NSIS_PATH="C:\Program Files (x86)\NSIS\makensis.exe"
if not exist %NSIS_PATH% (
    set NSIS_PATH="C:\Program Files\NSIS\makensis.exe"
)
if not exist %NSIS_PATH% (
    echo BLAD: NSIS nie jest zainstalowany
    echo.
    echo ROZWIAZANIE:
    echo 1. Pobierz NSIS z: https://nsis.sourceforge.io/Download
    echo 2. Zainstaluj NSIS
    echo 3. Uruchom ten skrypt ponownie
    echo.
    pause
    exit /b 1
)
echo       NSIS znaleziony!

echo.
echo [3/5] Sprawdzanie pliku installer_large.nsi...
if not exist "installer_large.nsi" (
    echo BLAD: Plik installer_large.nsi nie istnieje
    echo Stworz plik installer_large.nsi z konfiguracja
    pause
    exit /b 1
)
echo       Plik installer_large.nsi gotowy

echo.
echo [4/5] Budowanie instalatora...
echo UWAGA: To moze potrwac 10-30 minut dla aplikacji %APP_SIZE% MB
echo Nie przerywaj procesu!
echo.

echo Rozpoczynam budowanie...
%NSIS_PATH% /V3 installer_large.nsi

if exist "Retixly-1.0.0-Setup.exe" (
    echo.
    echo       SUKCES! Instalator utworzony
    for /f %%i in ('powershell -command "(Get-Item 'Retixly-1.0.0-Setup.exe').Length / 1MB"') do set INSTALLER_SIZE=%%i
    echo       Rozmiar instalatora: %INSTALLER_SIZE% MB
) else (
    echo.
    echo       BLAD: Instalator nie zostal utworzony
    echo.
    echo MOZLIWE PRZYCZYNY:
    echo 1. Brak miejsca na dysku
    echo 2. Aplikacja jest uruchomiona
    echo 3. Blokada antywirusowa
    echo 4. Blad w pliku .nsi
    echo.
    echo ROZWIAZANIA:
    echo 1. Zamknij aplikacje Retixly
    echo 2. Tymczasowo wylacz antywirus
    echo 3. Sprawdz czy masz 10GB wolnego miejsca
    echo 4. Uruchom jako administrator
    echo.
    pause
    exit /b 1
)

echo.
echo [5/5] Test instalatora...
echo Sprawdzanie czy instalator sie uruchamia...
echo (Test zostanie przerwany po 3 sekundach)

start "" "Retixly-1.0.0-Setup.exe"
timeout /t 3 /nobreak >nul
taskkill /F /IM "Retixly-1.0.0-Setup.exe" >nul 2>&1

echo.
echo ==========================================
echo         INSTALATOR GOTOWY!
echo ==========================================
echo.
echo Plik: Retixly-1.0.0-Setup.exe
echo Rozmiar: %INSTALLER_SIZE% MB
echo Aplikacja: %APP_SIZE% MB
echo.
echo DYSTRYBUCJA:
echo 1. WeTransfer Pro ^(20GB limit^) - $10/miesiąc
echo 2. Google Drive ^(15GB darmowe^)
echo 3. Mega.nz ^(20GB darmowe^)
echo 4. GitHub LFS ^(2GB darmowe + $5/50GB^)
echo.
echo ZALECENIE dla %INSTALLER_SIZE% MB:
if %INSTALLER_SIZE% GTR 2000 (
    echo - Mega.nz ^(darmowe 20GB^)
    echo - Google Drive ^(jesli masz miejsce^)
) else (
    echo - WeTransfer ^(darmowe 2GB^)
    echo - GitHub Release ^(do 2GB^)
)
echo.
echo INSTRUKCJE DLA TESTEROW:
echo 1. Pobierz Retixly-1.0.0-Setup.exe
echo 2. Uruchom jako administrator
echo 3. Zainstaluj ^(moze potrwac kilka minut^)
echo 4. Uruchom z menu Start
echo 5. Testuj auto-update: Help -^> Check for Updates
echo.
pause