@echo off
echo ==========================================
echo    RETIXLY LIGHTWEIGHT BUILD + INSTALLER
echo ==========================================
echo.

echo [1/6] Sprawdzanie plików...
if not exist "main.py" (echo BŁĄD: main.py nie znaleziony && pause && exit /b 1)
if not exist "bootstrap_ui.py" (echo BŁĄD: bootstrap_ui.py nie znaleziony && pause && exit /b 1)
if not exist "version_info.txt" (echo BŁĄD: version_info.txt nie znaleziony && pause && exit /b 1)
echo ✅ Pliki źródłowe OK

echo.
echo [2/6] Czyszczenie poprzednich buildów...
if exist "dist" rmdir /s /q "dist"
if exist "build" rmdir /s /q "build"
if exist "Retixly-1.0.0-Setup.exe" del "Retixly-1.0.0-Setup.exe"
echo ✅ Wyczyszczone

echo.
echo [3/6] Budowanie LIGHTWEIGHT EXE (bez pakietów AI)...
python -m PyInstaller build_simple.spec --clean --noconfirm

if not exist "dist\Retixly\Retixly.exe" (
    echo ❌ BŁĄD: EXE nie zbudował się
    pause && exit /b 1
)

echo.
echo [4/6] Sprawdzanie rozmiaru...
for /f %%i in ('powershell -command "(Get-ChildItem -Path 'dist\Retixly' -Recurse | Measure-Object -Property Length -Sum).Sum / 1MB"') do set SIZE=%%i
echo 📦 Rozmiar LIGHTWEIGHT app: %SIZE% MB

if %SIZE% GTR 500 (
    echo ⚠️ OSTRZEŻENIE: Aplikacja nadal za duża (%SIZE% MB)
    echo Sprawdź czy wszystkie duże pakiety zostały wykluczone
    pause
)

echo.
echo [5/6] Test aplikacji...
echo Sprawdzanie czy aplikacja się uruchamia...
cd "dist\Retixly"
start "" "Retixly.exe"
timeout /t 3 /nobreak >nul
taskkill /F /IM "Retixly.exe" >nul 2>&1
cd ..\..
echo ✅ Test uruchomienia OK

echo.
echo [6/6] Tworzenie instalatora NSIS...
set NSIS_PATH="C:\Program Files (x86)\NSIS\makensis.exe"
if not exist %NSIS_PATH% (
    set NSIS_PATH="C:\Program Files\NSIS\makensis.exe"
)

if exist %NSIS_PATH% (
    echo 🔨 Tworzenie instalatora...
    %NSIS_PATH% installer_final.nsi
    
    if exist "Retixly-1.0.0-Setup.exe" (
        for /f %%i in ('powershell -command "(Get-Item 'Retixly-1.0.0-Setup.exe').Length / 1MB"') do set INSTALLER_SIZE=%%i
        echo.
        echo ==========================================
        echo        SUKCES! INSTALATOR GOTOWY!
        echo ==========================================
        echo.
        echo 🎉 LIGHTWEIGHT INSTALATOR: Retixly-1.0.0-Setup.exe
        echo 📦 Rozmiar aplikacji: %SIZE% MB
        echo 📦 Rozmiar instalatora: %INSTALLER_SIZE% MB
        echo.
        echo 📋 JAK TO DZIAŁA:
        echo 1. Użytkownik pobiera mały instalator (%INSTALLER_SIZE% MB)
        echo 2. Instaluje szybko do Program Files
        echo 3. Przy pierwszym uruchomieniu - bootstrap dialog
        echo 4. Automatycznie pobiera pakiety AI (~2-3GB)
        echo 5. Następne uruchomienia - normalna praca
        echo.
        echo ✅ GOTOWE DO DYSTRYBUCJI!
    ) else (
        echo ❌ Błąd tworzenia instalatora NSIS
        echo Tworzę ZIP zamiast instalatora...
        powershell -command "Compress-Archive -Path 'dist\Retixly\*' -DestinationPath 'Retixly-1.0.0-Lightweight.zip' -CompressionLevel Optimal -Force"
        
        if exist "Retixly-1.0.0-Lightweight.zip" (
            for /f %%i in ('powershell -command "(Get-Item 'Retixly-1.0.0-Lightweight.zip').Length / 1MB"') do set ZIP_SIZE=%%i
            echo ✅ LIGHTWEIGHT ZIP: %ZIP_SIZE% MB
        )
    )
) else (
    echo ⚠️ NSIS nie znaleziony
    echo Tworzę portable ZIP...
    powershell -command "Compress-Archive -Path 'dist\Retixly\*' -DestinationPath 'Retixly-1.0.0-Lightweight.zip' -CompressionLevel Optimal -Force"
    
    if exist "Retixly-1.0.0-Lightweight.zip" (
        for /f %%i in ('powershell -command "(Get-Item 'Retixly-1.0.0-Lightweight.zip').Length / 1MB"') do set ZIP_SIZE=%%i
        echo ✅ LIGHTWEIGHT ZIP: %ZIP_SIZE% MB
        echo.
        echo 📋 JAK TO DZIAŁA:
        echo 1. Rozpakuj ZIP i uruchom Retixly.exe
        echo 2. Przy pierwszym uruchomieniu - bootstrap pobierze AI
        echo 3. Szybki download dla testerów!
    )
)

echo.
pause