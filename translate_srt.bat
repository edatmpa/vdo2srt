@echo off
echo.
echo ============================================================================
echo  translate_srt - Translate existing .srt files (no video/transcription)
echo ============================================================================
echo   - Translates .srt subtitle files that already exist, to another
echo     language (default: English). Engine is chosen automatically per
echo     detected source language - see translate_routing.txt.
echo   - Point it at a single .srt file, one folder, or a library root with
echo     --recursive (root -^> movie/show folders -^> files).
echo   - Skips files that already have a translation, unless --overwrite
echo     (which backs up the previous translation to .bak first).
echo   - No arguments: opens a GUI picker (file or folder).
echo ============================================================================
echo.
setlocal
call "%~dp0_env.bat" || goto done
"%PY%" "%ROOT%translate_srt.py" %*
:done
echo.
echo Finished. Press any key to close.
pause > nul
