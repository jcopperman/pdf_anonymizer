@echo off
REM Build script for Windows

REM Create virtual environment
python -m venv venv
call venv\Scripts\activate

REM Install requirements
pip install -r requirements.txt

REM Download spacy model
python -m spacy download en_core_web_sm

REM Create executable
python pyinstaller_spec.py

REM Clean up
deactivate