"""
Estrategias de backup para diferentes motores de BD
"""
from .base_strategy import BackupStrategy
from .mysql_strategy import MySQLBackupStrategy
from .postgresql_strategy import PostgreSQLBackupStrategy
from .sqlserver_strategy import SQLServerBackupStrategy

__all__ = [
    'BackupStrategy',
    'MySQLBackupStrategy',
    'PostgreSQLBackupStrategy',
    'SQLServerBackupStrategy'
]