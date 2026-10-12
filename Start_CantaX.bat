@echo off
setlocal
cd /d "%~dp0"
if defined CANTAX_PYTHON (
  "%CANTAX_PYTHON%" "%~dp0scripts\launcher.py"
) else (
  python "%~dp0scripts\launcher.py"
)
if errorlevel 1 (
  echo Launcher failed. Install/configure the documented Python environment.
  pause
)
endlocal
