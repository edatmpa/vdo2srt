@echo off
rem _env.bat - shared start-up for vdo2srt.bat, process_list.bat and translate_srt.bat (called, not run directly).
rem Sets ROOT and PY (the project's own Python in venv\) and checks that it works on THIS PC.
rem A venv copied from another PC points at that PC's Python and fails - then run setup.bat.
set "ROOT=%~dp0"
set "PY=%ROOT%venv\Scripts\python.exe"
set "KMP_DUPLICATE_LIB_OK=TRUE"
rem NVIDIA GPU libraries (only present when setup.bat found an NVIDIA GPU)
set "PATH=%ROOT%venv\Lib\site-packages\nvidia\cublas\bin;%ROOT%venv\Lib\site-packages\nvidia\cudnn\bin;%PATH%"

if not exist "%PY%" goto broken
"%PY%" -c "import faster_whisper" >nul 2>&1
if errorlevel 1 goto broken
exit /b 0

:broken
echo.
echo  The Python environment (venv) is missing or was made on another PC.
echo  Run setup.bat in this folder once to build it, then try again.
echo.
exit /b 1
