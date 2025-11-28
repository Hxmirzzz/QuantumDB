"""
Estrategia de backup para MySQL/MariaDB
"""
import subprocess
from pathlib import Path
from .base_strategy import BackupStrategy
from ..models import DatabaseConfig, BackupResult


class MySQLBackupStrategy(BackupStrategy):
    """Estrategia de backup para MySQL/MariaDB"""
    
    def backup(self, db_config: DatabaseConfig, output_file: Path) -> BackupResult:
        """
        Ejecuta backup de MySQL/MariaDB usando mysqldump
        
        Args:
            db_config: Configuración de la base de datos
            output_file: Archivo de salida para el backup
            
        Returns:
            Resultado del backup
        """
        # Validar herramientas
        tool_error = self._validate_tools(['mysqldump'])
        if tool_error:
            return BackupResult(
                database_name=db_config.name,
                success=False,
                error=tool_error
            )
        
        try:
            # Construir comando
            cmd = [
                'mysqldump',
                f'--host={db_config.host}',
                f'--port={db_config.port}',
                f'--user={db_config.user}',
                f'--password={db_config.password}',
                '--single-transaction',  # Para InnoDB sin bloqueo
                '--routines',            # Incluir procedures y functions
                '--triggers',            # Incluir triggers
                '--events',              # Incluir eventos
                '--set-gtid-purged=OFF', # Evitar problemas con GTID
                '--quick',               # Para tablas grandes
                '--lock-tables=false',   # No bloquear tablas
                '--add-drop-database',   # Agregar DROP DATABASE
                '--databases',           # Especificar que es una BD
                db_config.name
            ]
            
            # Ejecutar comando
            with open(output_file, 'w', encoding='utf-8') as f:
                result = subprocess.run(
                    cmd,
                    stdout=f,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=3600
                )
            
            if result.returncode == 0:
                return BackupResult(
                    database_name=db_config.name,
                    success=True,
                    output_file=str(output_file)
                )
            else:
                # Limpiar archivo de salida en caso de error
                if output_file.exists():
                    output_file.unlink()
                
                return BackupResult(
                    database_name=db_config.name,
                    success=False,
                    error=result.stderr
                )
                
        except subprocess.TimeoutExpired:
            if output_file.exists():
                output_file.unlink()
            return BackupResult(
                database_name=db_config.name,
                success=False,
                error="Timeout: El backup tardó más de 1 hora"
            )
        except Exception as e:
            # Limpiar archivo de salida en caso de error
            if output_file.exists():
                output_file.unlink()
            
            return BackupResult(
                database_name=db_config.name,
                success=False,
                error=str(e)
            )