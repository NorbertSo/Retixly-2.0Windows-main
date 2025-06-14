@echo off
echo ==========================================
echo    RETIXLY LARGE APP DISTRIBUTION
echo ==========================================
echo.

echo [1/5] Sprawdzanie czy EXE istnieje...
if not exist "dist\Retixly\Retixly.exe" (
    echo BLAD: Nie znaleziono aplikacji
    echo Uruchom najpierw: python -m PyInstaller build_config.spec
    pause
    exit /b 1
)
echo       Aplikacja znaleziona!

echo.
echo [2/5] Sprawdzanie rozmiaru...
for /f %%i in ('powershell -command "(Get-ChildItem -Path 'dist\Retixly' -Recurse | Measure-Object -Property Length -Sum).Sum / 1MB"') do set APP_SIZE_MB=%%i
echo       Rozmiar: %APP_SIZE_MB% MB

echo.
echo [3/5] Tworzenie archiwum 7Z z maksymalna kompresja...

REM Sprawdz czy jest 7-Zip
where 7z >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo BLAD: 7-Zip nie jest zainstalowany
    echo Pobierz z: https://www.7-zip.org/download.html
    echo.
    echo ALTERNATYWA: Tworzenie ZIP z PowerShell...
    powershell -command "Compress-Archive -Path 'dist\Retixly\*' -DestinationPath 'Retixly-1.0.0-Portable.zip' -CompressionLevel Optimal -Force"
    if exist "Retixly-1.0.0-Portable.zip" (
        echo ZIP utworzony!
        for /f %%i in ('powershell -command "(Get-Item 'Retixly-1.0.0-Portable.zip').Length / 1MB"') do set ZIP_SIZE=%%i
        echo Rozmiar ZIP: %ZIP_SIZE% MB
    )
    goto :INSTRUCTIONS
)

echo Tworzenie 7Z z maksymalna kompresja (moze potrwac kilka minut)...
7z a -t7z -mx=9 -mfb=273 -ms -md=31 "Retixly-1.0.0-Portable.7z" "dist\Retixly\*"

if exist "Retixly-1.0.0-Portable.7z" (
    echo       7Z utworzony pomyslnie!
    for /f %%i in ('powershell -command "(Get-Item 'Retixly-1.0.0-Portable.7z').Length / 1MB"') do set SEVEN_SIZE=%%i
    echo       Rozmiar 7Z: %SEVEN_SIZE% MB
) else (
    echo       Blad tworzenia 7Z
    goto :ERROR
)

echo.
echo [4/5] Tworzenie podzielonych archiwow dla email (25MB czesci)...
7z a -t7z -mx=9 -v25m "Retixly-1.0.0-Email.7z" "dist\Retixly\*"

echo.
echo [5/5] Tworzenie pliku README dla testerow...
echo Tworzenie instrukcji...

(
echo # Retixly v1.0.0 - Wersja Testowa
echo.
echo ## Instalacja ^(Wersja Portable^)
echo.
echo 1. Rozpakuj archiwum do dowolnego folderu
echo 2. Uruchom `Retixly.exe`
echo 3. Gotowe!
echo.
echo ## Wymagania
echo - Windows 10/11
echo - Brak dodatkowych instalacji
echo.
echo ## Funkcje testowe
echo - Usuwanie tla ze zdjec
echo - Przetwarzanie wsadowe
echo - System aktualizacji
echo - Interfejs w jezyku polskim/angielskim
echo.
echo ## Zgłaszanie błędów
echo Jesli znajdziesz blad, napisz email z:
echo - Opisem problemu
echo - Krokami do odtworzenia
echo - Zrzutem ekranu ^(jesli mozliwe^)
echo.
echo ## Uwagi
echo - To wersja testowa - moze zawierac bledy
echo - Aplikacja automatycznie sprawdza aktualizacje
echo - Nie wymaga instalacji - mozna uruchomic z dowolnego miejsca
echo.
echo Dziekuje za testowanie!
echo RetixlySoft Team
) > "README-TESTERZY.txt"

:INSTRUCTIONS
echo.
echo ==========================================
echo        GOTOWE! OPCJE DYSTRYBUCJI
echo ==========================================
echo.
if exist "Retixly-1.0.0-Portable.7z" (
    echo OPCJA 1: Upload na GitHub ^(Git LFS^)
    echo - Plik: Retixly-1.0.0-Portable.7z
    echo - Rozmiar: %SEVEN_SIZE% MB
    echo - Wymaga: git lfs install
    echo.
)

if exist "Retixly-1.0.0-Email.7z.001" (
    echo OPCJA 2: Wysylka emailem ^(podzielone archiwum^)
    echo - Pliki: Retixly-1.0.0-Email.7z.001, .002, etc.
    echo - Kazda czesc: max 25MB
    echo - Testerzy lacza: 7z x Retixly-1.0.0-Email.7z.001
    echo.
)

if exist "Retixly-1.0.0-Portable.zip" (
    echo OPCJA 3: ZIP dla prostoty
    echo - Plik: Retixly-1.0.0-Portable.zip  
    echo - Rozmiar: %ZIP_SIZE% MB
    echo - Uniwersalny format
    echo.
)

echo OPCJA 4: WeTransfer/Google Drive
echo - Upload calego archiwum
echo - Wyslij link do testerow
echo - Najprostsze rozwiazanie
echo.

echo ZALECENIE:
echo 1. WeTransfer ^(najprosciej^) - upload 7Z i wyslij link
echo 2. Google Drive - udostepnij folder z archiwum
echo 3. Email - jesli male grupy testerow
echo.

goto :END

:ERROR
echo.
echo ==========================================
echo                BLAD
echo ==========================================
echo Nie udalo sie utworzyc archiwum.
echo Sprawdz czy:
echo - Masz wystarczajaco miejsca na dysku
echo - Aplikacja nie jest uruchomiona
echo - Masz uprawnienia zapisu
echo.

:END
echo Pliki gotowe do dystrybucji!
echo Dolacz plik README-TESTERZY.txt do wysylki.
echo.
pause