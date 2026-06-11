@echo off
python "%~dp0vdo2srt.py" %*
echo.
echo Finished. Press any key to close.
timeout /t -1 /nobreak > nul
