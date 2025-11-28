"""
Tests unitarios para el sistema de backup
"""
import unittest
from pathlib import Path
import tempfile
import shutil
import sys

# Agregar src al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import Config
from src.models import DatabaseConfig, BackupSettings, BackupResult
from src.repositories.config_repository import ConfigRepository
from src.factories.strategy_factory import BackupStrategyFactory
from src.services.cleanup_service import CleanupService


class TestModels(unittest.TestCase):
    """Tests para modelos de datos"""
    
    def test_database_config_creation(self):
        """Test creación de DatabaseConfig"""
        db = DatabaseConfig(
            name="test_db",
            type="mysql",
            host="localhost",
            port=3306,
            user="root",
            password="password"
        )
        self.assertEqual(db.name, "test_db")
        self.assertEqual(db.type, "mysql")
        self.assertTrue(db.enabled)
    
    def test_database_config_validation(self):
        """Test validación de DatabaseConfig"""
        with self.assertRaises(ValueError):
            DatabaseConfig(
                name="",  # Nombre vacío debe fallar
                type="mysql",
                host="localhost",
                port=3306,
                user="root",
                password="password"
            )
    
    def test_backup_settings_creation(self):
        """Test creación de BackupSettings"""
        settings = BackupSettings(
            retention_days=7,
            schedule="02:00",
            compress=True
        )
        self.assertEqual(settings.retention_days, 7)
        self.assertEqual(settings.schedule, "02:00")
    
    def test_backup_settings_time_validation(self):
        """Test validación de formato de tiempo"""
        with self.assertRaises(ValueError):
            BackupSettings(
                retention_days=7,
                schedule="25:00"  # Hora inválida
            )
    
    def test_backup_result_creation(self):
        """Test creación de BackupResult"""
        result = BackupResult(
            database_name="test_db",
            success=True,
            output_file="/path/to/backup.sql",
            duration_seconds=5.5
        )
        self.assertTrue(result.success)
        self.assertIn("test_db", str(result))


class TestConfigRepository(unittest.TestCase):
    """Tests para ConfigRepository"""
    
    def setUp(self):
        """Setup para tests"""
        self.temp_dir = tempfile.mkdtemp()
        self.config_file = Path(self.temp_dir) / "test_config.json"
        self.repo = ConfigRepository(self.config_file)
    
    def tearDown(self):
        """Cleanup después de tests"""
        if Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)
    
    def test_load_nonexistent_config(self):
        """Test cargar configuración inexistente"""
        config = self.repo.load()
        self.assertIsNotNone(config)
        self.assertIn('databases', config)
    
    def test_save_and_load_config(self):
        """Test guardar y cargar configuración"""
        test_config = {
            "databases": [{
                "name": "test_db",
                "type": "mysql",
                "host": "localhost",
                "port": 3306,
                "user": "root",
                "password": "pass",
                "enabled": True
            }],
            "backup_settings": {
                "retention_days": 7,
                "schedule": "02:00"
            }
        }
        
        self.assertTrue(self.repo.save(test_config))
        loaded = self.repo.load()
        self.assertEqual(loaded['databases'][0]['name'], 'test_db')
    
    def test_get_databases(self):
        """Test obtener lista de bases de datos"""
        databases = self.repo.get_databases()
        self.assertIsInstance(databases, list)
    
    def test_get_backup_settings(self):
        """Test obtener configuración de backup"""
        settings = self.repo.get_backup_settings()
        self.assertIsInstance(settings, BackupSettings)


class TestBackupStrategyFactory(unittest.TestCase):
    """Tests para BackupStrategyFactory"""
    
    def test_create_mysql_strategy(self):
        """Test crear estrategia MySQL"""
        strategy = BackupStrategyFactory.create('mysql')
        self.assertIsNotNone(strategy)
        self.assertEqual(strategy.__class__.__name__, 'MySQLBackupStrategy')
    
    def test_create_postgresql_strategy(self):
        """Test crear estrategia PostgreSQL"""
        strategy = BackupStrategyFactory.create('postgresql')
        self.assertIsNotNone(strategy)
        self.assertEqual(strategy.__class__.__name__, 'PostgreSQLBackupStrategy')
    
    def test_create_sqlserver_strategy(self):
        """Test crear estrategia SQL Server"""
        strategy = BackupStrategyFactory.create('sqlserver')
        self.assertIsNotNone(strategy)
        self.assertEqual(strategy.__class__.__name__, 'SQLServerBackupStrategy')
    
    def test_create_unsupported_strategy(self):
        """Test crear estrategia no soportada"""
        strategy = BackupStrategyFactory.create('oracle')
        self.assertIsNone(strategy)
    
    def test_get_supported_types(self):
        """Test obtener tipos soportados"""
        types = BackupStrategyFactory.get_supported_types()
        self.assertIn('mysql', types)
        self.assertIn('postgresql', types)
        self.assertIn('sqlserver', types)


class TestCleanupService(unittest.TestCase):
    """Tests para CleanupService"""
    
    def setUp(self):
        """Setup para tests"""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.service = CleanupService(retention_days=7)
    
    def tearDown(self):
        """Cleanup después de tests"""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
    
    def test_cleanup_nonexistent_directory(self):
        """Test limpieza de directorio inexistente"""
        fake_dir = self.temp_dir / "fake"
        deleted = self.service.cleanup_old_backups(fake_dir)
        self.assertEqual(deleted, 0)
    
    def test_get_backup_stats_empty_dir(self):
        """Test estadísticas de directorio vacío"""
        stats = self.service.get_backup_stats(self.temp_dir)
        self.assertEqual(stats['total_files'], 0)
        self.assertEqual(stats['total_size_mb'], 0)
    
    def test_get_backup_stats_with_files(self):
        """Test estadísticas con archivos"""
        # Crear archivo de prueba
        test_file = self.temp_dir / "test_backup.sql"
        test_file.write_text("test content")
        
        stats = self.service.get_backup_stats(self.temp_dir)
        self.assertEqual(stats['total_files'], 1)
        self.assertGreater(stats['total_size_mb'], 0)


def run_tests():
    """Ejecuta todos los tests"""
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(sys.modules[__name__])
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)