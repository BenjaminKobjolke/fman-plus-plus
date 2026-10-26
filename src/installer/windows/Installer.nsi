!include MUI2.nsh
!include FileFunc.nsh
!include WordFunc.nsh
!include WinMessages.nsh
!insertmacro WordReplace
!insertmacro un.WordReplace
!define MUI_ICON "..\${app_name}\Icon.ico"
!define MUI_UNICON "..\${app_name}\Icon.ico"

!getdllversion "..\${app_name}\${app_name}.exe" ver
!define VERSION "${ver1}.${ver2}.${ver3}.${ver4}"

VIProductVersion "${VERSION}"
VIAddVersionKey "ProductName" "${display_name}"
VIAddVersionKey "FileVersion" "${VERSION}"
VIAddVersionKey "ProductVersion" "${VERSION}"
VIAddVersionKey "LegalCopyright" "(C) Michael Herrmann"
VIAddVersionKey "FileDescription" "${display_name}"

;--------------------------------
;Perform Machine-level install, if possible

!define MULTIUSER_EXECUTIONLEVEL Highest
;Add support for command-line args that let uninstaller know whether to
;uninstall machine- or user installation:
!define MULTIUSER_INSTALLMODE_COMMANDLINE
!include MultiUser.nsh
!include LogicLib.nsh

Function .onInit
  !insertmacro MULTIUSER_INIT
  ;Do not use InstallDir at all so we can detect empty $InstDir!
  ${If} $InstDir == "" ; /D not used
      ${If} $MultiUser.InstallMode == "AllUsers"
          StrCpy $InstDir "$PROGRAMFILES\${app_name}"
      ${Else}
          StrCpy $InstDir "$LOCALAPPDATA\${app_name}"
      ${EndIf}
  ${EndIf}
FunctionEnd

Function un.onInit
  !insertmacro MULTIUSER_UNINIT
FunctionEnd

; Build one copy for the installer and one for its separate uninstaller binary.
!macro DefineUpdateUserPath function
Function ${function}
  Exch $4
  Push $0
  Push $1
  Push $2
  Push $3
  Push $R0
  StrCpy $R0 $4

  ReadRegStr $0 HKCU "Environment" "Path"
  StrLen $1 "$0"
  IntOp $2 ${NSIS_MAX_STRLEN} - 100
  IntCmp $1 $2 path_too_long path_safe path_too_long

  path_safe:
    ; Remove the entry in all three positions so reinstall stays idempotent.
    !if "${function}" == "un.UpdateUserPath"
      ${un.WordReplace} "$0" ";$InstDir\bin" "" "+" $0
      ${un.WordReplace} "$0" "$InstDir\bin;" "" "+" $0
      ${un.WordReplace} "$0" "$InstDir\bin" "" "+" $0
    !else
      ${WordReplace} "$0" ";$InstDir\bin" "" "+" $0
      ${WordReplace} "$0" "$InstDir\bin;" "" "+" $0
      ${WordReplace} "$0" "$InstDir\bin" "" "+" $0
    !endif
    StrCmp $R0 "add" path_add path_write

  path_add:
    StrCmp $0 "" 0 +2
      StrCpy $0 "$InstDir\bin"
    StrCmp $0 "$InstDir\bin" path_write
    StrCpy $0 "$0;$InstDir\bin"

  path_write:
    WriteRegExpandStr HKCU "Environment" "Path" "$0"
    SendMessage ${HWND_BROADCAST} ${WM_SETTINGCHANGE} 0 "STR:Environment" /TIMEOUT=5000
    Goto path_done

  path_too_long:
    DetailPrint "User PATH is too long to update safely; fman command PATH entry was left unchanged."

  path_done:
  Pop $R0
  Pop $3
  Pop $2
  Pop $1
  Pop $0
  Pop $4
FunctionEnd
!macroend
!insertmacro DefineUpdateUserPath UpdateUserPath
!insertmacro DefineUpdateUserPath un.UpdateUserPath

;--------------------------------
;General

  Name "${display_name}"
  OutFile "..\${app_name}Setup.exe"

;--------------------------------
;Interface Settings

  !define MUI_ABORTWARNING

;--------------------------------
;Pages

  !define MUI_WELCOMEPAGE_TEXT "This wizard will guide you through the installation of ${display_name}.$\r$\n$\r$\n$\r$\nClick Next to continue."
  !insertmacro MUI_PAGE_WELCOME
  !insertmacro MUI_PAGE_DIRECTORY
  !insertmacro MUI_PAGE_INSTFILES
    !define MUI_FINISHPAGE_NOAUTOCLOSE
    !define MUI_FINISHPAGE_RUN
    !define MUI_FINISHPAGE_RUN_CHECKED
    !define MUI_FINISHPAGE_RUN_TEXT "Run ${display_name}"
    !define MUI_FINISHPAGE_RUN_FUNCTION "LaunchAsNonAdmin"
  !insertmacro MUI_PAGE_FINISH

  !insertmacro MUI_UNPAGE_CONFIRM
  !insertmacro MUI_UNPAGE_INSTFILES

;--------------------------------
;Languages

  !insertmacro MUI_LANGUAGE "English"

;--------------------------------
;Installer Sections

!define UNINST_KEY \
  "Software\Microsoft\Windows\CurrentVersion\Uninstall\${app_name}"
Section
  SetOutPath "$InstDir"
  File /r "..\${app_name}\*"
  WriteRegStr SHCTX "Software\${app_name}" "" $InstDir
  WriteUninstaller "$InstDir\uninstall.exe"
  Delete "$SMPROGRAMS\${app_name}.lnk"
  CreateShortCut "$SMPROGRAMS\${display_name}.lnk" "$InstDir\${app_name}.exe"
  WriteRegStr SHCTX "${UNINST_KEY}" "DisplayName" "${display_name}"
  WriteRegStr SHCTX "${UNINST_KEY}" "UninstallString" \
    "$\"$InstDir\uninstall.exe$\" /$MultiUser.InstallMode"
  WriteRegStr SHCTX "${UNINST_KEY}" "QuietUninstallString" \
    "$\"$InstDir\uninstall.exe$\" /$MultiUser.InstallMode /S"
  WriteRegStr SHCTX "${UNINST_KEY}" "Publisher" "Michael Herrmann"
  WriteRegStr SHCTX "${UNINST_KEY}" "DisplayIcon" "$InstDir\uninstall.exe"
  ${GetSize} "$InstDir" "/S=0K" $0 $1 $2
  IntFmt $0 "0x%08X" $0
  WriteRegDWORD SHCTX "${UNINST_KEY}" "EstimatedSize" "$0"
  Push "add"
  Call UpdateUserPath

SectionEnd

;--------------------------------
;Uninstaller Section

Section "Uninstall"

  Push "remove"
  Call un.UpdateUserPath
  RMDir /r "$InstDir"
  Delete "$SMPROGRAMS\${app_name}.lnk"
  Delete "$SMPROGRAMS\${display_name}.lnk"
  DeleteRegKey /ifempty SHCTX "Software\${app_name}"
  DeleteRegKey SHCTX "${UNINST_KEY}"

SectionEnd

Function LaunchAsNonAdmin
  Exec '"$WINDIR\explorer.exe" "$InstDir\${app_name}.exe"'
FunctionEnd
