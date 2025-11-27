# 🗄️ Sistema de Backup Automático de Bases de Datos

Sistema profesional y modular de backup automático para bases de datos MySQL/MariaDB, PostgreSQL y SQL Server, desarrollado con principios SOLID y arquitectura limpia.

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

## ✨ Características

- ✅ **Backups automáticos** programables diariamente
- ✅ **Multi-motor**: MySQL/MariaDB, PostgreSQL y SQL Server
- ✅ **Credenciales seguras** mediante variables de entorno
- ✅ **Logs detallados** de todas las operaciones
- ✅ **Limpieza automática** de backups antiguos
- ✅ **Reinicio automático** tras caídas del servidor
- ✅ **Arquitectura SOLID** modular y extensible
- ✅ **Tests unitarios** incluidos
- ✅ **Listo para GitHub** sin exponer secretos

## 🏗️ Arquitectura

### Principios SOLID Implementados

1. **Single Responsibility**: Cada clase tiene una única responsabilidad
2. **Open/Closed**: Extensible sin modificar código existente
3. **Liskov Substitution**: Estrategias intercambiables
4. **Interface Segregation**: Interfaces específicas
5. **Dependency Inversion**: Dependencias mediante abstracciones

### Estructura del Proyecto

```
DailyBackupDatabase/
│
├── src/
│   ├── __init__.py
│   ├── config.py                 # Configuración centralizada
│   ├── logger.py                 # Servicio de logging
│   ├── models.py                 # Modelos de datos
│   │
│   ├── repositories/
│   │   ├── __init__.py
│   │   └── config_repository.py  # Gestión de configuración
│   │
│   ├── strategies/
│   │   ├── __init__.py
│   │   ├── base_strategy.py      # Estrategia base (abstracta)
│   │   ├── mysql_strategy.py     # Implementación MySQL
│   │   ├── postgresql_strategy.py
│   │   └── sqlserver_strategy.py
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── backup_service.py     # Orquestación de backups
│   │   ├── cleanup_service.py    # Limpieza de archivos antiguos
│   │   └── scheduler_service.py  # Programación de tareas
│   │
│   └── factories/
│       ├── __init__.py
│       └── strategy_factory.py   # Factory de estrategias
│
├── tests/
│   ├── __init__.py
│   └── test_backup.py            # Tests unitarios
│
├── scripts/
│   ├── install_windows_service.bat
│   └── install_linux_service.sh
│
├── main.py                       # Punto de entrada
├── setup.py                      # Setup para instalación
├── requirements.txt
├── Makefile
├── .env.example
├── .gitignore
├── config.json.example
└── README.md
```

## 📋 Requisitos Previos

### Windows
```bash
# Instalar Python
winget install Python.Python.3.12

# Instalar herramientas de BD (según necesites)
winget install Oracle.MySQL
winget install PostgreSQL.PostgreSQL
```

### Linux (Ubuntu/Debian)
```bash
sudo apt update
sudo apt install python3 python3-pip python3-venv
sudo apt install mysql-client      # Para MySQL
sudo apt install postgresql-client # Para PostgreSQL
```

## 🚀 Instalación Rápida

```bash
# 1. Clonar repositorio
git clone https://github.com/Hxmirzzz/DailyBackupDatabase.git
cd DailyBackupDatabase

# 2. Crear entorno virtual
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Inicializar configuración
python main.py --init

# 5. Configurar credenciales
cp .env.example .env
# Editar .env con tus credenciales

# 6. Configurar bases de datos
# Editar config.json con tu configuración
```

## ⚙️ Configuración

### 1. Archivo `.env` (Credenciales)

```bash
# MySQL/MariaDB
DB_USER=backup_user
DB_PASSWORD=tu_password_seguro

# PostgreSQL
PG_USER=postgres_user
PG_PASSWORD=otro_password

# SQL Server
MSSQL_USER=sa
MSSQL_PASSWORD=password_sqlserver
```

### 2. Archivo `config.json` (Bases de Datos)

```json
{
  "databases": [
    {
      "name": "mi_base_datos",
      "type": "mysql",
      "host": "localhost",
      "port": 3306,
      "user": "${DB_USER}",
      "password": "${DB_PASSWORD}",
      "enabled": true
    },
    {
      "name": "otra_base",
      "type": "postgresql",
      "host": "localhost",
      "port": 5432,
      "user": "${PG_USER}",
      "password": "${PG_PASSWORD}",
      "enabled": true
    }
  ],
  "backup_settings": {
    "retention_days": 7,
    "schedule": "02:00",
    "compress": true
  }
}
```

## 🎯 Uso

### Comandos Básicos

```bash
# Modo scheduler (automático)
python main.py

# Ejecutar backup una sola vez
python main.py once

# Backup de una BD específica
python main.py --db mi_base_datos

# Ver estadísticas
python main.py --stats

# Iniciar con backup inmediato
python main.py --now

# Ver ayuda
python main.py --help
```

### Usando Make

```bash
make install    # Instalar dependencias
make init       # Crear archivos de configuración
make test       # Ejecutar tests
make run        # Ejecutar en modo scheduler
make run-once   # Ejecutar backup una vez
make stats      # Ver estadísticas
make clean      # Limpiar archivos temporales
```

## 🖥️ Instalación como Servicio

### Windows (NSSM - Recomendado)

```bash
# 1. Descargar NSSM desde https://nssm.cc/download

# 2. Ejecutar el instalador (como administrador)
scripts\install_windows_service.bat

# Comandos útiles
nssm start DBBackupService
nssm stop DBBackupService
nssm status DBBackupService
nssm edit DBBackupService
nssm remove DBBackupService
```

### Windows (Task Scheduler)

1. Abrir "Programador de tareas"
2. Crear tarea básica
3. Disparador: "Al iniciar el sistema"
4. Acción: Ejecutar `start_backup.bat`
5. Configurar para ejecutar con privilegios

### Linux (systemd)

```bash
# Ejecutar script de instalación
sudo bash scripts/install_linux_service.sh

# Comandos útiles
sudo systemctl start db-backup
sudo systemctl stop db-backup
sudo systemctl status db-backup
sudo systemctl enable db-backup   # Habilitar inicio automático
sudo systemctl disable db-backup  # Deshabilitar inicio automático
journalctl -u db-backup -f        # Ver logs en tiempo real
```

## 🔒 Seguridad de Credenciales

### Crear Usuario de Backup en MySQL

```sql
-- Crear usuario específico para backups
CREATE USER 'backup_user'@'localhost' IDENTIFIED BY 'password_seguro_aqui';

-- Otorgar permisos necesarios (solo lectura)
GRANT SELECT, LOCK TABLES, SHOW VIEW, EVENT, TRIGGER 
ON *.* TO 'backup_user'@'localhost';

-- Aplicar cambios
FLUSH PRIVILEGES;
```

### Crear Usuario de Backup en PostgreSQL

```sql
-- Crear usuario
CREATE USER backup_user WITH PASSWORD 'password_seguro_aqui';

-- Otorgar permisos
GRANT CONNECT ON DATABASE mi_base_datos TO backup_user;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO backup_user;
GRANT SELECT ON ALL SEQUENCES IN SCHEMA public TO backup_user;

-- Para futuras tablas
ALTER DEFAULT PRIVILEGES IN SCHEMA public 
GRANT SELECT ON TABLES TO backup_user;
```

### Crear Usuario de Backup en SQL Server

```sql
-- Crear login
CREATE LOGIN backup_user WITH PASSWORD = 'password_seguro_aqui';

-- Crear usuario en la base de datos
USE mi_base_datos;
CREATE USER backup_user FOR LOGIN backup_user;

-- Otorgar permisos
GRANT BACKUP DATABASE TO backup_user;
GRANT BACKUP LOG TO backup_user;
GRANT VIEW DEFINITION TO backup_user;
```

## 📊 Logs y Monitoreo

Los logs se generan automáticamente en el directorio `logs/`:

```
logs/
├── BackupService_20241127.log
├── ConfigRepository_20241127.log
├── CleanupService_20241127.log
└── SchedulerService_20241127.log
```

### Ver Logs en Tiempo Real

```bash
# Linux
tail -f logs/BackupService_*.log

# Windows PowerShell
Get-Content logs\BackupService_*.log -Wait -Tail 50
```

## 🧪 Tests

```bash
# Ejecutar todos los tests
python -m pytest tests/ -v

# Con cobertura
python -m pytest tests/ -v --cov=src --cov-report=html

# Test específico
python tests/test_backup.py
```

## 🔧 Extender el Sistema

### Agregar Soporte para Nueva Base de Datos

```python
# 1. Crear nueva estrategia en src/strategies/
from .base_strategy import BackupStrategy

class OracleBackupStrategy(BackupStrategy):
    def backup(self, db_config, output_file):
        # Implementar lógica de backup
        pass

# 2. Registrar en factory
from src.factories.strategy_factory import BackupStrategyFactory
from src.strategies.oracle_strategy import OracleBackupStrategy

BackupStrategyFactory.register_strategy('oracle', OracleBackupStrategy)
```

## 🐛 Troubleshooting

### Error: "comando no encontrado mysqldump/pg_dump"
```bash
# Instalar herramientas de cliente
sudo apt install mysql-client postgresql-client
```

### Error: "Access denied"
```bash
# Verificar credenciales en .env
# Verificar permisos del usuario en la BD
```

### Error: "Cannot find config.json"
```bash
# Inicializar configuración
python main.py --init
```

### Logs no se generan
```bash
# Verificar permisos del directorio logs/
chmod 755 logs/
```

## 📈 Roadmap

- [ ] Compresión automática de backups (gzip)
- [ ] Notificaciones por email/Slack
- [ ] Sincronización con servicios cloud (S3, Azure Blob)
- [ ] Dashboard web para monitoreo
- [ ] Soporte para Oracle y MongoDB
- [ ] Cifrado de backups
- [ ] Restauración automática
- [ ] API REST

## 🤝 Contribuciones

Las contribuciones son bienvenidas! Por favor:

1. Fork del proyecto
2. Crear rama para tu feature (`git checkout -b feature/AmazingFeature`)
3. Commit de cambios (`git commit -m 'Add: nueva funcionalidad'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abrir Pull Request

## 📄 Licencia

Este proyecto está bajo la Licencia MIT - ver el archivo [LICENSE](LICENSE) para detalles.

## 👤 Autor

**Hamir David Rocha Causaya**
- GitHub: [Hxmirzzz](https://github.com/Hxmirzzz)
- LinkedIn: [Hamir David Rocha Causaya](https://www.linkedin.com/in/hamir01/)

## 🙏 Agradecimientos

- Diseñado con principios SOLID
- Inspirado en las mejores prácticas de DevOps
- Arquitectura limpia y mantenible

## 📞 Soporte

Si encuentras algún problema o tienes preguntas:
- 📧 Contacto: jamir08david@gmail.com

---

⭐ Si este proyecto te fue útil, considera darle una estrella en GitHub!
