@echo off
echo.
echo ============================================================================
echo  process_list - Batch Video to Subtitle (folder list)
echo ============================================================================
echo   - Reads a text file of folder paths (one per line) and transcribes every
echo     video found in each, using the same engine as vdo2srt (local Whisper
echo     or Google Cloud STT).
echo   - Skips hidden folders and known non-movie folders (Subs, Extras, etc.).
echo   - Videos with an existing .srt are translated only (no re-transcribe);
echo     orphan .srt files with no matching video are translated too.
echo   - --overwrite re-transcribes videos AND retranslates existing output
echo     (previous translation backed up to .bak first).
echo   - No arguments: opens a GUI picker for the list file.
echo ============================================================================
echo.
setlocal
call "%~dp0_env.bat" || goto done
"%PY%" "%ROOT%process_list.py" %*
:done
echo.
echo Finished. Press any key to close.
pause > nul