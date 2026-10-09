@echo off
setlocal
cd /d "%~dp0"
echo === Windows 10 project checks ===
where py >nul 2>nul
if errorlevel 1 (
  echo Python launcher "py" not found.
  echo Install Python from https://www.python.org/downloads/windows/
  echo Enable Add Python to PATH, then open a new Command Prompt.
  pause
  exit /b 1
)
py --version
py -m compileall -q tools
if errorlevel 1 (
  echo Python syntax check failed.
  pause
  exit /b 1
)
echo Checks passed. No extra Python packages are required.
pause
