@echo off
setlocal
cd /d "%~dp0"

REM Run the CLI: notebooklm-export.bat list
REM                         notebooklm-export.bat export "My Notebook" --out .\exports
where python >nul 2>&1
if errorlevel 1 (
  echo Python was not found on PATH. Install Python 3.10+ and run: pip install -e .
  exit /b 1
)

python -m notebooklm_export %*
exit /b %ERRORLEVEL%
