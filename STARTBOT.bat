echo off

set STABLEDIFFUSION_CACHE_DIR=stablediffusion_cache

python -m venv venv
if NOT %ERRORLEVEL% == 0 goto :venv_preparation_failed

venv\Scripts\python.exe -m pip install -r requirements.txt
if NOT %ERRORLEVEL% == 0 goto :dependencies_install_failed

venv\Scripts\python.exe degu_diffusion_v0.py
pause
exit

:dependencies_install_failed
echo "Dependencies install failed."
echo "Exiting."
pause
exit

:venv_activation_failed
echo "Could not active the Python virtual environment."
echo "Exiting."
pause
exit

:venv_preparation_failed
echo "Creation of the Python virtual environment failed."
echo "Exiting."
pause
exit

