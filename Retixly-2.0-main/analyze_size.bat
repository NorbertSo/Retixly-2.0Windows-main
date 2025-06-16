@echo off
chcp 65001 >nul
echo ==========================================
echo      ANALIZA ROZMIARU RETIXLY
echo ==========================================
echo.

echo [1] Analiza folderu zrodlowego...
if exist "." (
    echo Folder główny:
    for /f %%i in ('powershell -command "(Get-ChildItem -Path '.' -File -Recurse | Measure-Object -Property Length -Sum).Sum / 1MB"') do set SOURCE_SIZE=%%i
    echo   Rozmiar: %SOURCE_SIZE% MB
    
    echo.
    echo Największe pliki w projekcie:
    powershell -command "Get-ChildItem -Path '.' -File -Recurse | Sort-Object Length -Descending | Select-Object -First 10 | Format-Table Name, @{Name='Size(MB)';Expression={[math]::Round($_.Length/1MB,2)}}, DirectoryName -AutoSize"
)

echo.
echo [2] Analiza folderu dist (jeśli istnieje)...
if exist "dist\Retixly" (
    echo Folder dist\Retixly:
    for /f %%i in ('powershell -command "(Get-ChildItem -Path 'dist\Retixly' -Recurse | Measure-Object -Property Length -Sum).Sum / 1MB"') do set DIST_SIZE=%%i
    echo   Rozmiar: %DIST_SIZE% MB
    
    echo.
    echo Największe pliki w dist:
    powershell -command "Get-ChildItem -Path 'dist\Retixly' -File -Recurse | Sort-Object Length -Descending | Select-Object -First 10 | Format-Table Name, @{Name='Size(MB)';Expression={[math]::Round($_.Length/1MB,2)}}, DirectoryName -AutoSize"
    
    echo.
    echo Analiza według typów plików:
    powershell -command "Get-ChildItem -Path 'dist\Retixly' -File -Recurse | Group-Object Extension | Sort-Object @{Expression={($_.Group | Measure-Object Length -Sum).Sum}} -Descending | Select-Object Name, Count, @{Name='TotalSize(MB)';Expression={[math]::Round(($_.Group | Measure-Object Length -Sum).Sum/1MB,2)}} | Format-Table -AutoSize"
) else (
    echo Folder dist nie istnieje - uruchom najpierw PyInstaller
)

echo.
echo [3] Sprawdzanie modeli AI...
if exist "dist\Retixly" (
    echo Szukam modeli rembg/onnx:
    powershell -command "Get-ChildItem -Path 'dist\Retixly' -Filter '*.onnx' -Recurse | Format-Table Name, @{Name='Size(MB)';Expression={[math]::Round($_.Length/1MB,2)}}, DirectoryName -AutoSize"
    
    echo.
    echo Szukam bibliotek ML:
    powershell -command "Get-ChildItem -Path 'dist\Retixly' -Filter '*torch*' -Recurse | Format-Table Name, @{Name='Size(MB)';Expression={[math]::Round($_.Length/1MB,2)}}, DirectoryName -AutoSize"
    powershell -command "Get-ChildItem -Path 'dist\Retixly' -Filter '*tensorflow*' -Recurse | Format-Table Name, @{Name='Size(MB)';Expression={[math]::Round($_.Length/1MB,2)}}, DirectoryName -AutoSize"
    powershell -command "Get-ChildItem -Path 'dist\Retixly' -Filter '*onnx*' -Recurse | Format-Table Name, @{Name='Size(MB)';Expression={[math]::Round($_.Length/1MB,2)}}, DirectoryName -AutoSize"
)

echo.
echo [4] Sprawdzanie plików tymczasowych...
if exist "build" (
    echo Folder build:
    for /f %%i in ('powershell -command "(Get-ChildItem -Path 'build' -Recurse | Measure-Object -Property Length -Sum).Sum / 1MB"') do set BUILD_SIZE=%%i
    echo   Rozmiar: %BUILD_SIZE% MB
)

if exist "__pycache__" (
    echo Pliki cache:
    for /f %%i in ('powershell -command "(Get-ChildItem -Path '__pycache__' -Recurse | Measure-Object -Property Length -Sum).Sum / 1MB"') do set CACHE_SIZE=%%i
    echo   Rozmiar: %CACHE_SIZE% MB
)

echo.
echo ==========================================
echo            PODSUMOWANIE
echo ==========================================
if defined SOURCE_SIZE echo Kod źródłowy: %SOURCE_SIZE% MB
if defined DIST_SIZE echo Aplikacja zbudowana: %DIST_SIZE% MB
if defined BUILD_SIZE echo Pliki budowania: %BUILD_SIZE% MB
if defined CACHE_SIZE echo Pliki cache: %CACHE_SIZE% MB
echo.
echo NASTĘPNE KROKI:
echo 1. Uruchom ten skrypt
echo 2. Sprawdź które pliki zajmują najwięcej miejsca
echo 3. Zoptymalizuj build_config.spec
echo 4. Usuń niepotrzebne zależności
echo.
pause