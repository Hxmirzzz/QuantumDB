#!/bin/bash

# Script para instalar el sistema de backup como servicio systemd en Linux

echo "============================================"
echo "Instalador de Servicio de Backup de BBDD"
echo "============================================"
echo ""

# Verificar si se ejecuta como root
if [ "$EUID" -ne 0 ]; then 
    echo "ERROR: Este script debe ejecutarse como root"
    echo "Por favor ejecuta: sudo $0"
    exit 1
fi

# Obtener directorio del script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$SCRIPT_DIR"

# Obtener usuario real (no root)
REAL_USER="${SUDO_USER:-$USER}"
echo "Usuario del servicio: $REAL_USER"
echo "Directorio de trabajo: $SCRIPT_DIR"

# Verificar que existe Python
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python3 no está instalado"
    echo "Instala con: sudo apt install python3 python3-pip python3-venv"
    exit 1
fi

# Crear entorno virtual si no existe
if [ ! -d "venv" ]; then
    echo "Creando entorno virtual..."
    sudo -u "$REAL_USER" python3 -m venv venv
    sudo -u "$REAL_USER" ./venv/bin/pip install -r requirements.txt
fi

# Verificar archivos de configuración
if [ ! -f "config.json" ]; then
    if [ -f "config.json.example" ]; then
        echo "Copiando config.json.example a config.json"
        sudo -u "$REAL_USER" cp config.json.example config.json
        echo "ATENCIÓN: Debes editar config.json con tu configuración"
    else
        echo "ERROR: No existe config.json ni config.json.example"
        exit 1
    fi
fi

if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        echo "Copiando .env.example a .env"
        sudo -u "$REAL_USER" cp .env.example .env
        echo "ATENCIÓN: Debes editar .env con tus credenciales"
    fi
fi

# Crear directorio de logs si no existe
mkdir -p Logs Backups
chown "$REAL_USER:$REAL_USER" Logs Backups

# Crear archivo de servicio systemd
SERVICE_FILE="/etc/systemd/system/db-backup.service"

echo ""
echo "Creando archivo de servicio systemd..."

cat > "$SERVICE_FILE" <<EOF
[Unit]
Description=Database Backup Service
After=network.target mysql.service postgresql.service mariadb.service
Wants=network-online.target

[Service]
Type=simple
User=$REAL_USER
Group=$REAL_USER
WorkingDirectory=$SCRIPT_DIR
Environment="PATH=$SCRIPT_DIR/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
ExecStart=$SCRIPT_DIR/venv/bin/python $SCRIPT_DIR/main.py
Restart=always
RestartSec=10
StandardOutput=append:$SCRIPT_DIR/Logs/service_stdout.log
StandardError=append:$SCRIPT_DIR/Logs/service_stderr.log

# Configuración de seguridad
PrivateTmp=true
NoNewPrivileges=true

[Install]
WantedBy=multi-user.target
EOF

echo "Archivo de servicio creado en: $SERVICE_FILE"

# Recargar systemd
echo "Recargando systemd..."
systemctl daemon-reload

# Habilitar servicio para que inicie automáticamente
echo "Habilitando servicio para inicio automático..."
systemctl enable db-backup.service

echo ""
echo "============================================"
echo "Servicio instalado exitosamente!"
echo "============================================"
echo ""
echo "Comandos útiles:"
echo "  Iniciar servicio:    sudo systemctl start db-backup"
echo "  Detener servicio:    sudo systemctl stop db-backup"
echo "  Reiniciar servicio:  sudo systemctl restart db-backup"
echo "  Estado del servicio: sudo systemctl status db-backup"
echo "  Ver logs:            sudo journalctl -u db-backup -f"
echo "  Ver logs del script: tail -f $SCRIPT_DIR/Logs/*.log"
echo ""
echo "Deshabilitar inicio automático: sudo systemctl disable db-backup"
echo "Eliminar servicio: sudo systemctl stop db-backup && sudo systemctl disable db-backup && sudo rm $SERVICE_FILE && sudo systemctl daemon-reload"
echo ""

read -p "¿Deseas iniciar el servicio ahora? (s/n): " -n 1 -r
echo ""

if [[ $REPLY =~ ^[SsYy]$ ]]; then
    echo "Iniciando servicio..."
    systemctl start db-backup.service
    sleep 2
    systemctl status db-backup.service
    echo ""
    echo "Revisa los logs en: $SCRIPT_DIR/Logs/"
fi

echo ""
echo "Instalación completada."