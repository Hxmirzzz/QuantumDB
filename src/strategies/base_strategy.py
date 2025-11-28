"""
Estrategia base para backups (Strategy Pattern)
"""
from abc import ABC, abstractmethod
from pathlib import Path
import re
from typing import Optional
from ..logger import LoggerService
from ..models import DatabaseConfig, BackupResult
import time


class BackupStrategy(ABC):
    """Interfaz abstracta para estrategias de backup (Open/Closed Principle)"""
    
    def __init__(self):
        """Inicializa la estrategia"""
        self.logger = LoggerService.get_logger(self.__class__.__name__)
    
    @abstractmethod
    def backup(self, db_config: DatabaseConfig, output_file: Path) -> BackupResult:
        """
        Ejecuta el backup de la base de datos
        
        Args:
            db_config: Configuración de la base de datos
            output_file: Archivo de salida para el backup
            
        Returns:
            Resultado del backup
        """
        pass

    def execute_backup(self, db_config: DatabaseConfig, output_file: Path) -> BackupResult:
        """
        Template method para ejecutar backup con medición de tiempo
        
        Args:
            db_config: Configuración de la base de datos
            output_file: Archivo de salida para el backup
            
        Returns:
            Resultado del backup
        """
        self.logger.info(f"Iniciando backup de {db_config.name}...")
        start_time = time.time()
        
        try:
            result = self.backup(db_config, output_file)
            result.duration_seconds = time.time() - start_time

            if result.success:
                file_size = output_file.stat().st_size / (1024 * 1024)  # MB
                self.logger.info(
                    f"Backup exitoso: {output_file.name} "
                    f"({file_size:.2f} MB, {result.duration_seconds:.2f}s)"
                )
            else:
                self.logger.error(f"Backup fallido: {result.error}")
            
            return result
        
        except Exception as e:
            duration = time.time() - start_time
            self.logger.error(f"Error al ejecutar backup: {str(e)}")
            return BackupResult(
                database_name=db_config.name,
                success=False,
                error=str(e),
                duration_seconds=duration
            )

    def _validate_tools(self, tools: list) -> Optional[str]:
        """
        Valida que las herramientas necesarias estén disponibles
        
        Args:
            tools: Lista de herramientas requeridas
            
        Returns:
            None si todo está OK, mensaje de error en caso contrario
        """
        import shutil
        for tool in tools:
            if not shutil.which(tool):
                return f"La herramienta {tool} no está instalada"
        return None