#!/bin/bash

if [ "$#" -le 0 ]; then
	echo "Usage : ${0} python_script_to_execute.py"
	exit 1
fi

SCRIPT_TO_EXECUTE=${1}

venv_preparation_failed () {
	echo "Could not create the Virtual Environment. Exiting."
	exit 1
}

pip_requirements_failed () {
	echo "Could not install the dependencies correctly."
	exit 1
}

select_python_venv () {
	if [ ! -z "${VENV_PYTHON+x}" ]; then
		echo "Using preset VENV_PYTHON variable : ${VENV_PYTHON}"
		return
	fi

	local venv_dir=${1}

	local linux_venv_python="${venv_dir}/bin/python"
	local windows_venv_python="${venv_dir}/Scripts/python.exe"

	if [ -f "${linux_venv_python}" ]; then
		echo 'Using Linux-like Virtual Environment'
		VENV_PYTHON="${linux_venv_python}"
	elif [ -f "${windows_venv_python}" ]; then
		echo 'Using Windows-like Virtual Environment'
		VENV_PYTHON="${windows_venv_python}"
	else
		echo "${windows_venv_python}"
		echo "Unsupported Virtual Environment. Exiting."
		exit 1
	fi
}


python -m venv venv || venv_preparation_failed
select_python_venv venv
"${VENV_PYTHON}" -m pip install -r requirements.txt || pip_requirements_failed
"${VENV_PYTHON}" "${SCRIPT_TO_EXECUTE}"
