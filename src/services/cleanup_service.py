"""
Servicio para limpiar backups antiguos (Single Responsibility)
"""
from datetime import datetime, timedelta
from pathlib import Path
from ..logger import LoggerService


class CleanupService:
    """Servicio para limpiar backups antiguos"""
    
    def __init__(self, retention_days: int):
        """
        Inicializa el servicio de limpieza
        
        Args:
            retention_days: Días de retención de backups
        """
        self.retention_days = retention_days
        self.logger = LoggerService.get_logger("CleanupService")
    
    def cleanup_old_backups(self, backup_dir: Path) -> int:
        """
        Elimina backups más antiguos que retention_days
        PROTEGE los backups anuales (archivos que empiezan con ANNUAL_)
        
        Args:
            backup_dir: Directorio de backups
            
        Returns:
            Cantidad de archivos eliminados
        """
        try:
            if not backup_dir.exists():
                self.logger.warning(f"Directorio de backups no existe: {backup_dir}")
                return 0
            
            now = datetime.now()
            cutoff_date = now - timedelta(days=self.retention_days)
            deleted_count = 0
            
            # Patrones de archivos a limpiar
            patterns = ['*.sql', '*.bak', '*.sql.gz', '*.bak.gz', '*.dump']
            
            for pattern in patterns:
                for backup_file in backup_dir.glob(pattern):
                    try:
                        # PROTEGER backups anuales
                        if backup_file.name.startswith('ANNUAL_'):
                            self.logger.debug(f"Protegiendo backup anual: {backup_file.name}")
                            continue
                        
                        file_mtime = datetime.fromtimestamp(backup_file.stat().st_mtime)
                        
                        if file_mtime < cutoff_date:
                            file_size = backup_file.stat().st_size / (1024 * 1024)  # MB
                            backup_file.unlink()
                            deleted_count += 1
                            self.logger.info(
                                f"Eliminado backup antiguo: {backup_file.name} "
                                f"({file_size:.2f} MB, {(now - file_mtime).days} días)"
                            )
                    except Exception as e:
                        self.logger.error(f"Error al eliminar {backup_file.name}: {e}")
            
            if deleted_count > 0:
                self.logger.info(
                    f"Limpieza completada: {deleted_count} archivo(s) eliminado(s)"
                )
            else:
                self.logger.info("No hay backups antiguos para eliminar")
            
            return deleted_count
            
        except Exception as e:
            self.logger.error(f"Error durante limpieza: {e}")
            return 0
    
    def get_backup_stats(self, backup_dir: Path) -> dict:
        """
        Obtiene estadísticas de los backups
        
        Args:
            backup_dir: Directorio de backups
            
        Returns:
            Diccionario con estadísticas
        """
        try:
            if not backup_dir.exists():
                return {
                    'total_files': 0,
                    'total_size_mb': 0,
                    'oldest_backup': None,
                    'newest_backup': None,
                    'annual_backups': 0,
                    'daily_backups': 0
                }
            
            files = (list(backup_dir.glob('*.sql')) + 
                    list(backup_dir.glob('*.bak')) + 
                    list(backup_dir.glob('*.dump')))
            
            if not files:
                return {
                    'total_files': 0,
                    'total_size_mb': 0,
                    'oldest_backup': None,
                    'newest_backup': None,
                    'annual_backups': 0,
                    'daily_backups': 0
                }
            
            total_size = sum(f.stat().st_size for f in files)
            oldest = min(files, key=lambda f: f.stat().st_mtime)
            newest = max(files, key=lambda f: f.stat().st_mtime)
            
            # Contar backups anuales vs diarios
            annual_count = sum(1 for f in files if f.name.startswith('ANNUAL_'))
            daily_count = len(files) - annual_count
            
            return {
                'total_files': len(files),
                'total_size_mb': total_size / (1024 * 1024),
                'oldest_backup': datetime.fromtimestamp(oldest.stat().st_mtime),
                'newest_backup': datetime.fromtimestamp(newest.stat().st_mtime),
                'annual_backups': annual_count,
                'daily_backups': daily_count
            }
            
        except Exception as e:
            self.logger.error(f"Error obteniendo estadísticas: {e}")
            return {
                'total_files': 0,
                'total_size_mb': 0,
                'oldest_backup': None,
                'newest_backup': None,
                'annual_backups': 0,
                'daily_backups': 0
            }