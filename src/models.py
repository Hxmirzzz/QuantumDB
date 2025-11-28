"""
Modelos de datos del sistema
"""
from dataclasses import dataclass
from typing import Optional


@dataclass
class DatabaseConfig:
    """Configuración de una base de datos"""
    name: str
    type: str
    host: str
    port: int
    user: str
    password: str
    enabled: bool = True
    database: Optional[str] = None

    def __post_init__(self):
        """Validación después de inicialización"""
        if not self.name:
            raise ValueError("El nombre de la base de datos es obligatorio")
        if not self.type:
            raise ValueError("El tipo de base de datos es obligatorio")

@dataclass
class BackupSettings:
    """Configuración de backups"""
    retention_days: int = 7
    schedule: str = "02:00"
    compress: bool = True

    def __post_init__(self):
        """Validación después de inicialización"""
        if self.retention_days < 1:
            raise ValueError("retention_days debe ser mayor a 0")
        if not self._validate_time_format(self.schedule):
            raise ValueError("El formato de schedule debe ser HH:MM")

    @staticmethod
    def _validate_time_format(time_str: str) -> bool:
        """Valida formato de hora HH:MM"""
        try:
            parts = time_str.split(":")
            if len(parts) != 2:
                return False
            hours, minutes = int(parts[0]), int(parts[1])
            return 0 <= hours < 23 and 0 <= minutes < 59
        except (ValueError, AttributeError):
            return False

@dataclass
class BackupResult:
    """Resultado de una operación de backup"""
    database_name: str
    success: bool
    output_file: Optional[str] = None
    error: Optional[str] = None
    duration_seconds: float = 0.0

    def __str__(self):
        if self.success:
            return f"✓ {self.database_name}: {self.output_file} ({self.duration_seconds:.2f}s)"
        else:
            return f"✗ {self.database_name}: {self.error}"