@echo off
rem setup.bat - builds the Python environment (venv) for vdo2srt on THIS PC. Run it once after copying or
rem cloning the folder, after reinstalling Python, or whenever a launcher says the venv is missing/broken.
rem   - uses Python 3.10+ ("py" launcher or python on PATH)
rem   - an old/foreign venv is renamed to venv_old_<date> (not deleted)
rem   - installs requirements.txt; the NVIDIA GPU libraries only if an NVIDIA GPU is present
rem   - checks FFmpeg and offers to install it with winget
setlocal
cd /d "%~dp0"
title vdo2srt - setup
echo.
echo  vdo2srt - setup
echo  ---------------

set "SYS="
where py >nul 2>&1 && set "SYS=py -3"
if not defined SYS where python >nul 2>&1 && set "SYS=python"
if not defined SYS goto nopython
%SYS% -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>&1
if errorlevel 1 goto nopython
for /f "delims=" %%v in ('%SYS% --version') do echo  Found %%v

rem ---- keep a working venv, replace a broken/foreign one
if exist "venv\Scripts\python.exe" (
    "venv\Scripts\python.exe" -c "import sys" >nul 2>&1
    if not errorlevel 1 (
        echo  venv works on this PC - updating its packages.
        goto install
    )
)
if exist "venv\" (
    for /f %%d in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd_HHmm"') do set "STAMP=%%d"
    call echo  The existing venv does not work on this PC - renaming it to venv_old_%%STAMP%% ^(delete it later^).
    call ren venv venv_old_%%STAMP%%
    if exist "venv\" (
        echo  Could not rename venv - close any program using it and run setup.bat again.
        goto fail
    )
)
echo  Creating venv ...
%SYS% -m venv venv
if errorlevel 1 goto fail

:install
echo.
echo  Installing packages (faster-whisper, translators, Google STT) ...
"venv\Scripts\python.exe" -m pip install --upgrade pip --quiet
"venv\Scripts\python.exe" -m pip install --upgrade -r requirements.txt
if errorlevel 1 goto fail

where nvidia-smi >nul 2>&1
if errorlevel 1 (
    echo  No NVIDIA GPU found - transcription will use the CPU ^(choose "Local CPU"^).
) else (
    echo  NVIDIA GPU found - installing the CUDA libraries ^(about 1 GB^) ...
    "venv\Scripts\python.exe" -m pip install --upgrade -r requirements-gpu.txt
    if errorlevel 1 goto fail
)

"venv\Scripts\python.exe" -c "import faster_whisper, deep_translator, langdetect, tqdm; print('  Packages OK')"
if errorlevel 1 goto fail

echo.
where ffmpeg >nul 2>&1
if errorlevel 1 (
    echo  FFmpeg is not installed ^(needed to read the sound from videos^).
    choice /C YN /M "  Install FFmpeg with winget now"
    if not errorlevel 2 winget install --id Gyan.FFmpeg.Essentials -e --accept-source-agreements --accept-package-agreements
    echo  Close this window and open a new one so Windows finds FFmpeg.
) else (
    echo  FFmpeg OK.
)

echo.
echo  Setup finished. Start the tools with vdo2srt.bat.
echo.
pause
exit /b 0

:nopython
echo  Python 3.10 or newer was not found. Install it from https://www.python.org/downloads/
echo  (tick "Add python.exe to PATH"), then run setup.bat again.
:fail
echo.
echo  Setup did not finish - see the messages above.
pause
exit /b 1
