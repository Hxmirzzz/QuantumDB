"""
Factory para crear estrategias de backup
"""
from typing import Optional
from ..strategies.base_strategy import BackupStrategy
from ..strategies.mysql_strategy import MySQLBackupStrategy
from ..strategies.postgresql_strategy import PostgreSQLBackupStrategy
from ..strategies.sqlserver_strategy import SQLServerBackupStrategy


class BackupStrategyFactory:
    """Factory para crear estrategias de backup (Factory Pattern)"""
    
    # Mapeo de tipos a estrategias
    _strategies = {
        'mysql': MySQLBackupStrategy,
        'mariadb': MySQLBackupStrategy,
        'postgresql': PostgreSQLBackupStrategy,
        'postgres': PostgreSQLBackupStrategy,
        'sqlserver': SQLServerBackupStrategy,
        'mssql': SQLServerBackupStrategy,
    }
    
    @classmethod
    def create(cls, db_type: str) -> Optional[BackupStrategy]:
        """
        Crea una estrategia de backup según el tipo de base de datos
        
        Args:
            db_type: Tipo de base de datos (mysql, postgresql, sqlserver, etc.)
            
        Returns:
            Instancia de BackupStrategy o None si el tipo no es soportado
        """
        strategy_class = cls._strategies.get(db_type.lower())
        if strategy_class:
            return strategy_class()
        return None
    
    @classmethod
    def register_strategy(cls, db_type: str, strategy_class: type):
        """
        Registra una nueva estrategia (permite extender sin modificar - Open/Closed)
        
        Args:
            db_type: Tipo de base de datos
            strategy_class: Clase de estrategia a registrar
        """
        cls._strategies[db_type.lower()] = strategy_class
    
    @classmethod
    def get_supported_types(cls) -> list:
        """
        Obtiene lista de tipos de base de datos soportados
        
        Returns:
            Lista de tipos soportados
        """
        return list(cls._strategies.keys())