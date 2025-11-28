@echo off
REM Script para instalar el sistema de backup como servicio en Windows
REM Requiere NSSM (https://nssm.cc/)

echo ============================================
echo Instalador de Servicio de Backup de BBDD
echo ============================================
echo.

REM Verificar si se ejecuta como administrador
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo ERROR: Este script requiere privilegios de administrador
    echo Por favor, ejecuta como administrador
    pause
    exit /b 1
)

REM Obtener la ruta actual
set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%\.."

REM Verificar que existe Python
python --version >nul 2>&1
if %errorLevel% neq 0 (
    echo ERROR: Python no esta instalado o no esta en el PATH
    echo Por favor, instala Python primero
    pause
    exit /b 1
)

REM Verificar que existe el entorno virtual
if not exist "venv\Scripts\python.exe" (
    echo AVISO: No se encontro el entorno virtual
    echo Creando entorno virtual...
    python -m venv venv
    call venv\Scripts\activate
    pip install -r requirements.txt
)

REM Verificar archivos de configuración
if not exist "config.json" (
    if exist "config.json.example" (
        echo Copiando config.json.example a config.json
        copy config.json.example config.json
        echo ATENCION: Debes editar config.json con tu configuracion
    ) else (
        echo ERROR: No existe config.json ni config.json.example
        pause
        exit /b 1
    )
)

if not exist ".env" (
    if exist ".env.example" (
        echo Copiando .env.example a .env
        copy .env.example .env
        echo ATENCION: Debes editar .env con tus credenciales
    ) else (
        echo AVISO: No existe archivo .env
        echo Las credenciales deben estar en config.json o variables de sistema
    )
)

REM Verificar si NSSM está instalado
where nssm >nul 2>&1
if %errorLevel% neq 0 (
    echo.
    echo ERROR: NSSM no esta instalado
    echo.
    echo Por favor descarga NSSM desde: https://nssm.cc/download
    echo Y agrega nssm.exe al PATH del sistema
    echo.
    echo Como alternativa, puedes usar el Programador de Tareas de Windows
    pause
    exit /b 1
)

echo.
echo Configuracion:
echo - Directorio: %CD%
echo - Python: %CD%\venv\Scripts\python.exe
echo - Script: %CD%\main.py
echo.

REM Detener y eliminar servicio existente si existe
nssm stop DBBackupService >nul 2>&1
nssm remove DBBackupService confirm >nul 2>&1

echo Instalando servicio...
nssm install DBBackupService "%CD%\venv\Scripts\python.exe" "%CD%\main.py"

echo Configurando servicio...
nssm set DBBackupService AppDirectory "%CD%"
nssm set DBBackupService DisplayName "Database Backup Service"
nssm set DBBackupService Description "Sistema automatico de backup de bases de datos"
nssm set DBBackupService Start SERVICE_AUTO_START

REM Configurar logs de NSSM
nssm set DBBackupService AppStdout "%CD%\Logs\service_stdout.log"
nssm set DBBackupService AppStderr "%CD%\Logs\service_stderr.log"

REM Configurar reinicio automático
nssm set DBBackupService AppExit Default Restart
nssm set DBBackupService AppRestartDelay 5000

echo.
echo Servicio instalado exitosamente!
echo.
echo Comandos utiles:
echo   Iniciar servicio:  nssm start DBBackupService
echo   Detener servicio:  nssm stop DBBackupService
echo   Estado servicio:   nssm status DBBackupService
echo   Editar servicio:   nssm edit DBBackupService
echo   Eliminar servicio: nssm remove DBBackupService
echo.
echo Para iniciar el servicio ahora, presiona cualquier tecla...
pause >nul

echo Iniciando servicio...
nssm start DBBackupService

echo.
nssm status DBBackupService
echo.
echo Servicio iniciado. Revisa los logs en: %CD%\Logs\
echo.
pause