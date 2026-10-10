@echo off
setlocal
if "%~1"=="" (
  echo Usage: summarize-ghidra-export.bat "D:\reports\jal_triage_001.csv" [more CSV parts...]
  echo For many files, run the Python script directly with all CSV paths.
  exit /b 2
)
py -3 "%~dp0tools\summarize_ghidra_export.py" %*
endlocal
