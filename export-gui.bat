@echo off
setlocal
cd /d "%~dp0"
set "PYTHONUNBUFFERED=1"
set "PYTHONIOENCODING=utf-8"

where py >nul 2>&1
if not errorlevel 1 (
  start "NotebookLM export" py -3 -m notebooklm_export.gui
  exit /b 0
)
where python >nul 2>&1
if not errorlevel 1 (
  start "NotebookLM export" python -m notebooklm_export.gui
  exit /b 0
)

echo Python not found. Install Python 3.10+ and try again.
pause
exit /b 1
