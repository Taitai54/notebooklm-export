@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"

REM =============================================================================
REM  Double-click export: set your notebook TITLE or UUID on the next line.
REM  Title matching is the same as the CLI (case-insensitive; unique substring OK).
REM =============================================================================
set "NOTEBOOK=CHANGE_ME_TO_YOUR_NOTEBOOK_TITLE_OR_UUID"

if /I "!NOTEBOOK!"=="CHANGE_ME_TO_YOUR_NOTEBOOK_TITLE_OR_UUID" (
  echo.
  echo Edit export.bat in Notepad and set NOTEBOOK= to your notebook name or UUID.
  echo Example:  set "NOTEBOOK=December"
  echo Example:  set "NOTEBOOK=cf0de99f-b8fc-4014-b26c-647cd2a0d431"
  echo.
  pause
  exit /b 1
)

where py >nul 2>&1
if not errorlevel 1 goto :run_with_py
where python >nul 2>&1
if not errorlevel 1 goto :run_with_python

echo.
echo [ERROR] Python not found on PATH. Install Python 3.10+ and enable PATH or the py launcher.
echo.
pause
exit /b 900

:run_with_py
echo Using: py -3
echo Notebook: !NOTEBOOK!
echo Output:   %~dp0exports
echo.
py -3 -m pip show notebooklm-export >nul 2>&1
if errorlevel 1 (
  echo First-time setup: pip install -e .
  py -3 -m pip install -e .
  if errorlevel 1 (
    echo pip install failed.
    pause
    exit /b 1
  )
)
py -3 -m notebooklm_export export "!NOTEBOOK!" --out "%~dp0exports" --summaries --studio-manifest
set "EC=!ERRORLEVEL!"
goto :finish

:run_with_python
echo Using: python
echo Notebook: !NOTEBOOK!
echo Output:   %~dp0exports
echo.
python -m pip show notebooklm-export >nul 2>&1
if errorlevel 1 (
  echo First-time setup: pip install -e .
  python -m pip install -e .
  if errorlevel 1 (
    echo pip install failed.
    pause
    exit /b 1
  )
)
python -m notebooklm_export export "!NOTEBOOK!" --out "%~dp0exports" --summaries --studio-manifest
set "EC=!ERRORLEVEL!"

:finish
if not "!EC!"=="0" (
  echo.
  echo Export finished with errors ^(code !EC!^). Read messages above.
  echo Common fixes: run notebooklm-mcp-auth ; use pip install -e . with same Python as this script.
  echo.
) else (
  echo.
  echo Done. Files are under: %~dp0exports
  echo.
)
pause
exit /b !EC!
