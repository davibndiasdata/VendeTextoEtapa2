@echo off
setlocal
chcp 65001 >nul
set PYTHONUTF8=1
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo Execute instalar_windows.bat primeiro.
    pause
    exit /b 1
)
".venv\Scripts\python.exe" vendetexto2.py --modo cache --offline %*
if errorlevel 1 (
    echo Confira o erro acima. Se faltarem modelos, execute instalar_windows.bat com internet.
) else (
    echo Resultados disponiveis no caminho impresso acima.
)
pause
