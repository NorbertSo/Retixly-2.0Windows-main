@echo off
echo ==========================================
echo    SIMPLE FIX - KOPIUJ BOOTSTRAP DO EXE
echo ==========================================

echo [1/3] Sprawdzam lokalizacje...
echo Obecny folder: %cd%
if exist "bootstrap_ui.py" (
    echo ✅ bootstrap_ui.py znaleziony
) else (
    echo ❌ bootstrap_ui.py NIE ZNALEZIONY w %cd%
    echo Sprawdzam czy jesteśmy w odpowiednim folderze...
    dir bootstrap_ui.py 2>nul || (
        echo BŁĄD: Uruchom ten skrypt z głównego folderu projektu!
        pause && exit /b 1
    )
)

echo.
echo [2/3] Kopiuję bootstrap_ui.py do EXE...
if exist "dist\Retixly\" (
    copy "bootstrap_ui.py" "dist\Retixly\bootstrap_ui.py"
    echo ✅ Plik skopiowany
) else (
    echo ❌ Folder dist\Retixly nie istnieje!
    echo Zbuduj najpierw EXE: python -m PyInstaller Retixly.spec --clean
    pause && exit /b 1
)

echo.
echo [3/3] Test...
cd "dist\Retixly"
python -c "import bootstrap_ui; print('✅ Bootstrap found')" 2>nul && (
    echo ✅ Bootstrap działa!
    echo.
    echo 🚀 Uruchom teraz: .\Retixly.exe
    echo Bootstrap dialog powinien się pokazać!
) || (
    echo ❌ Bootstrap nadal nie działa
)

echo.
echo Naciśnij Enter aby uruchomić aplikację...
pause
.\Retixly.exe