#!/usr/bin/env bash
# Executa o FarmaControl (Linux / macOS)
cd "$(dirname "$0")"
python3 -c "import customtkinter, openpyxl, reportlab" 2>/dev/null || python3 -m pip install -r requirements.txt
python3 main.py
