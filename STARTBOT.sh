#!/bin/bash

if [ -z "${STABLEDIFFUSION_CACHE_DIR+x}" ]; then
	export STABLEDIFFUSION_CACHE_DIR=stablediffusion_cache
fi

bash venv_python.sh degu_diffusion_v0.py
