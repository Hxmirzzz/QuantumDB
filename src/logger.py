"""
Servicio de logging siguiendo principio Single Responsibility
"""
import logging
import sys
from datetime import datetime
from pathlib import Path
from .config import Config


class LoggerService:
    """Servicio centralizado de logging"""
    
    _loggers = {}
    
    @classmethod
    def get_logger(cls, name: str) -> logging.Logger:
        """
        Obtiene o crea un logger con el nombre especificado
        
        Args:
            name: Nombre del logger
            
        Returns:
            Logger configurado
        """
        if name in cls._loggers:
            return cls._loggers[name]
        
        logger = cls._setup_logger(name)
        cls._loggers[name] = logger
        return logger
    
    @classmethod
    def _setup_logger(cls, name: str) -> logging.Logger:
        """
        Configura un nuevo logger
        
        Args:
            name: Nombre del logger
            
        Returns:
            Logger configurado
        """
        Config.ensure_directories()
        
        logger = logging.getLogger(name)
        logger.setLevel(Config.LOG_LEVEL)
        
        # Evitar duplicar handlers
        if logger.handlers:
            return logger
        
        # Handler para archivo
        log_file = Config.LOG_DIR / f"{name}_{datetime.now().strftime('%Y%m%d')}.log"
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(Config.LOG_LEVEL)
        
        # Handler para consola
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(Config.LOG_LEVEL)
        
        # Formato
        formatter = logging.Formatter(Config.LOG_FORMAT)
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        
        return logger