!include "MUI2.nsh"

Name "Retixly"
OutFile "Retixly-1.0.0-Setup.exe"
InstallDir "$PROGRAMFILES64\Retixly"
RequestExecutionLevel admin

!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

!insertmacro MUI_LANGUAGE "English"

Section "MainSection" SEC01
    SetOutPath "$INSTDIR"
    File /r "dist\Retixly\*.*"
    
    CreateDirectory "$SMPROGRAMS\Retixly"
    CreateShortCut "$SMPROGRAMS\Retixly\Retixly.lnk" "$INSTDIR\Retixly.exe"
    CreateShortCut "$DESKTOP\Retixly.lnk" "$INSTDIR\Retixly.exe"
    
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Retixly" "DisplayName" "Retixly"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Retixly" "UninstallString" "$INSTDIR\uninstall.exe"
    WriteUninstaller "$INSTDIR\uninstall.exe"
SectionEnd

Section "Uninstall"
    Delete "$INSTDIR\*.*"
    RMDir /r "$INSTDIR"
    Delete "$SMPROGRAMS\Retixly\*.*"
    RMDir "$SMPROGRAMS\Retixly"
    Delete "$DESKTOP\Retixly.lnk"
    DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Retixly"
SectionEnd
