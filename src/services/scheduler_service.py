"""
Servicio de programación de tareas de backup
"""
import schedule
import time
import signal
import sys
from ..logger import LoggerService
from .backup_service import BackupService


class SchedulerService:
    """Servicio para programar y ejecutar backups automáticos"""
    
    def __init__(self, backup_service: BackupService):
        """
        Inicializa el servicio de programación
        
        Args:
            backup_service: Servicio de backup a ejecutar
        """
        self.backup_service = backup_service
        self.logger = LoggerService.get_logger("SchedulerService")
        self.running = False
        
        # Registrar manejadores de señales para shutdown graceful
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def start(self, run_immediately: bool = False):
        """
        Inicia el programador de tareas
        
        Args:
            run_immediately: Si es True, ejecuta un backup inmediatamente al iniciar
        """
        schedule_time = self.backup_service.backup_settings.schedule
        
        # Programar tarea diaria
        schedule.every().day.at(schedule_time).do(
            self._run_backup_job
        )
        
        self.logger.info("=" * 70)
        self.logger.info("SERVICIO DE BACKUP AUTOMÁTICO INICIADO")
        self.logger.info("=" * 70)
        self.logger.info(f"Programación: Diariamente a las {schedule_time}")
        self.logger.info(f"Retención de backups: {self.backup_service.backup_settings.retention_days} días")
        self.logger.info(f"Bases de datos configuradas: {len(self.backup_service.databases)}")
        
        for db in self.backup_service.databases:
            status = "✓ Habilitada" if db.enabled else "✗ Deshabilitada"
            self.logger.info(f"  - {db.name} ({db.type}): {status}")
        
        self.logger.info("-" * 70)
        self.logger.info(f"Próxima ejecución: {self.get_next_run()}")
        self.logger.info("Presiona Ctrl+C para detener el servicio")
        self.logger.info("=" * 70)
        
        # Ejecutar backup inmediatamente si se solicita
        if run_immediately:
            self.logger.info("Ejecutando backup inicial...")
            self._run_backup_job()
        
        # Loop principal
        self.running = True
        try:
            while self.running:
                schedule.run_pending()
                time.sleep(60)  # Revisar cada minuto
        except KeyboardInterrupt:
            self._shutdown()
    
    def _run_backup_job(self):
        """Ejecuta el trabajo de backup"""
        try:
            self.logger.info(f"Ejecutando backup programado a las {time.strftime('%Y-%m-%d %H:%M:%S')}")
            results = self.backup_service.backup_all_databases()
            
            # Verificar si hubo errores
            failed = [r for r in results if not r.success]
            if failed:
                self.logger.warning(
                    f"Backup completado con {len(failed)} error(es). "
                    "Revisa los logs para más detalles."
                )
            else:
                self.logger.info("Backup completado exitosamente")
                
        except Exception as e:
            self.logger.error(f"Error crítico durante backup: {e}", exc_info=True)
    
    def _signal_handler(self, signum, frame):
        """
        Manejador de señales para shutdown graceful
        
        Args:
            signum: Número de señal
            frame: Frame actual
        """
        try:
            signal_name = signal.Signals(signum).name
        except:
            signal_name = str(signum)
        
        self.logger.info(f"Señal recibida: {signal_name}")
        self._shutdown()
    
    def _shutdown(self):
        """Detiene el servicio de forma ordenada"""
        self.logger.info("Deteniendo servicio de backup...")
        self.running = False
        schedule.clear()
        self.logger.info("Servicio detenido correctamente")
        sys.exit(0)
    
    def get_next_run(self) -> str:
        """
        Obtiene el tiempo hasta la próxima ejecución
        
        Returns:
            String con el tiempo hasta la próxima ejecución
        """
        next_run = schedule.next_run()
        if next_run:
            return next_run.strftime('%Y-%m-%d %H:%M:%S')
        return "No hay ejecuciones programadas"