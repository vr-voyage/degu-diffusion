echo off

if "%1" == "" GOTO invalid_usage

python -m venv venv
if NOT %ERRORLEVEL% == 0 goto :venv_preparation_failed
if NOT EXIST "venv\Scripts\python.exe" goto :venv_preparation_failed

set VENV_PYTHON="venv\Scripts\python.exe"

%VENV_PYTHON% -m pip install -r requirements.txt
if NOT %ERRORLEVEL% == 0 goto :dependencies_install_failed

%VENV_PYTHON% %1
pause
exit 0

:dependencies_install_failed
echo "Dependencies install failed."
echo "Exiting."
pause
exit 1

:venv_preparation_failed
echo "Creation of the Python virtual environment failed."
echo "Exiting."
pause
exit 1

:invalid_usage
echo "Usage %0 python_script_to_execute.py"
pause
exit 1
