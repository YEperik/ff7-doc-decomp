@echo off
setlocal
cd /d "%~dp0"
if "%~1"=="" (
  echo Usage: drag an ELF onto this file, or run:
  echo   analyze-elf.bat "C:\path\to\game.elf"
  pause
  exit /b 2
)
where py >nul 2>nul
if errorlevel 1 (
  echo Python launcher not found. Install Python 3 from https://www.python.org/downloads/windows/
  pause
  exit /b 1
)
py tools\analyze_elf.py "%~1" --out reports
echo.
pause
