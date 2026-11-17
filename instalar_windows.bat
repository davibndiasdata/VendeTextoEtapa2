@echo off
setlocal
chcp 65001 >nul
set PYTHONUTF8=1
cd /d "%~dp0"
echo VendeTexto - instalacao da etapa 2
echo Recomendado: Python 3.12 de 64 bits. A primeira instalacao precisa de internet.
if not exist ".venv\Scripts\python.exe" (
    py -3.12 -m venv .venv
    if errorlevel 1 (
        echo Tentando o comando python disponivel no computador...
        python -m venv .venv
        if errorlevel 1 goto falha
    )
)
".venv\Scripts\python.exe" -m pip install -r requirements-torch-cpu.txt
if errorlevel 1 goto falha
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto falha
".venv\Scripts\python.exe" vendetexto2.py --modo preparar
if errorlevel 1 goto falha
".venv\Scripts\python.exe" -m unittest discover -s testes -v
if errorlevel 1 goto falha
echo.
echo Instalacao concluida. Abra executar_windows.bat para analisar as cinco issues.
pause
exit /b 0
:falha
echo.
echo Nao foi possivel concluir. Confira o erro acima e o arquivo LEIA_PRIMEIRO.txt.
pause
exit /b 1
