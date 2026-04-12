@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"

REM Force Python to print each line immediately (double-click consoles look "frozen" otherwise)
set "PYTHONUNBUFFERED=1"
set "PYTHONIOENCODING=utf-8"

title NotebookLM export

echo.
echo ===============================================================================
echo   NotebookLM export
echo   Folder: %~dp0
echo   Time:   %date% %time%
echo ===============================================================================
echo.

REM =============================================================================
REM  Option A: Put your notebook TITLE or UUID here (same rules as the CLI).
REM  Option B: Leave the placeholder — you will be asked to type it when you run.
REM =============================================================================
set "NOTEBOOK=CHANGE_ME_TO_YOUR_NOTEBOOK_TITLE_OR_UUID"

if /I "!NOTEBOOK!"=="CHANGE_ME_TO_YOUR_NOTEBOOK_TITLE_OR_UUID" (
  echo You have not set NOTEBOOK inside export.bat yet.
  echo.
  echo Type the notebook TITLE ^(e.g. December^) or paste the UUID, then press Enter:
  set /p "NOTEBOOK=> "
  echo.
)

REM Trim accidental spaces (common when pasting from the web)
for /f "tokens=* delims= " %%A in ("!NOTEBOOK!") do set "NOTEBOOK=%%A"

if "!NOTEBOOK!"=="" (
  echo [ERROR] No notebook name or UUID entered. Nothing was exported.
  echo.
  pause
  exit /b 1
)

echo Will export notebook: !NOTEBOOK!
echo Output will go under: %~dp0exports
echo.

where py >nul 2>&1
if not errorlevel 1 goto :run_with_py
where python >nul 2>&1
if not errorlevel 1 goto :run_with_python

echo [ERROR] Python not found on PATH.
echo Install Python 3.10+ from python.org and tick "Add python.exe to PATH", or install the "py" launcher.
echo.
pause
exit /b 900

:run_with_py
echo Using Python launcher: py -3
echo.
py -3 -m pip show notebooklm-export >nul 2>&1
if errorlevel 1 (
  echo First-time setup: installing this package ^(pip install -e .^)...
  py -3 -m pip install -e "%~dp0."
  if errorlevel 1 (
    echo [ERROR] pip install failed. Open a terminal in this folder and run:  py -3 -m pip install -e .
    pause
    exit /b 1
  )
  echo.
)

echo -------------------------------------------------------------------------------
echo  Calling NotebookLM MCP — this can take several minutes for large notebooks.
echo  Do not close this window until you see "Finished" below.
echo -------------------------------------------------------------------------------
echo.

py -3 -m notebooklm_export export "!NOTEBOOK!" --out "%~dp0exports" --summaries --studio-manifest
set "EC=!ERRORLEVEL!"
goto :finish

:run_with_python
echo Using: python
echo.
python -m pip show notebooklm-export >nul 2>&1
if errorlevel 1 (
  echo First-time setup: installing this package ^(pip install -e .^)...
  python -m pip install -e "%~dp0."
  if errorlevel 1 (
    echo [ERROR] pip install failed. Run:  python -m pip install -e .
    pause
    exit /b 1
  )
  echo.
)

echo -------------------------------------------------------------------------------
echo  Calling NotebookLM MCP — this can take several minutes for large notebooks.
echo  Do not close this window until you see "Finished" below.
echo -------------------------------------------------------------------------------
echo.

python -m notebooklm_export export "!NOTEBOOK!" --out "%~dp0exports" --summaries --studio-manifest
set "EC=!ERRORLEVEL!"

:finish
echo.
echo ===============================================================================
echo   Finished — exit code !EC!
echo ===============================================================================
if not "!EC!"=="0" (
  echo.
  echo Something went wrong ^(see messages above^). Common fixes:
  echo   - Run notebooklm-mcp-auth once so NotebookLM can sign in
  echo   - Run from cmd:  py -3 -m notebooklm_export list
  echo.
) else (
  echo.
  echo Export folder contents ^(first level^):
  if exist "%~dp0exports\" (
    dir /b "%~dp0exports" 2>nul
    echo.
    echo Tip: your files are usually in a subfolder under "exports" with your notebook title in the name.
  ) else (
    echo (exports folder was not created — check errors above^)
  )
  echo.
)

echo Press any key to close this window . . .
pause >nul
exit /b !EC!
