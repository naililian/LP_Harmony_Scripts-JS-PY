@echo off
REM Customize Toolbars — launcher.
REM   Double-click to open the app. First run creates a local .venv and installs deps.
REM   run.bat build <project.lptb.json> --install "<folder>"   runs the CLI instead.

setlocal
set "HERE=%~dp0"
set "VENV=%HERE%.venv"
set "PY=%VENV%\Scripts\python.exe"
set "PYTHONPATH=%HERE%"

if not exist "%PY%" (
  echo Creating a local Python environment ^(first run only^)...
  where py >nul 2>&1 && ( py -3 -m venv "%VENV%" ) || ( python -m venv "%VENV%" )
  "%PY%" -m pip install --upgrade pip
  "%PY%" -m pip install -r "%HERE%requirements.txt"
)

"%PY%" -m customize_toolbars_builder %*
if errorlevel 1 (
  echo.
  echo Customize Toolbars exited with an error.
  pause
)
endlocal
