#!/usr/bin/env bash
# Gera um executável para o sistema em que este script for rodado (Linux / macOS)
cd "$(dirname "$0")"
python3 -m pip install -r requirements.txt pyinstaller || exit 1
python3 -m PyInstaller --noconfirm --clean --windowed --name FarmaControl --collect-all customtkinter main.py || exit 1
echo "Pronto! Veja a pasta dist/FarmaControl"
