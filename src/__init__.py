"""
Sistema de Backup Automático de Bases de Datos
"""
__version__ = "1.0.0"
__author__ = "Tu Nombre"

from .config import Config
from .logger import LoggerService

__all__ = ['Config', 'LoggerService']