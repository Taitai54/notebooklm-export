@echo off
setlocal EnableExtensions
cd /d "%~dp0"

REM Prefer Windows "py" launcher (often works when double-clicking even if python.exe is not on PATH)
set "HAS_PY=0"
where py >nul 2>&1 && set "HAS_PY=1"
set "HAS_PYTHON=0"
where python >nul 2>&1 && set "HAS_PYTHON=1"

if "%HAS_PY%"=="0" if "%HAS_PYTHON%"=="0" (
  echo.
  echo [ERROR] Python was not found.
  echo.
  echo Fix: Install Python 3.10+ from https://www.python.org/downloads/
  echo  - Enable "Add python.exe to PATH", OR
  echo  - Use the default "py" launcher install.
  echo Then open PowerShell in this folder and run:  pip install -e .
  echo.
  pause
  exit /b 900
)

REM Double-click with no args: open the GUI (same as export-gui.bat).
REM CLI users: run from Command Prompt with a subcommand, e.g. list / export / discover.
if "%~1"=="" (
  echo.
  echo Starting the NotebookLM export GUI in a new window...
  echo.
  echo Tip: For the command line, open Command Prompt here and run:
  echo   notebooklm-export.bat list
  echo   notebooklm-export.bat export "My notebook title" --out .\exports
  echo.
  echo For one-click export without the GUI, double-click export.bat
  echo.
  if exist "%~dp0export-gui.bat" (
    call "%~dp0export-gui.bat"
  ) else (
    set "PYTHONUNBUFFERED=1"
    set "PYTHONIOENCODING=utf-8"
    if "%HAS_PY%"=="1" (
      start "NotebookLM export" py -3 -m notebooklm_export.gui
    ) else (
      start "NotebookLM export" python -m notebooklm_export.gui
    )
  )
  timeout /t 2 /nobreak >nul
  exit /b 0
)

if "%HAS_PY%"=="1" (
  py -3 -m notebooklm_export %*
) else (
  python -m notebooklm_export %*
)

set "EC=%ERRORLEVEL%"
if not "%EC%"=="0" (
  echo.
  echo [ERROR] Exit code %EC%. If you see "No module named notebooklm_export", run:
  echo   pip install -e .
  echo from this folder in a terminal ^(use the same Python as above^).
  echo.
  pause
)
exit /b %EC%
