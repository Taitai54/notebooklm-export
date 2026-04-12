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

REM Double-click with no args: argparse would fail and the window would vanish
if "%~1"=="" (
  echo.
  echo notebooklm-export.bat — no command given.
  echo.
  echo Open Command Prompt here and run for example:
  echo   notebooklm-export.bat list
  echo   notebooklm-export.bat export "My notebook title" --out .\exports
  echo.
  echo Or double-click  export.bat  to export using the default notebook set inside that file.
  echo.
  pause
  exit /b 1
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
