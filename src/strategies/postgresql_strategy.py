"""
Estrategia de backup para PostgreSQL
"""
import subprocess
import os
from pathlib import Path
from .base_strategy import BackupStrategy
from ..models import DatabaseConfig, BackupResult


class PostgreSQLBackupStrategy(BackupStrategy):
    """Estrategia de backup para PostgreSQL"""
    
    def backup(self, db_config: DatabaseConfig, output_file: Path) -> BackupResult:
        """
        Ejecuta backup de PostgreSQL usando pg_dump
        
        Args:
            db_config: Configuración de la base de datos
            output_file: Archivo de salida para el backup
            
        Returns:
            Resultado del backup
        """
        # Validar herramientas
        tool_error = self._validate_tools(['pg_dump'])
        if tool_error:
            return BackupResult(
                database_name=db_config.name,
                success=False,
                error=tool_error
            )
        
        try:
            # Configurar variable de entorno para password
            env = os.environ.copy()
            env['PGPASSWORD'] = db_config.password
            
            # Construir comando
            cmd = [
                'pg_dump',
                f'--host={db_config.host}',
                f'--port={db_config.port}',
                f'--username={db_config.user}',
                '--format=plain',        # Formato SQL plano
                '--clean',               # Incluir DROP statements
                '--if-exists',           # Usar IF EXISTS en DROP
                '--create',              # Incluir CREATE DATABASE
                '--encoding=UTF8',       # Encoding
                '--no-owner',            # No incluir comandos de ownership
                '--no-privileges',       # No incluir comandos de privilegios
                db_config.name
            ]
            
            # Ejecutar comando
            with open(output_file, 'w', encoding='utf-8') as f:
                result = subprocess.run(
                    cmd,
                    stdout=f,
                    stderr=subprocess.PIPE,
                    text=True,
                    env=env,
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