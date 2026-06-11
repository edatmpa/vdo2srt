@echo off
set KMP_DUPLICATE_LIB_OK=TRUE
set PATH=C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.5\bin;%PATH%
python "%~dp0vdo2srt.py" %*
echo.
echo Finished. Press any key to close.
timeout /t -1 /nobreak > nul
