echo off

if "%STABLEDIFFUSION_CACHE_DIR%" == "" set STABLEDIFFUSION_CACHE_DIR=stablediffusion_cache
venv_python.bat degu_diffusion_v0.py
