"""
Estrategia de backup para SQL Server
"""
import subprocess
from pathlib import Path
from .base_strategy import BackupStrategy
from ..models import DatabaseConfig, BackupResult


class SQLServerBackupStrategy(BackupStrategy):
    """Estrategia de backup para SQL Server"""
    
    def backup(self, db_config: DatabaseConfig, output_file: Path) -> BackupResult:
        """
        Ejecuta backup de SQL Server
        
        Args:
            db_config: Configuración de la base de datos
            output_file: Archivo de salida para el backup
            
        Returns:
            Resultado del backup
        """
        # Validar herramientas - sqlcmd debe estar instalado
        tool_error = self._validate_tools(['sqlcmd'])
        if tool_error:
            return BackupResult(
                database_name=db_config.name,
                success=False,
                error=tool_error
            )
        
        try:
            # Determinar el nombre de la base de datos
            database_name = db_config.database or db_config.name
            
            # Generar archivo .bak
            backup_file = output_file.with_suffix('.bak')
            
            # Construir comando SQL para backup
            sql_query = f"""
            BACKUP DATABASE [{database_name}] 
            TO DISK = N'{backup_file}' 
            WITH FORMAT, 
                 INIT, 
                 NAME = N'{database_name}-Full Database Backup', 
                 SKIP, 
                 NOREWIND, 
                 NOUNLOAD, 
                 COMPRESSION, 
                 STATS = 10
            """
            
            # Construir comando sqlcmd
            cmd = [
                'sqlcmd',
                '-S', db_config.host,
                '-U', db_config.user,
                '-P', db_config.password,
                '-Q', sql_query
            ]
            
            # Si se especifica un puerto diferente al default (1433)
            if db_config.port != 1433:
                cmd[2] = f'{db_config.host},{db_config.port}'
            
            self.logger.info(f"Ejecutando backup de SQL Server: {database_name}")
            
            # Ejecutar comando
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=3600  # Timeout de 1 hora
            )
            
            if result.returncode == 0:
                # También intentar generar script SQL
                self._generate_sql_script(db_config, output_file)
                
                return BackupResult(
                    database_name=db_config.name,
                    success=True,
                    output_file=str(backup_file)
                )
            else:
                # Limpiar archivo en caso de error
                if backup_file.exists():
                    backup_file.unlink()
                
                error_msg = result.stderr or result.stdout or "Error desconocido"
                return BackupResult(
                    database_name=db_config.name,
                    success=False,
                    error=error_msg
                )
                
        except subprocess.TimeoutExpired:
            return BackupResult(
                database_name=db_config.name,
                success=False,
                error="Timeout: El backup tardó más de 1 hora"
            )
        except Exception as e:
            # Limpiar archivos en caso de error
            if backup_file.exists():
                backup_file.unlink()
            
            return BackupResult(
                database_name=db_config.name,
                success=False,
                error=str(e)
            )
    
    def _generate_sql_script(self, db_config: DatabaseConfig, output_file: Path):
        """
        Genera script SQL adicional con la estructura de la BD
        
        Args:
            db_config: Configuración de la base de datos
            output_file: Archivo de salida para el script
        """
        try:
            database_name = db_config.database or db_config.name
            
            # Query para obtener script de tablas
            sql_query = f"""
            USE [{database_name}];
            SELECT 
                'CREATE TABLE [' + SCHEMA_NAME(t.schema_id) + '].[' + t.name + '] (' + CHAR(13) +
                STUFF((
                    SELECT ',' + CHAR(13) + '    [' + c.name + '] ' + 
                           TYPE_NAME(c.user_type_id) +
                           CASE 
                               WHEN c.max_length = -1 THEN '(MAX)'
                               WHEN TYPE_NAME(c.user_type_id) IN ('varchar', 'char', 'nvarchar', 'nchar') 
                               THEN '(' + CAST(c.max_length AS VARCHAR) + ')'
                               WHEN TYPE_NAME(c.user_type_id) IN ('decimal', 'numeric')
                               THEN '(' + CAST(c.precision AS VARCHAR) + ',' + CAST(c.scale AS VARCHAR) + ')'
                               ELSE ''
                           END +
                           CASE WHEN c.is_nullable = 0 THEN ' NOT NULL' ELSE ' NULL' END
                    FROM sys.columns c
                    WHERE c.object_id = t.object_id
                    ORDER BY c.column_id
                    FOR XML PATH('')
                ), 1, 1, '') + CHAR(13) + ');' + CHAR(13) + 'GO' + CHAR(13)
            FROM sys.tables t
            WHERE t.is_ms_shipped = 0
            FOR XML PATH(''), TYPE
            """
            
            cmd = [
                'sqlcmd',
                '-S', db_config.host,
                '-U', db_config.user,
                '-P', db_config.password,
                '-d', database_name,
                '-Q', sql_query,
                '-o', str(output_file),
                '-y', '0'  # Sin límite de ancho
            ]
            
            # Ejecutar comando
            subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            self.logger.info(f"Script SQL generado: {output_file}")
            
        except Exception as e:
            self.logger.warning(f"No se pudo generar script SQL: {e}")