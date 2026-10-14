@echo off
setlocal enabledelayedexpansion

REM Shared start-up: sets ROOT and PY and checks the venv works on this PC (else: run setup.bat).
call "%~dp0_env.bat"
if errorlevel 1 (
    pause
    exit /b 1
)

REM =====================================================================
REM  vdo2srt - main launcher for the whole toolkit (vdo2srt / process_list
REM  / translate_srt).
REM
REM  Double-click ............ interactive menu below (options prompted one
REM                             at a time; blank = default or GUI picker).
REM  Command line ............ pass arguments directly to skip the menu
REM                             entirely and run vdo2srt.py as before, e.g.:
REM       vdo2srt.bat "E:\Movies\film.mkv" --engine local --language ru
REM =====================================================================

REM Command-line bypass: any arguments given -> run vdo2srt.py directly.
if not "%~1"=="" (
    "%PY%" "%ROOT%vdo2srt.py" %*
    exit /b %ERRORLEVEL%
)

:menu
echo.
echo ============================================================================
echo  vdo2srt toolkit
echo ============================================================================
echo  1) Convert video/audio to subtitles        (vdo2srt)
echo  2) Batch process a list of folders         (process_list)
echo  3) Translate existing SRT only              (translate_srt)
echo  4) Exit
echo ============================================================================
echo  Tip: pass arguments directly on the command line to skip this menu, e.g.
echo       vdo2srt.bat "E:\Movies\film.mkv" --engine local --language ru
echo ============================================================================
echo.

set "choice="
set /p choice="Enter your choice (1-4): "

if "!choice!"=="1" (
    call :run_vdo2srt
) else if "!choice!"=="2" (
    call :run_process_list
) else if "!choice!"=="3" (
    call :run_translate_srt
) else if "!choice!"=="4" (
    exit /b 0
) else (
    echo Invalid choice. Please try again.
)
goto menu

REM =====================================================================
:run_vdo2srt
echo.
echo --- vdo2srt: convert video/audio to subtitles ---
echo (press Enter on any prompt to accept the default / open a picker)
echo.

set "INPUT="
set /p INPUT="Video/audio file or folder [blank = picker]: "

set "ENGINE_ARG="
echo Engine:  1=Local GPU   2=Local CPU   3=Google Cloud   [blank = picker]
set "ENGINE_CHOICE="
set /p ENGINE_CHOICE="Choice: "
if "!ENGINE_CHOICE!"=="1" set "ENGINE_ARG=--engine local --device cuda"
if "!ENGINE_CHOICE!"=="2" set "ENGINE_ARG=--engine local --device cpu"
if "!ENGINE_CHOICE!"=="3" set "ENGINE_ARG=--engine cloud"

set "LANG="
set /p LANG="Source language code (e.g. ru, ja) [blank = auto-detect]: "
set "LANG_ARG="
if not "!LANG!"=="" set "LANG_ARG=--language !LANG!"

set "TRANSLATE=Y"
set /p TRANSLATE="Translate to another language? (Y/n) [Y]: "
set "TRANSLATE_ARG="
set "TARGETLANG_ARG="
if /i "!TRANSLATE!"=="n" (
    set "TRANSLATE_ARG=--no-translate"
) else (
    set "TARGET="
    set /p TARGET="Target language [en]: "
    if not "!TARGET!"=="" set "TARGETLANG_ARG=--target-language !TARGET!"
)

set "OVERWRITE=N"
set /p OVERWRITE="Re-transcribe/retranslate existing output? (y/N) [N]: "
set "OVERWRITE_ARG="
if /i "!OVERWRITE!"=="y" set "OVERWRITE_ARG=--overwrite"

set "INPUT_ARG="
if not "!INPUT!"=="" set "INPUT_ARG="!INPUT!""

echo.
echo Running vdo2srt.py !INPUT_ARG! !ENGINE_ARG! !LANG_ARG! !TRANSLATE_ARG! !TARGETLANG_ARG! !OVERWRITE_ARG!
echo.
"%PY%" "%ROOT%vdo2srt.py" !INPUT_ARG! !ENGINE_ARG! !LANG_ARG! !TRANSLATE_ARG! !TARGETLANG_ARG! !OVERWRITE_ARG!
echo.
echo Finished. Press any key to return to menu.
pause >nul
goto :eof

REM =====================================================================
:run_process_list
echo.
echo --- process_list: batch over folders listed in a text file ---
echo (press Enter on any prompt to accept the default / open a picker)
echo.

set "LISTFILE="
set /p LISTFILE="Folder-list .txt file [blank = picker]: "

set "ENGINE_ARG="
echo Engine:  1=Local GPU   2=Local CPU   3=Google Cloud   [blank = picker]
set "ENGINE_CHOICE="
set /p ENGINE_CHOICE="Choice: "
if "!ENGINE_CHOICE!"=="1" set "ENGINE_ARG=--engine local --device cuda"
if "!ENGINE_CHOICE!"=="2" set "ENGINE_ARG=--engine local --device cpu"
if "!ENGINE_CHOICE!"=="3" set "ENGINE_ARG=--engine cloud"

set "LANG="
set /p LANG="Source language code (e.g. ru, ja) [blank = auto-detect]: "
set "LANG_ARG="
if not "!LANG!"=="" set "LANG_ARG=--language !LANG!"

set "TRANSLATE=Y"
set /p TRANSLATE="Translate to another language? (Y/n) [Y]: "
set "TRANSLATE_ARG="
set "TARGETLANG_ARG="
if /i "!TRANSLATE!"=="n" (
    set "TRANSLATE_ARG=--no-translate"
) else (
    set "TARGET="
    set /p TARGET="Target language [en]: "
    if not "!TARGET!"=="" set "TARGETLANG_ARG=--target-language !TARGET!"
)

set "OVERWRITE=N"
set /p OVERWRITE="Re-transcribe/retranslate existing output? (y/N) [N]: "
set "OVERWRITE_ARG="
if /i "!OVERWRITE!"=="y" set "OVERWRITE_ARG=--overwrite"

set "LISTFILE_ARG="
if not "!LISTFILE!"=="" set "LISTFILE_ARG="!LISTFILE!""

echo.
echo Running process_list.py !LISTFILE_ARG! !ENGINE_ARG! !LANG_ARG! !TRANSLATE_ARG! !TARGETLANG_ARG! !OVERWRITE_ARG!
echo.
"%PY%" "%ROOT%process_list.py" !LISTFILE_ARG! !ENGINE_ARG! !LANG_ARG! !TRANSLATE_ARG! !TARGETLANG_ARG! !OVERWRITE_ARG!
echo.
echo Finished. Press any key to return to menu.
pause >nul
goto :eof

REM =====================================================================
:run_translate_srt
echo.
echo --- translate_srt: translate existing SRT files only ---
echo (press Enter on any prompt to accept the default / open a picker)
echo.

set "INPUT="
set /p INPUT="A .srt file, a folder, or a library root [blank = picker]: "

set "RECURSIVE=N"
set /p RECURSIVE="Recursive - treat input as a library root of movie folders? (y/N) [N]: "
set "RECURSIVE_ARG="
if /i "!RECURSIVE!"=="y" set "RECURSIVE_ARG=--recursive"

set "TARGET="
set /p TARGET="Target language [en]: "
set "TARGETLANG_ARG="
if not "!TARGET!"=="" set "TARGETLANG_ARG=--target-language !TARGET!"

set "OVERWRITE=N"
set /p OVERWRITE="Retranslate and replace existing translations? (y/N) [N]: "
set "OVERWRITE_ARG="
if /i "!OVERWRITE!"=="y" set "OVERWRITE_ARG=--overwrite"

set "INPUT_ARG="
if not "!INPUT!"=="" set "INPUT_ARG="!INPUT!""

echo.
echo Running translate_srt.py !INPUT_ARG! !RECURSIVE_ARG! !TARGETLANG_ARG! !OVERWRITE_ARG!
echo.
"%PY%" "%ROOT%translate_srt.py" !INPUT_ARG! !RECURSIVE_ARG! !TARGETLANG_ARG! !OVERWRITE_ARG!
echo.
echo Finished. Press any key to return to menu.
pause >nul
goto :eof
