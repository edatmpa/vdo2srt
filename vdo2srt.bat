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
call :banner "vdo2srt: convert video/audio to subtitles"
call :ask_path "Video/audio file or folder [blank = picker]: "
call :ask_engine
call :ask_source_lang
call :ask_translate
call :ask_yes OVERWRITE_ARG --overwrite "Re-transcribe/retranslate existing output? (y/N) [N]: "
set "ARGS=!PATH_ARG! !ENGINE_ARG! !SRCLANG_ARG! !TRANSLATE_ARG! !TARGETLANG_ARG! !OVERWRITE_ARG!"
call :run vdo2srt.py
goto :eof

REM =====================================================================
:run_process_list
call :banner "process_list: batch over folders listed in a text file"
call :ask_path "Folder-list .txt file [blank = picker]: "
call :ask_engine
call :ask_source_lang
call :ask_translate
call :ask_yes OVERWRITE_ARG --overwrite "Re-transcribe/retranslate existing output? (y/N) [N]: "
set "ARGS=!PATH_ARG! !ENGINE_ARG! !SRCLANG_ARG! !TRANSLATE_ARG! !TARGETLANG_ARG! !OVERWRITE_ARG!"
call :run process_list.py
goto :eof

REM =====================================================================
:run_translate_srt
call :banner "translate_srt: translate existing SRT files only"
call :ask_path "A .srt file, a folder, or a library root [blank = picker]: "
call :ask_yes RECURSIVE_ARG --recursive "Recursive - treat input as a library root of movie folders? (y/N) [N]: "
call :ask_target_lang
call :ask_yes OVERWRITE_ARG --overwrite "Retranslate and replace existing translations? (y/N) [N]: "
set "ARGS=!PATH_ARG! !RECURSIVE_ARG! !TARGETLANG_ARG! !OVERWRITE_ARG!"
call :run translate_srt.py
goto :eof

REM =====================================================================
REM  Shared prompts. Each one sets a *_ARG variable (empty = use default).
REM =====================================================================

:banner
echo.
echo --- %~1 ---
echo (press Enter on any prompt to accept the default / open a picker)
echo.
goto :eof

REM Path prompt -> PATH_ARG. Strips any quotes the user typed or pasted
REM (Explorer "Copy as path", drag-and-drop) before re-quoting once, so a
REM quoted path with spaces is not split into several arguments.
:ask_path
set "PATH_ARG="
set "_IN="
set /p _IN="%~1"
if defined _IN set "_IN=!_IN:"=!"
if defined _IN set "PATH_ARG="!_IN!""
goto :eof

:ask_engine
set "ENGINE_ARG="
echo Engine:  1=Local GPU   2=Local CPU   3=Google Cloud   [blank = picker]
set "_IN="
set /p _IN="Choice: "
if "!_IN!"=="1" set "ENGINE_ARG=--engine local --device cuda"
if "!_IN!"=="2" set "ENGINE_ARG=--engine local --device cpu"
if "!_IN!"=="3" set "ENGINE_ARG=--engine cloud"
goto :eof

:ask_source_lang
set "SRCLANG_ARG="
set "_IN="
set /p _IN="Source language code (e.g. ru, ja) [blank = auto-detect]: "
if defined _IN set "SRCLANG_ARG=--language !_IN!"
goto :eof

:ask_target_lang
set "TARGETLANG_ARG="
set "_IN="
set /p _IN="Target language [en]: "
if defined _IN set "TARGETLANG_ARG=--target-language !_IN!"
goto :eof

REM Translate? (default yes) -> TRANSLATE_ARG, plus TARGETLANG_ARG when yes.
:ask_translate
set "TRANSLATE_ARG="
set "TARGETLANG_ARG="
set "_IN="
set /p _IN="Translate to another language? (Y/n) [Y]: "
if /i "!_IN!"=="n" (
    set "TRANSLATE_ARG=--no-translate"
) else (
    call :ask_target_lang
)
goto :eof

REM Yes/no (default no): ask_yes VAR --flag "prompt" -> VAR=--flag on y.
:ask_yes
set "%~1="
set "_IN="
set /p _IN="%~3"
if /i "!_IN!"=="y" set "%~1=%~2"
goto :eof

REM Runs a root script with ARGS, then waits before returning to the menu.
:run
echo.
echo Running %~1 !ARGS!
echo.
"%PY%" "%ROOT%%~1" !ARGS!
echo.
echo Finished. Press any key to return to menu.
pause >nul
goto :eof
