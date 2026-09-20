@echo off
setlocal
cd /d "%~dp0"
set "PY=python"
where py >nul 2>nul && set "PY=py"

echo Instalando dependencias e o PyInstaller...
%PY% -m pip install -r requirements.txt pyinstaller || goto erro

echo Gerando o executavel (pode levar alguns minutos)...
%PY% -m PyInstaller --noconfirm --clean --windowed --name FarmaControl --collect-all customtkinter main.py || goto erro

echo.
echo Pronto! O programa esta em: dist\FarmaControl\FarmaControl.exe
echo Copie a pasta inteira "dist\FarmaControl" para onde quiser. Os dados ficam na subpasta "dados".
pause
exit /b 0

:erro
echo.
echo Falha ao gerar o executavel. Veja as mensagens acima.
pause
exit /b 1
