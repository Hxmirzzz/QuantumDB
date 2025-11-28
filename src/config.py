"""
Configuración centralizada del sistema de backup
"""
import logging
from pathlib import Path


class Config:
    """Configuración centralizada del sistema"""

    BASE_DIR = Path(__file__).parent.parent
    BACKUP_DIR = BASE_DIR / "Backups"
    LOG_DIR = BASE_DIR / "Logs"
    CONFIG_FILE = BASE_DIR / "config.json"
    ENV_FILE = BASE_DIR / ".env"

    MAX_BACKUP_DAYS = 7  # Dias de retención de backups
    BACKUP_HOUR = "02:00"  # Hora de ejecución del backup

    LOG_LEVEL = logging.INFO
    LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

    SUPPORTED_DB_TYPES = ['mysql', 'mariadb', 'postgresql', 'postgres', 'sqlserver', 'mssql']

    DEFAULT_CONFIG = {
        "databases": [
            {
                "name": "VCashPRD",
                "type": "sqlserver",
                "host": "WIN-OCH96NT6EBI\\VATCOPRD",
                "port": 1433,
                "user": "${DB_USER}",
                "password": "${DB_PASSWORD}",
                "database": "VCashAppDb",
                "enabled": True
            }
        ],
        "backup_settings": {
            "retention_days": 7,
            "schedule": "02:00",
            "compress": True
        }
    }

    @classmethod  # ← CORREGIDO: Agregado @classmethod
    def ensure_directories(cls):
        """Crea los directorios necesarios si no existen"""
        cls.BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        cls.LOG_DIR.mkdir(parents=True, exist_ok=True)