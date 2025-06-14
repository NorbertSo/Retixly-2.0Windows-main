!define APP_NAME "Retixly"
!define APP_VERSION "1.0.0"
!define APP_PUBLISHER "RetixlySoft"
!define APP_EXE "Retixly.exe"
!define APP_DESCRIPTION "AI-powered background removal tool"

# KLUCZOWE: Konfiguracja dla dużych plików
SetCompressor /SOLID lzma
SetCompressorDictSize 32
SetDatablockOptimize on
RequestExecutionLevel admin

!include "MUI2.nsh"

Name "${APP_NAME} ${APP_VERSION}"
OutFile "Retixly-${APP_VERSION}-Setup.exe"
InstallDir "$PROGRAMFILES\${APP_NAME}"

# Ikony instalatora
!define MUI_ICON "assets\icons\app_icon.ico"
!define MUI_UNICON "assets\icons\app_icon.ico"

# Strony instalatora z progress barem
!define MUI_INSTFILESPAGE_PROGRESSBAR smooth
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE "LICENSE"
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

# Strony deinstalatora
!insertmacro MUI_UNPAGE_WELCOME
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_UNPAGE_FINISH

# Język
!insertmacro MUI_LANGUAGE "English"

Section "Install" SEC01
    DetailPrint "Installing ${APP_NAME}..."
    DetailPrint "This may take several minutes due to large file size..."
    
    # Ustaw katalog docelowy
    SetOutPath "$INSTDIR"
    
    # WAŻNE: Kopiuj pliki wsadowo dla lepszej wydajności
    DetailPrint "Copying application files..."
    File /r "dist\Retixly\*"
    
    # Komunikat o postępie
    DetailPrint "Creating shortcuts..."
    
    # Utwórz skróty
    CreateDirectory "$SMPROGRAMS\${APP_NAME}"
    CreateShortCut "$SMPROGRAMS\${APP_NAME}\${APP_NAME}.lnk" "$INSTDIR\${APP_EXE}" "" "$INSTDIR\${APP_EXE}" 0
    CreateShortCut "$SMPROGRAMS\${APP_NAME}\Uninstall.lnk" "$INSTDIR\Uninstall.exe"
    CreateShortCut "$DESKTOP\${APP_NAME}.lnk" "$INSTDIR\${APP_EXE}" "" "$INSTDIR\${APP_EXE}" 0
    
    DetailPrint "Registering application..."
    
    # Wpisy w rejestrze Windows
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" "DisplayName" "${APP_NAME} ${APP_VERSION}"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" "UninstallString" "$INSTDIR\Uninstall.exe"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" "InstallLocation" "$INSTDIR"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" "DisplayVersion" "${APP_VERSION}"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" "Publisher" "${APP_PUBLISHER}"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" "DisplayIcon" "$INSTDIR\${APP_EXE}"
    WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" "NoModify" 1
    WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" "NoRepair" 1
    
    # Utwórz deinstalator
    WriteUninstaller "$INSTDIR\Uninstall.exe"
    
    DetailPrint "Installation completed successfully!"
    
    # Komunikat o zakończeniu
    MessageBox MB_OK "Installation completed successfully!$\n$\n${APP_NAME} ${APP_VERSION} has been installed.$\n$\nYou can find it in Start Menu or use the desktop shortcut.$\n$\nNote: First startup may take longer due to initialization."
SectionEnd

Section "Uninstall"
    DetailPrint "Uninstalling ${APP_NAME}..."
    
    # Zatrzymaj proces jeśli uruchomiony
    nsExec::Exec 'taskkill /F /IM "${APP_EXE}" /T'
    Sleep 1000
    
    # Usuń pliki aplikacji
    DetailPrint "Removing application files..."
    Delete "$INSTDIR\${APP_EXE}"
    Delete "$INSTDIR\Uninstall.exe"
    
    # Usuń foldery rekurencyjnie
    RMDir /r "$INSTDIR\_internal"
    RMDir /r "$INSTDIR\assets"
    RMDir /r "$INSTDIR\translations"
    RMDir /r "$INSTDIR\data"
    RMDir /r "$INSTDIR\logs"
    RMDir /r "$INSTDIR\temp"
    
    # Usuń pozostałe pliki
    Delete "$INSTDIR\*.*"
    RMDir "$INSTDIR"
    
    # Usuń skróty
    Delete "$SMPROGRAMS\${APP_NAME}\${APP_NAME}.lnk"
    Delete "$SMPROGRAMS\${APP_NAME}\Uninstall.lnk"
    RMDir "$SMPROGRAMS\${APP_NAME}"
    Delete "$DESKTOP\${APP_NAME}.lnk"
    
    # Usuń wpisy z rejestru
    DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}"
    
    # Komunikat o zakończeniu
    MessageBox MB_OK "${APP_NAME} has been successfully uninstalled."
SectionEnd