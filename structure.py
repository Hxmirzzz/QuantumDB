"""
DailyBackupDatabase/
│
├── src/
│   ├── __init__.py
│   ├── config.py                 # Configuración y constantes
│   ├── logger.py                 # Servicio de logging
│   ├── models.py                 # Modelos de datos
│   ├── repositories/
│   │   ├── __init__.py
│   │   └── config_repository.py  # Repositorio de configuración
│   ├── strategies/
│   │   ├── __init__.py
│   │   ├── base_strategy.py      # Estrategia base abstracta
│   │   ├── mysql_strategy.py     # Estrategia MySQL
│   │   ├── postgresql_strategy.py # Estrategia PostgreSQL
│   │   └── sqlserver_strategy.py # Estrategia SQL Server
│   ├── services/
│   │   ├── __init__.py
│   │   ├── backup_service.py     # Servicio principal de backup
│   │   ├── cleanup_service.py    # Servicio de limpieza
│   │   └── scheduler_service.py  # Servicio de programación
│   └── factories/
│       ├── __init__.py
│       └── strategy_factory.py   # Factory de estrategias
│
├── tests/
│   ├── __init__.py
│   └── test_backup.py            # Tests unitarios
│
├── scripts/
│   ├── install_windows_service.bat
│   └── install_linux_service.sh
│
├── main.py                       # Punto de entrada
├── requirements.txt
├── .env.example
├── .gitignore
├── config.json.example
└── README.md
"""