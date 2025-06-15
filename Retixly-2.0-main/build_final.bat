@echo off
echo ==========================================
echo    RETIXLY FINAL BUILD - KOMPLETNY INSTALLER
echo ==========================================
echo.

echo [1/5] Sprawdzanie środowiska...
if not exist "main.py" (echo BŁĄD: main.py nie znaleziony && pause && exit /b 1)
if not exist "bootstrap_ui.py" (echo BŁĄD: bootstrap_ui.py nie znaleziony && pause && exit /b 1)
echo ✅ Pliki źródłowe OK

echo.
echo [2/5] Budowanie EXE...
python -m PyInstaller Retixly.spec --clean --noconfirm

if not exist "dist\Retixly\Retixly.exe" (
    echo ❌ BŁĄD: EXE nie zbudował się
    pause && exit /b 1
)

echo.
echo [3/5] Naprawianie bootstrap...
copy "bootstrap_ui.py" "dist\Retixly\bootstrap_ui.py" >nul
echo ✅ Bootstrap naprawiony

echo.
echo [4/5] Sprawdzanie rozmiaru...
for /f %%i in ('powershell -command "(Get-ChildItem -Path 'dist\Retixly' -Recurse | Measure-Object -Property Length -Sum).Sum / 1MB"') do set SIZE=%%i
echo 📦 Rozmiar aplikacji: %SIZE% MB

echo.
echo [5/5] Tworzenie instalatora...
set NSIS_PATH="C:\Program Files (x86)\NSIS\makensis.exe"
if not exist %NSIS_PATH% (
    set NSIS_PATH="C:\Program Files\NSIS\makensis.exe"
)

if exist %NSIS_PATH% (
    echo 🔨 Tworzenie instalatora z NSIS...
    %NSIS_PATH% installer_final.nsi
    
    if exist "Retixly-1.0.0-Setup.exe" (
        for /f %%i in ('powershell -command "(Get-Item 'Retixly-1.0.0-Setup.exe').Length / 1MB"') do set INSTALLER_SIZE=%%i
        echo ✅ INSTALATOR GOTOWY!
        echo 📦 Rozmiar instalatora: %INSTALLER_SIZE% MB
        echo 📁 Plik: Retixly-1.0.0-Setup.exe
    ) else (
        echo ❌ Błąd tworzenia instalatora
    )
) else (
    echo ⚠️ NSIS nie znaleziony - tworzę portable ZIP...
    powershell -command "Compress-Archive -Path 'dist\Retixly\*' -DestinationPath 'Retixly-1.0.0-Portable.zip' -CompressionLevel Optimal -Force"
    
    if exist "Retixly-1.0.0-Portable.zip" (
        for /f %%i in ('powershell -command "(Get-Item 'Retixly-1.0.0-Portable.zip').Length / 1MB"') do set ZIP_SIZE=%%i
        echo ✅ PORTABLE ZIP GOTOWY!
        echo 📦 Rozmiar ZIP: %ZIP_SIZE% MB
        echo 📁 Plik: Retixly-1.0.0-Portable.zip
    )
)

echo.
echo ==========================================
echo        BUILD ZAKOŃCZONY!
echo ==========================================
echo.
if exist "Retixly-1.0.0-Setup.exe" (
    echo 🎉 MASZ INSTALATOR: Retixly-1.0.0-Setup.exe
    echo.
    echo 📋 INSTRUKCJE DLA TESTERÓW:
    echo 1. Pobierz: Retixly-1.0.0-Setup.exe
    echo 2. Uruchom jako administrator
    echo 3. Zainstaluj w Program Files
    echo 4. Uruchom z Menu Start
    echo 5. Przy pierwszym uruchomieniu wybierz "Install AI Components"
    echo.
    echo 📤 GOTOWE DO DYSTRYBUCJI!
)

if exist "Retixly-1.0.0-Portable.zip" (
    echo 🎉 MASZ PORTABLE: Retixly-1.0.0-Portable.zip
    echo.
    echo 📋 INSTRUKCJE DLA TESTERÓW:
    echo 1. Pobierz i rozpakuj ZIP
    echo 2. Uruchom Retixly.exe z folderu
    echo 3. Przy pierwszym uruchomieniu wybierz "Install AI Components"
    echo.
    echo 📤 GOTOWE DO DYSTRYBUCJI!
)

echo.
pause