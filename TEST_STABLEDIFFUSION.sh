#!/bin/bash

if [ -z "${STABLEDIFFUSION_CACHE_DIR+x}" ]; then
	export STABLEDIFFUSION_CACHE_DIR=stablediffusion_cache
fi

bash venv_python.sh sdworker.py
