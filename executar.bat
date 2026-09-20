@echo off
setlocal
cd /d "%~dp0"
set "PY=python"
where py >nul 2>nul && set "PY=py"

%PY% --version >nul 2>nul
if errorlevel 1 (
    echo Python nao encontrado. Instale em https://www.python.org/downloads/ 
    echo e marque a opcao "Add Python to PATH" durante a instalacao.
    pause
    exit /b 1
)

%PY% -c "import customtkinter, openpyxl, reportlab" >nul 2>nul
if errorlevel 1 (
    echo Instalando as bibliotecas necessarias, aguarde...
    %PY% -m pip install -r requirements.txt
    if errorlevel 1 (
        echo.
        echo Nao foi possivel instalar. Verifique a internet e tente novamente.
        pause
        exit /b 1
    )
)

%PY% main.py
if errorlevel 1 pause
