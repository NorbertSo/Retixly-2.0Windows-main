@echo off
echo ==========================================
echo    RETIXLY RELEASE BUILD SCRIPT
echo ==========================================
echo.

echo [1/5] Czyszczenie poprzednich buildow...
if exist "dist" rmdir /s /q "dist"
if exist "build" rmdir /s /q "build"
if exist "Retixly-1.0.0-Setup.exe" del "Retixly-1.0.0-Setup.exe"
echo       Wyczyszczone!

echo.
echo [2/5] Sprawdzanie pliku main.py...
if not exist "main.py" (
    echo BLAD: Nie znaleziono pliku main.py
    pause
    exit /b 1
)
echo       main.py - OK

echo.
echo [3/5] Budowanie EXE z PyInstaller...
python -m PyInstaller Retixly.spec

if not exist "dist\Retixly\Retixly.exe" (
    echo BLAD: Nie udalo sie zbudowac EXE
    echo Sprawdz logi powyzej i napraw bledy
    pause
    exit /b 1
)
echo       EXE zbudowany pomyslnie!

echo.
echo [4/5] Sprawdzanie NSIS...
set NSIS_PATH="C:\Program Files (x86)\NSIS\makensis.exe"
if not exist %NSIS_PATH% (
    set NSIS_PATH="C:\Program Files\NSIS\makensis.exe"
)
if not exist %NSIS_PATH% (
    echo BLAD: Nie znaleziono NSIS makensis.exe
    echo Zainstaluj NSIS z: https://nsis.sourceforge.io/Download
    pause
    exit /b 1
)
echo       NSIS znaleziony!

echo.
echo [5/5] Tworzenie instalatora...
%NSIS_PATH% installer.nsi

if not exist "Retixly-1.0.0-Setup.exe" (
    echo BLAD: Nie udalo sie utworzyc instalatora
    echo Sprawdz plik installer.nsi i logi NSIS
    pause
    exit /b 1
)

echo.
echo ==========================================
echo        SUKCES! INSTALATOR GOTOWY
echo ==========================================
echo.
echo Plik: Retixly-1.0.0-Setup.exe
echo Rozmiar:
dir "Retixly-1.0.0-Setup.exe" | find "Retixly-1.0.0-Setup.exe"
echo.
echo Mozesz teraz:
echo 1. Przetestowac instalator lokalnie
echo 2. Wyslac go do testerow
echo 3. Opublikowac na GitHub Releases
echo.
pause