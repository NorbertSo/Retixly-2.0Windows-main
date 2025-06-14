@echo off
echo ==========================================
echo    RETIXLY PORTABLE BUILD SCRIPT
echo ==========================================
echo.

echo [1/4] Czyszczenie poprzednich buildow...
if exist "Retixly-1.0.0-Portable.zip" del "Retixly-1.0.0-Portable.zip"
if exist "Retixly-1.0.0-Portable.7z" del "Retixly-1.0.0-Portable.7z"
echo       Wyczyszczone!

echo.
echo [2/4] Sprawdzanie czy EXE istnieje...
if not exist "dist\Retixly\Retixly.exe" (
    echo BLAD: Nie znaleziono dist\Retixly\Retixly.exe
    echo Uruchom najpierw: python -m PyInstaller build_config.spec
    pause
    exit /b 1
)
echo       EXE znaleziony!

echo.
echo [3/4] Sprawdzanie rozmiaru aplikacji...
for /f %%i in ('powershell -command "(Get-ChildItem -Path 'dist\Retixly' -Recurse | Measure-Object -Property Length -Sum).Sum / 1MB"') do set APP_SIZE_MB=%%i
echo       Rozmiar aplikacji: %APP_SIZE_MB% MB

echo.
echo [4/4] Tworzenie archiwum portable...

REM Sprobuj z PowerShell (wbudowane w Windows)
echo Tworzenie ZIP z PowerShell...
powershell -command "Compress-Archive -Path 'dist\Retixly\*' -DestinationPath 'Retixly-1.0.0-Portable.zip' -Force"

if exist "Retixly-1.0.0-Portable.zip" (
    echo       ZIP utworzony pomyslnie!
    for /f %%i in ('powershell -command "(Get-Item 'Retixly-1.0.0-Portable.zip').Length / 1MB"') do set ZIP_SIZE_MB=%%i
    echo       Rozmiar ZIP: %ZIP_SIZE_MB% MB
) else (
    echo       Blad tworzenia ZIP
)

REM Sprawdz czy jest 7-Zip
where 7z >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    echo Tworzenie 7Z z lepszą kompresją...
    7z a -t7z -mx=9 "Retixly-1.0.0-Portable.7z" "dist\Retixly\*"
    if exist "Retixly-1.0.0-Portable.7z" (
        echo       7Z utworzony pomyslnie!
        for /f %%i in ('powershell -command "(Get-Item 'Retixly-1.0.0-Portable.7z').Length / 1MB"') do set SEVEN_SIZE_MB=%%i
        echo       Rozmiar 7Z: %SEVEN_SIZE_MB% MB
    )
) else (
    echo 7-Zip nie znaleziony - tylko ZIP dostepny
)

echo.
echo ==========================================
echo        SUKCES! WERSJA PORTABLE GOTOWA
echo ==========================================
echo.
if exist "Retixly-1.0.0-Portable.zip" (
    echo Plik ZIP: Retixly-1.0.0-Portable.zip
)
if exist "Retixly-1.0.0-Portable.7z" (
    echo Plik 7Z:  Retixly-1.0.0-Portable.7z (mniejszy)
)
echo.
echo INSTRUKCJE DLA TESTEROW:
echo 1. Pobierz i rozpakuj archiwum
echo 2. Uruchom Retixly.exe z rozpakowanego folderu
echo 3. Aplikacja dziala bez instalacji
echo.
echo UWAGA: To wersja PORTABLE - nie wymaga instalatora!
echo Testerzy moga ja uruchomic bezposrednio po rozpakowaniu.
echo.
pause