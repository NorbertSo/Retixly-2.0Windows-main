!define APP_NAME "Retixly"
!define APP_VERSION "1.0.0"
!define APP_PUBLISHER "RetixlySoft"
!define APP_EXE "Retixly.exe"
!define APP_DESCRIPTION "AI-powered background removal tool"

!include "MUI2.nsh"

Name "${APP_NAME} ${APP_VERSION}"
OutFile "Retixly-${APP_VERSION}-Setup.exe"
InstallDir "$PROGRAMFILES\${APP_NAME}"
RequestExecutionLevel admin

# Ikony instalatora (jeśli masz)
!define MUI_ICON "assets\icons\app_icon.ico"
!define MUI_UNICON "assets\icons\app_icon.ico"

# Strony instalatora
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

Section "Install"
    # Kopiuj pliki aplikacji
    SetOutPath "$INSTDIR"
    File /r "dist\Retixly\*"
    
    # Utwórz skróty
    CreateDirectory "$SMPROGRAMS\${APP_NAME}"
    CreateShortCut "$SMPROGRAMS\${APP_NAME}\${APP_NAME}.lnk" "$INSTDIR\${APP_EXE}" "" "$INSTDIR\${APP_EXE}" 0
    CreateShortCut "$SMPROGRAMS\${APP_NAME}\Uninstall.lnk" "$INSTDIR\Uninstall.exe"
    CreateShortCut "$DESKTOP\${APP_NAME}.lnk" "$INSTDIR\${APP_EXE}" "" "$INSTDIR\${APP_EXE}" 0
    
    # Wpisy w rejestrze Windows (dla "Dodaj/Usuń programy")
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
    
    # Komunikat o pomyślnej instalacji
    MessageBox MB_OK "Installation completed successfully!$\n$\n${APP_NAME} ${APP_VERSION} has been installed.$\n$\nYou can find it in Start Menu or use the desktop shortcut."
SectionEnd

Section "Uninstall"
    # Usuń pliki aplikacji
    Delete "$INSTDIR\${APP_EXE}"
    Delete "$INSTDIR\Uninstall.exe"
    RMDir /r "$INSTDIR\_internal"
    RMDir /r "$INSTDIR\assets"
    RMDir /r "$INSTDIR\translations"
    RMDir /r "$INSTDIR\data"
    RMDir /r "$INSTDIR\logs"
    RMDir /r "$INSTDIR\temp"
    Delete "$INSTDIR\*.*"
    RMDir "$INSTDIR"
    
    # Usuń skróty
    Delete "$SMPROGRAMS\${APP_NAME}\${APP_NAME}.lnk"
    Delete "$SMPROGRAMS\${APP_NAME}\Uninstall.lnk"
    RMDir "$SMPROGRAMS\${APP_NAME}"
    Delete "$DESKTOP\${APP_NAME}.lnk"
    
    # Usuń wpisy z rejestru
    DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}"
    
    # Komunikat o pomyślnej deinstalacji
    MessageBox MB_OK "${APP_NAME} has been successfully uninstalled."
SectionEnd