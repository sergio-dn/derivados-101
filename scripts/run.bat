@echo off
REM Lanza la app derivados-101 en Windows.
REM Idempotente: crea .venv solo si no existe y reinstala dependencias solo si
REM requirements.txt cambio. Argumentos extra se pasan a "streamlit run".
setlocal EnableExtensions EnableDelayedExpansion

cd /d "%~dp0.."

REM 1) Buscar un Python >= 3.11 (lanzador "py" primero, luego "python")
set "PYTHON_BIN="
where py >nul 2>&1
if not errorlevel 1 (
    py -3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)" >nul 2>&1
    if not errorlevel 1 set "PYTHON_BIN=py -3"
)
if not defined PYTHON_BIN (
    where python >nul 2>&1
    if not errorlevel 1 (
        python -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)" >nul 2>&1
        if not errorlevel 1 set "PYTHON_BIN=python"
    )
)
if not defined PYTHON_BIN (
    echo ERROR: se necesita Python 3.11 o superior y no se encontro.
    echo        Descargalo desde https://www.python.org/downloads/
    echo        y marca "Add python.exe to PATH" durante la instalacion.
    exit /b 1
)

REM 2) Crear el entorno virtual si no existe
if not exist ".venv\Scripts\python.exe" (
    echo ==^> Creando entorno virtual en .venv ^(solo la primera vez^)...
    %PYTHON_BIN% -m venv .venv
    if errorlevel 1 (
        echo ERROR: no se pudo crear el entorno virtual.
        exit /b 1
    )
)

set "VENV_PY=.venv\Scripts\python.exe"
set "STAMP=.venv\requirements.stamp"

REM 3) Instalar dependencias solo si requirements.txt cambio
for /f "usebackq delims=" %%H in (`%VENV_PY% -c "import hashlib; print(hashlib.sha256(open('requirements.txt','rb').read()).hexdigest())"`) do set "CURRENT_HASH=%%H"
set "OLD_HASH="
if exist "%STAMP%" set /p OLD_HASH=<"%STAMP%"
if not "!OLD_HASH!"=="!CURRENT_HASH!" (
    echo ==^> Instalando dependencias ^(puede tardar un par de minutos la primera vez^)...
    "%VENV_PY%" -m pip --version >nul 2>&1
    if errorlevel 1 "%VENV_PY%" -m ensurepip --upgrade >nul
    "%VENV_PY%" -m pip install --upgrade pip --quiet
    "%VENV_PY%" -m pip install -r requirements.txt --quiet
    if errorlevel 1 (
        echo ERROR: fallo la instalacion de dependencias.
        exit /b 1
    )
    > "%STAMP%" echo !CURRENT_HASH!
) else (
    echo ==^> Dependencias al dia.
)

REM 4) Lanzar la app
echo ==^> Abriendo la app en el navegador ^(Ctrl+C para cerrar^)...
"%VENV_PY%" -m streamlit run app.py %*
endlocal
