; TagLab installer for Windows 10/11 (NSIS 3).
;
; Installs per user into %LOCALAPPDATA%\Programs\TagLab: no administrator
; rights are needed, and the folder stays writable for TagLab itself
; (downloaded networks, config.json, TagLab.log).
;
; Layout:
;   python\                 embedded CPython 3.11 + every package TagLab needs
;   app\                    TagLab source tree
;   wheels\                 pip, GDAL and rasterio wheels used during setup
;   logs\                   install.log, launcher.log
;   taglab_launcher.py      starts TagLab (see the notes in that file)
;   setup_env.py            installs packages and networks, run once by this installer
;
; Build with build.py, which prepares the payload directory and passes
; APPVERSION and PAYLOAD.

Unicode true
ManifestDPIAware true
RequestExecutionLevel user
SetCompressor /SOLID lzma

!ifndef APPVERSION
  !error "Define APPVERSION, e.g. makensis /DAPPVERSION=2026.4.1 (build.py does this)"
!endif
!ifndef PAYLOAD
  !error "Define PAYLOAD, the directory prepared by build.py"
!endif
!ifndef OUTFILE
  !define OUTFILE "TagLab-${APPVERSION}-setup.exe"
!endif

!define APPNAME "TagLab"
!define PUBLISHER "CNR-ISTI Visual Computing Lab"
!define HOMEPAGE "https://github.com/cnr-isti-vclab/TagLab"
!define UNINSTKEY "Software\Microsoft\Windows\CurrentVersion\Uninstall\TagLab"
!define SETTINGSKEY "Software\TagLab Installer"
; QSettings("VCLAB", "TagLab") keeps TagLab's preferences here
!define QSETTINGSKEY "Software\VCLAB\TagLab"

!include "MUI2.nsh"
!include "LogicLib.nsh"
!include "x64.nsh"
!include "WinVer.nsh"
!include "FileFunc.nsh"
!include "nsDialogs.nsh"

Name "${APPNAME} ${APPVERSION}"
OutFile "${OUTFILE}"
InstallDir "$LOCALAPPDATA\Programs\TagLab"
InstallDirRegKey HKCU "${SETTINGSKEY}" "InstallDir"
BrandingText "${APPNAME} ${APPVERSION}"
ShowInstDetails show
ShowUninstDetails show

Var TorchChoice      ; auto | cpu | cu118 | cu121 | cu124
Var InstallSam       ; 1 when the SAM component is selected
Var CreateDesktop    ; 1 when the desktop shortcut component is selected
Var GpuName
Var RadioAuto
Var RadioCpu
Var RadioCu124
Var RadioCu121
Var RadioCu118

!define MUI_ICON "${PAYLOAD}\taglab.ico"
!define MUI_UNICON "${PAYLOAD}\taglab.ico"
!define MUI_ABORTWARNING
!define MUI_COMPONENTSPAGE_SMALLDESC
!define MUI_FINISHPAGE_RUN
!define MUI_FINISHPAGE_RUN_FUNCTION LaunchTagLab

!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE "${PAYLOAD}\app\LICENSE"
!insertmacro MUI_PAGE_COMPONENTS
Page custom TorchPageCreate TorchPageLeave
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

!insertmacro MUI_LANGUAGE "Italian"
!insertmacro MUI_LANGUAGE "English"

; ---------------------------------------------------------------- strings

LangString SEC_CORE ${LANG_ITALIAN} "TagLab"
LangString SEC_CORE ${LANG_ENGLISH} "TagLab"
LangString DESC_CORE ${LANG_ITALIAN} "Programma, Python 3.11, librerie e reti neurali di base (circa 3,5 GB, scaricati durante l'installazione)."
LangString DESC_CORE ${LANG_ENGLISH} "Program, Python 3.11, libraries and core neural networks (about 3.5 GB, downloaded during setup)."
LangString SEC_SAM ${LANG_ITALIAN} "Modello SAM (2,6 GB)"
LangString SEC_SAM ${LANG_ENGLISH} "SAM model (2.6 GB)"
LangString DESC_SAM ${LANG_ITALIAN} "Segment Anything, usato dagli strumenti di segmentazione SAM. Grande download."
LangString DESC_SAM ${LANG_ENGLISH} "Segment Anything, used by the SAM segmentation tools. Large download."
LangString SEC_SAMPLES ${LANG_ITALIAN} "Progetti di esempio (127 MB)"
LangString SEC_SAMPLES ${LANG_ENGLISH} "Sample projects (127 MB)"
LangString DESC_SAMPLES ${LANG_ITALIAN} "Progetti dimostrativi da aprire con File > Apri progetto."
LangString DESC_SAMPLES ${LANG_ENGLISH} "Demo projects to open with File > Open project."
LangString SEC_DESKTOP ${LANG_ITALIAN} "Collegamento sul desktop"
LangString SEC_DESKTOP ${LANG_ENGLISH} "Desktop shortcut"
LangString DESC_DESKTOP ${LANG_ITALIAN} "Crea un collegamento a TagLab sul desktop."
LangString DESC_DESKTOP ${LANG_ENGLISH} "Create a TagLab shortcut on the desktop."

LangString TORCH_TITLE ${LANG_ITALIAN} "Accelerazione grafica"
LangString TORCH_TITLE ${LANG_ENGLISH} "Graphics acceleration"
LangString TORCH_SUBTITLE ${LANG_ITALIAN} "Scegli la versione di PyTorch usata dalle reti neurali."
LangString TORCH_SUBTITLE ${LANG_ENGLISH} "Choose the PyTorch build used by the neural networks."
LangString TORCH_GPU_FOUND ${LANG_ITALIAN} "Scheda NVIDIA rilevata:"
LangString TORCH_GPU_FOUND ${LANG_ENGLISH} "NVIDIA card detected:"
LangString TORCH_NO_GPU ${LANG_ITALIAN} "Nessuna scheda NVIDIA rilevata: la scelta automatica userà la CPU."
LangString TORCH_NO_GPU ${LANG_ENGLISH} "No NVIDIA card detected: the automatic choice will use the CPU."
LangString TORCH_AUTO ${LANG_ITALIAN} "Automatica (consigliata): CUDA se il driver NVIDIA lo supporta, altrimenti CPU"
LangString TORCH_AUTO ${LANG_ENGLISH} "Automatic (recommended): CUDA if the NVIDIA driver supports it, otherwise CPU"
LangString TORCH_CPU ${LANG_ITALIAN} "Solo CPU (circa 200 MB, funziona ovunque ma più lenta)"
LangString TORCH_CPU ${LANG_ENGLISH} "CPU only (about 200 MB, works everywhere but slower)"
LangString TORCH_CU124 ${LANG_ITALIAN} "NVIDIA CUDA 12.4 (circa 2,5 GB, driver recenti)"
LangString TORCH_CU124 ${LANG_ENGLISH} "NVIDIA CUDA 12.4 (about 2.5 GB, recent drivers)"
LangString TORCH_CU121 ${LANG_ITALIAN} "NVIDIA CUDA 12.1 (circa 2,5 GB)"
LangString TORCH_CU121 ${LANG_ENGLISH} "NVIDIA CUDA 12.1 (about 2.5 GB)"
LangString TORCH_CU118 ${LANG_ITALIAN} "NVIDIA CUDA 11.8 (circa 2,5 GB, driver meno recenti)"
LangString TORCH_CU118 ${LANG_ENGLISH} "NVIDIA CUDA 11.8 (about 2.5 GB, older drivers)"

LangString MSG_NEEDS_X64 ${LANG_ITALIAN} "TagLab richiede Windows a 64 bit."
LangString MSG_NEEDS_X64 ${LANG_ENGLISH} "TagLab requires 64-bit Windows."
LangString MSG_NEEDS_WIN10 ${LANG_ITALIAN} "TagLab richiede Windows 10 o Windows 11."
LangString MSG_NEEDS_WIN10 ${LANG_ENGLISH} "TagLab requires Windows 10 or Windows 11."
LangString MSG_UPGRADE ${LANG_ITALIAN} "TagLab è già installato: verrà aggiornato. Le reti neurali già scaricate vengono mantenute."
LangString MSG_UPGRADE ${LANG_ENGLISH} "TagLab is already installed and will be updated. Networks already downloaded are kept."
LangString MSG_RUNNING ${LANG_ITALIAN} "TagLab è in esecuzione. Chiudilo e riprova."
LangString MSG_RUNNING ${LANG_ENGLISH} "TagLab is running. Close it and try again."
LangString MSG_SETUP_FAILED ${LANG_ITALIAN} "L'installazione delle librerie non è riuscita (serve una connessione a Internet).$\r$\n$\r$\nDettagli in:$\r$\n$INSTDIR\logs\install.log$\r$\n$\r$\nPuoi riprovare rilanciando l'installer."
LangString MSG_SETUP_FAILED ${LANG_ENGLISH} "Installing the libraries failed (an Internet connection is required).$\r$\n$\r$\nDetails in:$\r$\n$INSTDIR\logs\install.log$\r$\n$\r$\nYou can retry by running the installer again."
LangString MSG_LEFTOVERS ${LANG_ITALIAN} "Alcuni file non installati da TagLab (per esempio progetti salvati nella cartella del programma) sono stati lasciati in:$\r$\n$INSTDIR"
LangString MSG_LEFTOVERS ${LANG_ENGLISH} "Some files that were not installed by TagLab (for example projects saved in the program folder) were left in:$\r$\n$INSTDIR"
LangString LNK_CONSOLE ${LANG_ITALIAN} "TagLab (con console)"
LangString LNK_CONSOLE ${LANG_ENGLISH} "TagLab (with console)"
LangString LNK_UNINSTALL ${LANG_ITALIAN} "Disinstalla TagLab"
LangString LNK_UNINSTALL ${LANG_ENGLISH} "Uninstall TagLab"

; ---------------------------------------------------------------- helpers

; A file in python\ is locked while TagLab runs; renaming the folder fails then.
!macro CheckNotRunning UN
  Function ${UN}CheckNotRunning
    ${If} ${FileExists} "$INSTDIR\python\*.*"
      ClearErrors
      Rename "$INSTDIR\python" "$INSTDIR\python.lockcheck"
      ${If} ${Errors}
        MessageBox MB_ICONEXCLAMATION "$(MSG_RUNNING)" /SD IDOK
        Abort
      ${EndIf}
      Rename "$INSTDIR\python.lockcheck" "$INSTDIR\python"
    ${EndIf}
  FunctionEnd
!macroend
!insertmacro CheckNotRunning ""
!insertmacro CheckNotRunning "un."

Function .onInit
  ${IfNot} ${RunningX64}
    MessageBox MB_ICONSTOP "$(MSG_NEEDS_X64)" /SD IDOK
    Abort
  ${EndIf}
  ${IfNot} ${AtLeastWin10}
    MessageBox MB_ICONSTOP "$(MSG_NEEDS_WIN10)" /SD IDOK
    Abort
  ${EndIf}
  SetRegView 64

  StrCpy $TorchChoice "auto"
  StrCpy $InstallSam "0"
  StrCpy $CreateDesktop "0"

  ; silent installs: TagLab-setup.exe /S /TORCH=cpu (or /CPU)
  ${GetParameters} $R0
  ClearErrors
  ${GetOptions} $R0 "/TORCH=" $R1
  ${IfNot} ${Errors}
    StrCpy $TorchChoice $R1
  ${EndIf}
  ClearErrors
  ${GetOptions} $R0 "/CPU" $R1
  ${IfNot} ${Errors}
    StrCpy $TorchChoice "cpu"
  ${EndIf}

  ; an existing installation is updated in place
  ReadRegStr $R2 HKCU "${UNINSTKEY}" "InstallLocation"
  ${If} $R2 != ""
  ${AndIf} ${FileExists} "$R2\taglab_launcher.py"
    StrCpy $INSTDIR $R2
    MessageBox MB_ICONINFORMATION "$(MSG_UPGRADE)" /SD IDOK
  ${EndIf}
FunctionEnd

Function .onVerifyInstDir
  ; long paths under python\Lib\site-packages (torch) can exceed MAX_PATH
  StrLen $R0 $INSTDIR
  ${If} $R0 > 80
    Abort
  ${EndIf}
FunctionEnd

Function TorchPageCreate
  !insertmacro MUI_HEADER_TEXT "$(TORCH_TITLE)" "$(TORCH_SUBTITLE)"
  nsDialogs::Create 1018
  Pop $0
  ${If} $0 == error
    Abort
  ${EndIf}

  nsExec::ExecToStack 'nvidia-smi --query-gpu=name --format=csv,noheader'
  Pop $1
  Pop $GpuName
  ${If} $1 == "0"
    ${NSD_CreateLabel} 0 0 100% 12u "$(TORCH_GPU_FOUND) $GpuName"
  ${Else}
    ${NSD_CreateLabel} 0 0 100% 12u "$(TORCH_NO_GPU)"
  ${EndIf}
  Pop $0

  ${NSD_CreateRadioButton} 0 22u 100% 12u "$(TORCH_AUTO)"
  Pop $RadioAuto
  ${NSD_CreateRadioButton} 0 38u 100% 12u "$(TORCH_CPU)"
  Pop $RadioCpu
  ${NSD_CreateRadioButton} 0 54u 100% 12u "$(TORCH_CU124)"
  Pop $RadioCu124
  ${NSD_CreateRadioButton} 0 70u 100% 12u "$(TORCH_CU121)"
  Pop $RadioCu121
  ${NSD_CreateRadioButton} 0 86u 100% 12u "$(TORCH_CU118)"
  Pop $RadioCu118

  ${Select} $TorchChoice
    ${Case} "cpu"
      ${NSD_Check} $RadioCpu
    ${Case} "cu124"
      ${NSD_Check} $RadioCu124
    ${Case} "cu121"
      ${NSD_Check} $RadioCu121
    ${Case} "cu118"
      ${NSD_Check} $RadioCu118
    ${CaseElse}
      ${NSD_Check} $RadioAuto
  ${EndSelect}

  nsDialogs::Show
FunctionEnd

Function TorchPageLeave
  StrCpy $TorchChoice "auto"
  ${NSD_GetState} $RadioCpu $0
  ${If} $0 == ${BST_CHECKED}
    StrCpy $TorchChoice "cpu"
  ${EndIf}
  ${NSD_GetState} $RadioCu124 $0
  ${If} $0 == ${BST_CHECKED}
    StrCpy $TorchChoice "cu124"
  ${EndIf}
  ${NSD_GetState} $RadioCu121 $0
  ${If} $0 == ${BST_CHECKED}
    StrCpy $TorchChoice "cu121"
  ${EndIf}
  ${NSD_GetState} $RadioCu118 $0
  ${If} $0 == ${BST_CHECKED}
    StrCpy $TorchChoice "cu118"
  ${EndIf}
FunctionEnd

Function LaunchTagLab
  SetOutPath "$INSTDIR\app"
  Exec '"$INSTDIR\python\pythonw.exe" "$INSTDIR\taglab_launcher.py"'
FunctionEnd

; ---------------------------------------------------------------- sections

Section "!$(SEC_CORE)" SecCore
  SectionIn RO
  ; packages and networks downloaded by setup_env.py (CPU build of PyTorch)
  AddSize 3300000

  Call CheckNotRunning

  ; the Python environment is always rebuilt from scratch
  RMDir /r "$INSTDIR\python"
  RMDir /r "$INSTDIR\wheels"

  SetOutPath "$INSTDIR"
  File /r "${PAYLOAD}\python"
  File /r "${PAYLOAD}\wheels"
  File /r "${PAYLOAD}\app"
  File "${PAYLOAD}\taglab_launcher.py"
  File "${PAYLOAD}\setup_env.py"
  File "${PAYLOAD}\requirements-lock.txt"
  File "${PAYLOAD}\taglab.ico"
  File "${PAYLOAD}\BUILD_INFO.txt"
  ; SHA-256 of the networks, when build.py was given them
  File /nonfatal "${PAYLOAD}\models.sha256"
  CreateDirectory "$INSTDIR\logs"

  ; registered before the long setup step, so a failed setup can be uninstalled
  WriteUninstaller "$INSTDIR\Uninstall.exe"
  WriteRegStr HKCU "${SETTINGSKEY}" "InstallDir" "$INSTDIR"
  WriteRegStr HKCU "${UNINSTKEY}" "DisplayName" "${APPNAME}"
  WriteRegStr HKCU "${UNINSTKEY}" "DisplayVersion" "${APPVERSION}"
  WriteRegStr HKCU "${UNINSTKEY}" "Publisher" "${PUBLISHER}"
  WriteRegStr HKCU "${UNINSTKEY}" "URLInfoAbout" "${HOMEPAGE}"
  WriteRegStr HKCU "${UNINSTKEY}" "DisplayIcon" "$INSTDIR\taglab.ico"
  WriteRegStr HKCU "${UNINSTKEY}" "InstallLocation" "$INSTDIR"
  WriteRegStr HKCU "${UNINSTKEY}" "UninstallString" '"$INSTDIR\Uninstall.exe"'
  WriteRegStr HKCU "${UNINSTKEY}" "QuietUninstallString" '"$INSTDIR\Uninstall.exe" /S'
  WriteRegDWORD HKCU "${UNINSTKEY}" "NoModify" 1
  WriteRegDWORD HKCU "${UNINSTKEY}" "NoRepair" 1
SectionEnd

Section "$(SEC_SAM)" SecSam
  AddSize 2505000
  StrCpy $InstallSam "1"
SectionEnd

Section /o "$(SEC_SAMPLES)" SecSamples
  SetOutPath "$INSTDIR\app"
  File /r "${PAYLOAD}\samples\sampleProjects"
SectionEnd

Section "$(SEC_DESKTOP)" SecDesktop
  StrCpy $CreateDesktop "1"
SectionEnd

; runs last, after the optional sections have set their flags
Section "-Setup" SecSetup
  StrCpy $0 ""
  ${If} $InstallSam == "1"
    StrCpy $0 "--sam"
  ${EndIf}
  DetailPrint "python setup_env.py --torch $TorchChoice $0"
  nsExec::ExecToLog '"$INSTDIR\python\python.exe" -u "$INSTDIR\setup_env.py" --torch $TorchChoice $0 --log "$INSTDIR\logs\install.log"'
  Pop $1
  ${If} $1 != "0"
    DetailPrint "setup_env.py failed: $1"
    MessageBox MB_ICONSTOP "$(MSG_SETUP_FAILED)" /SD IDOK
    Abort
  ${EndIf}

  ; the working directory of the shortcuts is app\ (TagLab resolves some paths from it)
  SetOutPath "$INSTDIR\app"
  CreateDirectory "$SMPROGRAMS\TagLab"
  CreateShortCut "$SMPROGRAMS\TagLab\TagLab.lnk" "$INSTDIR\python\pythonw.exe" '"$INSTDIR\taglab_launcher.py"' "$INSTDIR\taglab.ico" 0
  CreateShortCut "$SMPROGRAMS\TagLab\$(LNK_CONSOLE).lnk" "$INSTDIR\python\python.exe" '"$INSTDIR\taglab_launcher.py"' "$INSTDIR\taglab.ico" 0
  CreateShortCut "$SMPROGRAMS\TagLab\$(LNK_UNINSTALL).lnk" "$INSTDIR\Uninstall.exe"
  ${If} $CreateDesktop == "1"
    CreateShortCut "$DESKTOP\TagLab.lnk" "$INSTDIR\python\pythonw.exe" '"$INSTDIR\taglab_launcher.py"' "$INSTDIR\taglab.ico" 0
  ${EndIf}

  ; Size in KB for "Installed apps". Not ${GetSize}: it adds file sizes in
  ; 32-bit integers, so it skips the 2.6 GB SAM network, and it takes minutes
  ; to walk the tens of thousands of files in site-packages.
  nsExec::ExecToStack '"$INSTDIR\python\python.exe" -c "import os, sys; print(sum(os.path.getsize(os.path.join(d, f)) for d, _, fs in os.walk(sys.argv[1]) for f in fs) // 1024)" "$INSTDIR"'
  Pop $2
  Pop $3
  ${If} $2 == "0"
    IntOp $3 $3 + 0
    IntFmt $3 "0x%08X" $3
    WriteRegDWORD HKCU "${UNINSTKEY}" "EstimatedSize" $3
  ${EndIf}
SectionEnd

!insertmacro MUI_FUNCTION_DESCRIPTION_BEGIN
  !insertmacro MUI_DESCRIPTION_TEXT ${SecCore} "$(DESC_CORE)"
  !insertmacro MUI_DESCRIPTION_TEXT ${SecSam} "$(DESC_SAM)"
  !insertmacro MUI_DESCRIPTION_TEXT ${SecSamples} "$(DESC_SAMPLES)"
  !insertmacro MUI_DESCRIPTION_TEXT ${SecDesktop} "$(DESC_DESKTOP)"
!insertmacro MUI_FUNCTION_DESCRIPTION_END

; ---------------------------------------------------------------- uninstall

Function un.onInit
  SetRegView 64
FunctionEnd

Section "Uninstall"
  Call un.CheckNotRunning

  Delete "$DESKTOP\TagLab.lnk"
  ; shortcut names depend on the install language, so remove them all
  Delete "$SMPROGRAMS\TagLab\*.lnk"
  RMDir "$SMPROGRAMS\TagLab"

  ; created entirely by the installer
  RMDir /r "$INSTDIR\python"
  RMDir /r "$INSTDIR\wheels"
  RMDir /r "$INSTDIR\logs"
  Delete "$INSTDIR\taglab_launcher.py"
  Delete "$INSTDIR\setup_env.py"
  Delete "$INSTDIR\requirements-lock.txt"
  Delete "$INSTDIR\taglab.ico"
  Delete "$INSTDIR\BUILD_INFO.txt"
  Delete "$INSTDIR\models.sha256"

  ; app\: only the files that were installed or generated (networks, logs,
  ; __pycache__), never a blanket RMDir /r, so projects a user saved in
  ; the program folder survive. Generated by build.py.
  !include "${PAYLOAD}\uninstall_app.nsh"

  Delete "$INSTDIR\Uninstall.exe"
  RMDir "$INSTDIR"
  ${If} ${FileExists} "$INSTDIR\*.*"
    MessageBox MB_ICONINFORMATION "$(MSG_LEFTOVERS)" /SD IDOK
  ${EndIf}

  DeleteRegKey HKCU "${QSETTINGSKEY}"
  DeleteRegKey /ifempty HKCU "Software\VCLAB"
  DeleteRegKey HKCU "${UNINSTKEY}"
  DeleteRegKey HKCU "${SETTINGSKEY}"
SectionEnd
