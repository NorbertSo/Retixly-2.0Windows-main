@echo off
echo ==========================================
echo    RETIXLY SIMPLE BUILD WITH AUTO-INSTALL
echo ==========================================
echo.

echo [1/4] Instalowanie minimalnych pakietów...
pip install -r requirements_base.txt

echo [2/4] Czyszczenie...
if exist "dist" rmdir /s /q "dist" 
if exist "build" rmdir /s /q "build"

echo [3/4] Budowanie aplikacji (minimalna + bootstrap)...
python -m PyInstaller build_simple.spec --clean --noconfirm

echo [4/4] Sprawdzanie rozmiaru...
if exist "dist\Retixly\Retixly.exe" (
    for /f %%i in ('powershell -command "(Get-ChildItem -Path 'dist\Retixly' -Recurse | Measure-Object -Property Length -Sum).Sum / 1MB"') do set SIZE=%%i
    echo ✅ SUKCES! Aplikacja: %SIZE% MB
    echo.
    echo 🎯 JAK TO DZIAŁA:
    echo 1. Użytkownik uruchamia aplikację
    echo 2. Przy pierwszym uruchomieniu: dialog instalacji pakietów  
    echo 3. Automatyczne pobieranie wszystkich wymaganych pakietów
    echo 4. Następne uruchomienia: normalna praca
    echo.
    echo 📦 GOTOWE DO STWORZENIA INSTALATORA
) else (
    echo ❌ BŁĄD: Nie udało się zbudować
)

pause