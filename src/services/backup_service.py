"""
Servicio principal que orquesta los backups
"""
from datetime import datetime
from pathlib import Path
from typing import List
from ..config import Config
from ..logger import LoggerService
from ..models import DatabaseConfig, BackupResult
from ..repositories.config_repository import ConfigRepository
from ..factories.strategy_factory import BackupStrategyFactory
from .cleanup_service import CleanupService


class BackupService:
    """Servicio principal que orquesta los backups"""
    
    def __init__(self, config_repo: ConfigRepository):
        """
        Inicializa el servicio de backup
        
        Args:
            config_repo: Repositorio de configuración
        """
        self.config_repo = config_repo
        self.logger = LoggerService.get_logger("BackupService")
        
        # Cargar configuración
        self.databases = config_repo.get_databases()
        self.backup_settings = config_repo.get_backup_settings()
        
        # Crear directorios necesarios
        Config.ensure_directories()
        
        # Servicio de limpieza
        self.cleanup_service = CleanupService(self.backup_settings.retention_days)
    
    def backup_all_databases(self) -> List[BackupResult]:
        """
        Realiza backup de todas las bases de datos configuradas
        
        Returns:
            Lista de resultados de backup
        """
        self.logger.info("=" * 70)
        self.logger.info("INICIANDO PROCESO DE BACKUP AUTOMÁTICO")
        self.logger.info("=" * 70)
        
        results = []
        
        for db_config in self.databases:
            if not db_config.enabled:
                self.logger.info(f"Base de datos deshabilitada: {db_config.name}")
                continue
            
            result = self._backup_single_database(db_config)
            results.append(result)
        
        # Limpieza de backups antiguos
        self.logger.info("-" * 70)
        deleted_count = self.cleanup_service.cleanup_old_backups(Config.BACKUP_DIR)
        
        # Estadísticas
        self._print_summary(results, deleted_count)
        
        return results
    
    def _backup_single_database(self, db_config: DatabaseConfig) -> BackupResult:
        """
        Realiza backup de una base de datos
        
        Args:
            db_config: Configuración de la base de datos
            
        Returns:
            Resultado del backup
        """
        self.logger.info("-" * 70)
        
        # Crear estrategia de backup
        strategy = BackupStrategyFactory.create(db_config.type)
        if not strategy:
            error_msg = f"Tipo de base de datos no soportado: {db_config.type}"
            self.logger.error(error_msg)
            return BackupResult(
                database_name=db_config.name,
                success=False,
                error=error_msg
            )
        
        # Generar nombre de archivo
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Extensión según tipo de BD
        if db_config.type.lower() in ['sqlserver', 'mssql']:
            output_file = Config.BACKUP_DIR / f"{db_config.name}_{timestamp}.bak"
        else:
            output_file = Config.BACKUP_DIR / f"{db_config.name}_{timestamp}.sql"
        
        # Ejecutar backup
        return strategy.execute_backup(db_config, output_file)
    
    def _print_summary(self, results: List[BackupResult], deleted_count: int):
        """
        Imprime resumen de la operación de backup
        
        Args:
            results: Lista de resultados
            deleted_count: Cantidad de archivos eliminados
        """
        success_count = sum(1 for r in results if r.success)
        failed_count = len(results) - success_count
        total_time = sum(r.duration_seconds for r in results)
        
        self.logger.info("=" * 70)
        self.logger.info("RESUMEN DEL PROCESO DE BACKUP")
        self.logger.info("=" * 70)
        
        # Resultados individuales
        for result in results:
            status = "✓ EXITOSO" if result.success else "✗ FALLIDO"
            self.logger.info(f"{status}: {result.database_name} ({result.duration_seconds:.2f}s)")
            if not result.success:
                self.logger.error(f"  Error: {result.error}")
        
        self.logger.info("-" * 70)
        self.logger.info(f"Total de bases de datos procesadas: {len(results)}")
        self.logger.info(f"Backups exitosos: {success_count}")
        self.logger.info(f"Backups fallidos: {failed_count}")
        self.logger.info(f"Tiempo total: {total_time:.2f}s")
        self.logger.info(f"Backups antiguos eliminados: {deleted_count}")
        
        # Estadísticas de almacenamiento
        stats = self.cleanup_service.get_backup_stats(Config.BACKUP_DIR)
        self.logger.info(f"Backups almacenados: {stats['total_files']} archivo(s)")
        self.logger.info(f"Espacio utilizado: {stats['total_size_mb']:.2f} MB")
        
        self.logger.info("=" * 70)
        
        if failed_count > 0:
            self.logger.warning(
                f"ATENCIÓN: {failed_count} backup(s) fallaron. "
                "Revisa los errores arriba."
            )
    
    def backup_specific_database(self, database_name: str) -> BackupResult:
        """
        Realiza backup de una base de datos específica
        
        Args:
            database_name: Nombre de la base de datos
            
        Returns:
            Resultado del backup
        """
        for db_config in self.databases:
            if db_config.name == database_name:
                if not db_config.enabled:
                    self.logger.warning(
                        f"Base de datos deshabilitada: {database_name}"
                    )
                    return BackupResult(
                        database_name=database_name,
                        success=False,
                        error="Base de datos deshabilitada en configuración"
                    )
                
                return self._backup_single_database(db_config)
        
        error_msg = f"Base de datos no encontrada en configuración: {database_name}"
        self.logger.error(error_msg)
        return BackupResult(
            database_name=database_name,
            success=False,
            error=error_msg
        )