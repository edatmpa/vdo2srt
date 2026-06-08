@echo off
"E:\vdo2srt\venv\Scripts\python.exe" "E:\vdo2srt\vdo2srt.py" %*
echo.
echo Finished. Press any key to close.
timeout /t -1 /nobreak > nul
