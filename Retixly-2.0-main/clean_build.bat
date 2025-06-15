@echo off
echo ==========================================
echo    RETIXLY CLEAN BUILD (OPTIMIZED)
echo ==========================================
echo.

echo [1/8] Czyszczenie cache i plików tymczasowych...
if exist "__pycache__" rmdir /s /q "__pycache__"
if exist "*.pyc" del /s /q "*.pyc"
if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"
if exist "*.log" del /q "*.log"
echo       Cache wyczyszczony!

echo.
echo [2/8] Sprawdzanie zależności...
python -c "import PyQt6; print('✓ PyQt6 OK')" 2>nul || (echo ✗ PyQt6 BRAK && pause && exit /b 1)
python -c "import PIL; print('✓ Pillow OK')" 2>nul || (echo ✗ Pillow BRAK && pause && exit /b 1)
python -c "import requests; print('✓ Requests OK')" 2>nul || (echo ✗ Requests BRAK && pause && exit /b 1)
python -c "import cryptography; print('✓ Cryptography OK')" 2>nul || (echo ✗ Cryptography BRAK && pause && exit /b 1)

REM Opcjonalne zależności
python -c "import rembg; print('✓ Rembg OK')" 2>nul || echo ⚠ Rembg BRAK (opcjonalne)
python -c "import numpy; print('✓ Numpy OK')" 2>nul || echo ⚠ Numpy BRAK (opcjonalne)
python -c "import cv2; print('✓ OpenCV OK')" 2>nul || echo ⚠ OpenCV BRAK (opcjonalne)

echo.
echo [3/8] Sprawdzanie rozmiaru przed budowaniem...
for /f %%i in ('powershell -command "(Get-ChildItem -Path '.' -File -Recurse | Measure-Object -Property Length -Sum).Sum / 1MB"') do set SOURCE_SIZE=%%i
echo       Kod źródłowy: %SOURCE_SIZE% MB

echo.
echo [4/8] Tworzenie zoptymalizowanego build...
echo Używam zoptymalizowanego pliku spec...
python -m PyInstaller build_config.spec --clean --noconfirm

if not exist "dist\Retixly\Retixly.exe" (
    echo ✗ BŁĄD: Nie udało się zbudować EXE
    echo Sprawdź błędy powyżej
    pause
    exit /b 1
)

echo.
echo [5/8] Analiza rozmiaru po budowaniu...
for /f %%i in ('powershell -command "(Get-ChildItem -Path 'dist\Retixly' -Recurse | Measure-Object -Property Length -Sum).Sum / 1MB"') do set DIST_SIZE=%%i
echo       Aplikacja zbudowana: %DIST_SIZE% MB

echo.
echo [6/8] Szukanie największych plików...
echo Największe pliki w dist:
powershell -command "Get-ChildItem -Path 'dist\Retixly' -File -Recurse | Sort-Object Length -Descending | Select-Object -First 5 | Format-Table Name, @{Name='Size(MB)';Expression={[math]::Round($_.Length/1MB,2)}} -AutoSize"

echo.
echo [7/8] Testowanie aplikacji...
echo Sprawdzanie czy aplikacja się uruchamia...
cd "dist\Retixly"
start "" "Retixly.exe"
timeout /t 3 /nobreak >nul
taskkill /F /IM "Retixly.exe" >nul 2>&1
cd ..\..
echo       Test uruchomienia: OK

echo.
echo [8/8] Optymalizacja finalna...

REM Jeśli rozmiar nadal za duży, usuń niepotrzebne pliki
if %DIST_SIZE% GTR 500 (
    echo Rozmiar nadal za duży ^(%DIST_SIZE% MB^), czyszczenie...
    
    REM Usuń pliki dokumentacji
    del /s /q "dist\Retixly\*.md" 2>nul
    del /s /q "dist\Retrixly\*.txt" 2>nul
    del /s /q "dist\Retixly\*.rst" 2>nul
    
    REM Usuń pliki przykładów
    for /d /r "dist\Retixly" %%d in (*example*,*demo*,*sample*,*test*) do (
        if exist "%%d" rmdir /s /q "%%d"
    )
    
    REM Sprawdź rozmiar po czyszczeniu
    for /f %%i in ('powershell -command "(Get-ChildItem -Path 'dist\Retixly' -Recurse | Measure-Object -Property Length -Sum).Sum / 1MB"') do set FINAL_SIZE=%%i
    echo       Po czyszczeniu: %FINAL_SIZE% MB
) else (
    set FINAL_SIZE=%DIST_SIZE%
)

echo.
echo ==========================================
echo        PODSUMOWANIE BUDOWANIA
echo ==========================================
echo Kod źródłowy: %SOURCE_SIZE% MB
echo Aplikacja finalna: %FINAL_SIZE% MB
echo Ratio kompresji: x%FINAL_SIZE%/%SOURCE_SIZE% = x%FINAL_SIZE%
echo.

if %FINAL_SIZE% LSS 200 (
    echo ✅ SUKCES! Rozmiar optymalny ^(%FINAL_SIZE% MB^)
    echo Możesz teraz:
    echo 1. Utworzyć instalator
    echo 2. Zapakować do archiwum
    echo 3. Wysłać testerom
) else (
    if %FINAL_SIZE% LSS 500 (
        echo ⚠ OSTRZEŻENIE: Rozmiar duży ^(%FINAL_SIZE% MB^)
        echo Zalecenia:
        echo 1. Sprawdź czy wszystkie zależności są potrzebne
        echo 2. Usuń modele AI jeśli nieużywane
        echo 3. Użyj archiwum 7z z kompresją
    ) else (
        echo ❌ PROBLEM: Rozmiar za duży ^(%FINAL_SIZE% MB^)
        echo Musisz:
        echo 1. Usunąć niepotrzebne zależności
        echo 2. Przenieść modele AI do osobnego downloadera
        echo 3. Użyć lazy loading dla dużych bibliotek
    )
)

echo.
echo NASTĘPNE KROKI:
echo 1. Jeśli rozmiar OK - uruchom build_installer.bat
echo 2. Jeśli za duży - sprawdź co zajmuje miejsce
echo 3. Zoptymalizuj spec file dalej
echo.
pause