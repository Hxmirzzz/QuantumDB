"""
Estrategia de backup para SQL Server
Genera script SQL completo con estructura y datos
"""
import subprocess
from pathlib import Path
from datetime import datetime
import codecs
from .base_strategy import BackupStrategy
from ..models import DatabaseConfig, BackupResult


class SQLServerBackupStrategy(BackupStrategy):
    """Estrategia de backup para SQL Server"""
    
    def backup(self, db_config: DatabaseConfig, output_file: Path) -> BackupResult:
        """
        Ejecuta backup de SQL Server generando script SQL completo
        
        Args:
            db_config: Configuración de la base de datos
            output_file: Archivo de salida para el backup
            
        Returns:
            Resultado del backup
        """
        # Validar herramientas
        tool_error = self._validate_tools(['sqlcmd'])
        if tool_error:
            return BackupResult(
                database_name=db_config.name,
                success=False,
                error=tool_error
            )
        
        try:
            database_name = db_config.database or db_config.name
            script_file = output_file.with_suffix('.sql')
            
            self.logger.info(f"Generando backup SQL completo de: {database_name}")
            self.logger.info(f"Archivo destino: {script_file}")
            self.logger.info("GENERANDO: Estructura + Datos")

            # Validar credenciales
            if not db_config.user or not db_config.password:
                return BackupResult(
                    database_name=db_config.name,
                    success=False,
                    error="Usuario o contraseña no configurados"
                )
            
            if '${' in db_config.user or '${' in db_config.password:
                return BackupResult(
                    database_name=db_config.name,
                    success=False,
                    error="Variables de entorno no resueltas correctamente"
                )

            # Crear directorio si no existe
            script_file.parent.mkdir(parents=True, exist_ok=True)

            # Inicializar archivo con encabezado
            with open(script_file, 'w', encoding='utf-8-sig') as f:
                f.write(f"-- =============================================\n")
                f.write(f"-- BACKUP DE BASE DE DATOS: {database_name}\n")
                f.write(f"-- Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"-- Servidor: {self._get_server_string(db_config)}\n")
                f.write(f"-- =============================================\n\n")
                f.write(f"USE [{database_name}];\nGO\n\n")

            # Paso 1: Generar estructura
            self.logger.info("Paso 1/2: Generando estructura de la base de datos...")
            if not self._generate_schema(db_config, database_name, script_file):
                return BackupResult(
                    database_name=db_config.name,
                    success=False,
                    error="Error al generar estructura de la BD"
                )
            
            # Paso 2: Generar datos
            self.logger.info("Paso 2/2: Generando datos de todas las tablas...")
            if not self._generate_data(db_config, database_name, script_file):
                return BackupResult(
                    database_name=db_config.name,
                    success=False,
                    error="Error al generar datos de la BD"
                )
            
            # Verificar tamaño final
            if script_file.exists():
                file_size = script_file.stat().st_size / (1024 * 1024)
                self.logger.info(f"✓ Backup completado: {script_file.name} ({file_size:.2f} MB)")
                
                return BackupResult(
                    database_name=db_config.name,
                    success=True,
                    output_file=str(script_file)
                )
            else:
                return BackupResult(
                    database_name=db_config.name,
                    success=False,
                    error="El archivo no se generó correctamente"
                )

        except subprocess.TimeoutExpired:
            return BackupResult(
                database_name=db_config.name,
                success=False,
                error="Timeout: El backup tardó más de 1 hora"
            )
        except Exception as e:
            self.logger.error(f"Error inesperado: {e}")
            if 'script_file' in locals() and script_file.exists():
                try:
                    script_file.unlink()
                except:
                    pass
            return BackupResult(
                database_name=db_config.name,
                success=False,
                error=str(e)
            )

    def _generate_schema(self, db_config: DatabaseConfig, database_name: str, script_file: Path) -> bool:
        """Genera la estructura de la BD (tablas, PKs, FKs, índices)"""
        
        try:
            with open(script_file, 'a', encoding='utf-8-sig') as f:
                f.write("-- =============================================\n")
                f.write("-- ESTRUCTURA DE LA BASE DE DATOS\n")
                f.write("-- =============================================\n\n")
            
            # Obtener lista de tablas
            tables_query = """
            SET NOCOUNT ON;
            SELECT s.name + '.' + t.name
            FROM sys.tables t
            INNER JOIN sys.schemas s ON t.schema_id = s.schema_id
            WHERE t.is_ms_shipped = 0
            ORDER BY s.name, t.name;
            """
            
            cmd = [
                'sqlcmd',
                '-S', self._get_server_string(db_config),
                '-U', db_config.user,
                '-P', db_config.password,
                '-d', database_name,
                '-Q', tables_query,
                '-h', '-1',
                '-W',
                '-s', '|',
                '-C',
                '-f', '65001'  # UTF-8 encoding
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60, encoding='utf-8')
            
            if result.returncode != 0:
                self.logger.error(f"Error obteniendo tablas: {result.stderr}")
                return False
            
            tables = [t.strip() for t in result.stdout.splitlines() if t.strip()]
            
            if not tables:
                self.logger.warning("No se encontraron tablas en la base de datos")
                return True
            
            self.logger.info(f"  Exportando estructura de {len(tables)} tablas...")
            
            # Generar CREATE TABLE para cada tabla
            for i, table in enumerate(tables, 1):
                schema, table_name = table.split('.')
                self.logger.info(f"    [{i}/{len(tables)}] {schema}.{table_name}")
                
                if not self._generate_table_ddl(db_config, database_name, schema, table_name, script_file):
                    self.logger.error(f"Error generando DDL de {schema}.{table_name}")
                    return False
            
            self.logger.info("  ✓ Estructura generada correctamente")
            return True
            
        except Exception as e:
            self.logger.error(f"Error en _generate_schema: {e}")
            return False
    
    def _generate_table_ddl(self, db_config: DatabaseConfig, database_name: str, 
                            schema: str, table_name: str, script_file: Path) -> bool:
        """Genera el DDL de una tabla específica"""
        
        try:
            # Query para obtener definición de columnas
            ddl_query = f"""
            SET NOCOUNT ON;
            
            DECLARE @TableName NVARCHAR(128) = N'{table_name}';
            DECLARE @SchemaName NVARCHAR(128) = N'{schema}';
            DECLARE @SQL NVARCHAR(MAX) = '';
            
            -- DROP TABLE si existe
            PRINT '-- Tabla: [' + @SchemaName + '].[' + @TableName + ']';
            PRINT 'IF OBJECT_ID(''[' + @SchemaName + '].[' + @TableName + ']'', ''U'') IS NOT NULL';
            PRINT '    DROP TABLE [' + @SchemaName + '].[' + @TableName + '];';
            PRINT 'GO';
            PRINT '';
            
            -- CREATE TABLE
            SET @SQL = 'CREATE TABLE [' + @SchemaName + '].[' + @TableName + '] (';
            
            SELECT @SQL = @SQL + CHAR(13) + CHAR(10) + '    [' + c.name + '] ' + 
                TYPE_NAME(c.user_type_id) +
                CASE 
                    WHEN c.max_length = -1 THEN '(MAX)'
                    WHEN TYPE_NAME(c.user_type_id) IN ('varchar', 'char', 'varbinary', 'binary') 
                    THEN '(' + CAST(c.max_length AS VARCHAR) + ')'
                    WHEN TYPE_NAME(c.user_type_id) IN ('nvarchar', 'nchar') 
                    THEN '(' + CAST(c.max_length/2 AS VARCHAR) + ')'
                    WHEN TYPE_NAME(c.user_type_id) IN ('decimal', 'numeric')
                    THEN '(' + CAST(c.precision AS VARCHAR) + ',' + CAST(c.scale AS VARCHAR) + ')'
                    ELSE ''
                END +
                CASE 
                    WHEN c.is_identity = 1 THEN ' IDENTITY(1,1)' 
                    ELSE '' 
                END +
                CASE 
                    WHEN c.is_nullable = 0 THEN ' NOT NULL' 
                    ELSE ' NULL' 
                END +
                CASE 
                    WHEN c.column_id < (SELECT MAX(column_id) FROM sys.columns WHERE object_id = c.object_id) 
                    THEN ',' 
                    ELSE '' 
                END
            FROM sys.columns c
            WHERE c.object_id = OBJECT_ID('[' + @SchemaName + '].[' + @TableName + ']')
            ORDER BY c.column_id;
            
            SET @SQL = @SQL + CHAR(13) + CHAR(10) + ');';
            PRINT @SQL;
            PRINT 'GO';
            PRINT '';
            
            -- PRIMARY KEY si existe
            IF EXISTS (SELECT 1 FROM sys.indexes WHERE object_id = OBJECT_ID('[' + @SchemaName + '].[' + @TableName + ']') AND is_primary_key = 1)
            BEGIN
                DECLARE @PKName NVARCHAR(128);
                DECLARE @PKColumns NVARCHAR(MAX) = '';
                
                SELECT @PKName = i.name
                FROM sys.indexes i
                WHERE i.object_id = OBJECT_ID('[' + @SchemaName + '].[' + @TableName + ']') 
                    AND i.is_primary_key = 1;
                
                SELECT @PKColumns = @PKColumns + 
                    CASE WHEN @PKColumns = '' THEN '' ELSE ', ' END +
                    '[' + c.name + ']' +
                    CASE WHEN ic.is_descending_key = 1 THEN ' DESC' ELSE ' ASC' END
                FROM sys.index_columns ic
                INNER JOIN sys.columns c ON ic.object_id = c.object_id AND ic.column_id = c.column_id
                WHERE ic.object_id = OBJECT_ID('[' + @SchemaName + '].[' + @TableName + ']')
                    AND ic.index_id = (SELECT index_id FROM sys.indexes 
                                        WHERE object_id = OBJECT_ID('[' + @SchemaName + '].[' + @TableName + ']') 
                                        AND is_primary_key = 1)
                ORDER BY ic.key_ordinal;
                
                PRINT 'ALTER TABLE [' + @SchemaName + '].[' + @TableName + ']';
                PRINT '    ADD CONSTRAINT [' + @PKName + '] PRIMARY KEY CLUSTERED (' + @PKColumns + ');';
                PRINT 'GO';
                PRINT '';
            END
            """
            
            cmd = [
                'sqlcmd',
                '-S', self._get_server_string(db_config),
                '-U', db_config.user,
                '-P', db_config.password,
                '-d', database_name,
                '-Q', ddl_query,
                '-y', '0',
                '-w', '8000',
                '-C',
                '-f', '65001'
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60, encoding='utf-8')
            
            if result.returncode == 0:
                with open(script_file, 'a', encoding='utf-8-sig') as f:
                    f.write(result.stdout)
                    f.write('\n')
                return True
            else:
                self.logger.error(f"Error: {result.stderr}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error en _generate_table_ddl: {e}")
            return False
    
    def _generate_data(self, db_config: DatabaseConfig, database_name: str, script_file: Path) -> bool:
        """Genera los INSERT statements para todas las tablas usando método más confiable"""
        
        try:
            with open(script_file, 'a', encoding='utf-8-sig') as f:
                f.write("\n-- =============================================\n")
                f.write("-- DATOS DE LAS TABLAS\n")
                f.write("-- =============================================\n\n")
            
            # Obtener lista de tablas
            tables_query = """
            SET NOCOUNT ON;
            SELECT s.name + '.' + t.name
            FROM sys.tables t
            INNER JOIN sys.schemas s ON t.schema_id = s.schema_id
            WHERE t.is_ms_shipped = 0
            ORDER BY s.name, t.name;
            """
            
            cmd = [
                'sqlcmd',
                '-S', self._get_server_string(db_config),
                '-U', db_config.user,
                '-P', db_config.password,
                '-d', database_name,
                '-Q', tables_query,
                '-h', '-1',
                '-W',
                '-C',
                '-f', '65001'
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60, encoding='utf-8')
            tables = [t.strip() for t in result.stdout.splitlines() if t.strip()]
            
            if not tables:
                self.logger.warning("No hay tablas para exportar datos")
                return True
            
            self.logger.info(f"  Exportando datos de {len(tables)} tablas...")
            
            for i, table in enumerate(tables, 1):
                schema, table_name = table.split('.')
                self.logger.info(f"    [{i}/{len(tables)}] {schema}.{table_name}...")
                
                if not self._generate_table_inserts_safe(db_config, database_name, schema, table_name, script_file):
                    self.logger.warning(f"No se pudieron exportar datos de {schema}.{table_name}")
            
            self.logger.info("  ✓ Datos exportados")
            return True
            
        except Exception as e:
            self.logger.error(f"Error en _generate_data: {e}")
            return False
    
    def _generate_table_inserts_safe(self, db_config: DatabaseConfig, database_name: str,
                                    schema: str, table_name: str, script_file: Path) -> bool:
        """Genera los INSERT usando BCP para mejor manejo de caracteres especiales"""
        
        try:
            # Primero verificar si la tabla tiene datos
            count_query = f"SET NOCOUNT ON; SELECT COUNT(*) FROM [{schema}].[{table_name}];"
            
            cmd_count = [
                'sqlcmd',
                '-S', self._get_server_string(db_config),
                '-U', db_config.user,
                '-P', db_config.password,
                '-d', database_name,
                '-Q', count_query,
                '-h', '-1',
                '-W',
                '-C',
                '-f', '65001'
            ]
            
            result = subprocess.run(cmd_count, capture_output=True, text=True, timeout=30, encoding='utf-8')
            count = int(result.stdout.strip()) if result.stdout.strip().isdigit() else 0
            
            if count == 0:
                return True  # No hay datos, continuar
            
            self.logger.info(f"      {count} registros encontrados")
            
            # Usar BCP para exportar datos en formato compatible
            temp_file = script_file.parent / f"temp_{schema}_{table_name}.bcp"
            
            bcp_cmd = [
                'bcp',
                f'[{database_name}].{schema}.{table_name}',
                'out',
                str(temp_file),
                '-S', self._get_server_string(db_config),
                '-U', db_config.user,
                '-P', db_config.password,
                '-c',  # Character mode
                '-t,',  # Field terminator
                '-r\\n',  # Row terminator
                '-C', '65001'  # UTF-8 code page
            ]
            
            # Exportar datos con BCP
            result = subprocess.run(bcp_cmd, capture_output=True, text=True, timeout=120)
            
            if result.returncode != 0:
                self.logger.warning(f"BCP falló para {schema}.{table_name}: {result.stderr}")
                # Intentar método alternativo
                return self._generate_table_inserts_fallback(db_config, database_name, schema, table_name, script_file)
            
            # Obtener estructura de columnas
            columns_query = f"""
            SET NOCOUNT ON;
            SELECT c.name, t.name as type_name, c.max_length, c.precision, c.scale, c.is_nullable
            FROM sys.columns c
            JOIN sys.types t ON c.user_type_id = t.user_type_id
            WHERE c.object_id = OBJECT_ID('[{schema}].[{table_name}]')
            ORDER BY c.column_id;
            """
            
            cmd_cols = [
                'sqlcmd',
                '-S', self._get_server_string(db_config),
                '-U', db_config.user,
                '-P', db_config.password,
                '-d', database_name,
                '-Q', columns_query,
                '-h', '-1',
                '-s', '|',
                '-W',
                '-C',
                '-f', '65001'
            ]
            
            result_cols = subprocess.run(cmd_cols, capture_output=True, text=True, timeout=30, encoding='utf-8')
            columns = []
            
            for line in result_cols.stdout.strip().split('\n'):
                if line and '|' in line:
                    col_name, col_type, max_len, precision, scale, nullable = line.split('|')
                    columns.append({
                        'name': col_name.strip(),
                        'type': col_type.strip().lower(),
                        'max_length': int(max_len) if max_len.strip() else 0,
                        'precision': int(precision) if precision.strip() else 0,
                        'scale': int(scale) if scale.strip() else 0,
                        'nullable': nullable.strip() == '1'
                    })
            
            # Leer archivo BCP y generar INSERTs
            with open(script_file, 'a', encoding='utf-8-sig') as f:
                f.write(f"\n-- Datos de [{schema}].[{table_name}] ({count} registros)\n")
                
                # Check for identity column
                identity_query = f"""
                SELECT COUNT(*) 
                FROM sys.columns 
                WHERE object_id = OBJECT_ID('[{schema}].[{table_name}]') 
                AND is_identity = 1;
                """
                
                cmd_identity = [
                    'sqlcmd',
                    '-S', self._get_server_string(db_config),
                    '-U', db_config.user,
                    '-P', db_config.password,
                    '-d', database_name,
                    '-Q', identity_query,
                    '-h', '-1',
                    '-W',
                    '-C'
                ]
                
                result_identity = subprocess.run(cmd_identity, capture_output=True, text=True, timeout=10)
                has_identity = result_identity.stdout.strip() == '1'
                
                if has_identity:
                    f.write(f"SET IDENTITY_INSERT [{schema}].[{table_name}] ON;\nGO\n")
                
                # Generar INSERTs
                try:
                    with open(temp_file, 'r', encoding='utf-8', errors='replace') as data_file:
                        lines = data_file.readlines()
                        batch_size = 100
                        
                        for batch_start in range(0, len(lines), batch_size):
                            batch = lines[batch_start:batch_start + batch_size]
                            
                            for line in batch:
                                if not line.strip():
                                    continue
                                    
                                values = line.strip().split(',')
                                formatted_values = []
                                
                                for i, value in enumerate(values):
                                    if i >= len(columns):
                                        break
                                        
                                    col = columns[i]
                                    
                                    if value == 'NULL':
                                        formatted_values.append('NULL')
                                    elif col['type'] in ('varchar', 'char', 'nvarchar', 'nchar', 'text', 'ntext'):
                                        # Escapar comillas simples
                                        escaped_value = value.replace("'", "''")
                                        formatted_values.append(f"'{escaped_value}'")
                                    elif col['type'] in ('datetime', 'date', 'datetime2', 'smalldatetime'):
                                        formatted_values.append(f"'{value}'")
                                    elif col['type'] == 'bit':
                                        formatted_values.append('1' if value == 'True' or value == '1' else '0')
                                    else:
                                        formatted_values.append(value)
                                
                                # Construir INSERT
                                col_names = ', '.join([f"[{col['name']}]" for col in columns[:len(values)]])
                                val_str = ', '.join(formatted_values)
                                
                                f.write(f"INSERT INTO [{schema}].[{table_name}] ({col_names}) VALUES ({val_str});\n")
                            
                            f.write("GO\n")
                
                except Exception as e:
                    self.logger.warning(f"Error procesando datos de {schema}.{table_name}: {e}")
                
                if has_identity:
                    f.write(f"SET IDENTITY_INSERT [{schema}].[{table_name}] OFF;\nGO\n")
                
                f.write("\n")
            
            # Limpiar archivo temporal
            if temp_file.exists():
                temp_file.unlink()
            
            return True
                
        except Exception as e:
            self.logger.warning(f"Error exportando datos de {schema}.{table_name}: {e}")
            return True  # Continuar aunque falle
    
    def _generate_table_inserts_fallback(self, db_config: DatabaseConfig, database_name: str,
                                        schema: str, table_name: str, script_file: Path) -> bool:
        """Método alternativo para generar INSERTs cuando BCP falla"""
        
        try:
            # Query simplificada para evitar problemas de encoding
            insert_query = f"""
            SET NOCOUNT ON;
            
            DECLARE @SQL NVARCHAR(MAX) = '';
            SELECT @SQL = @SQL + 
                'INSERT INTO [{schema}].[{table_name}] VALUES ('' + ' +
                STUFF((
                    SELECT ' + '', '' + ' + 
                    CASE 
                        WHEN [{col}] IS NULL THEN ''NULL''
                        WHEN TYPE_NAME(system_type_id) IN (''varchar'', ''nvarchar'', ''char'', ''nchar'', ''datetime'', ''date'')
                        THEN ''''''''' + REPLACE(CONVERT(NVARCHAR(MAX), [{col}]), '''''''', '''''''''''') + '''''''''
                        ELSE 'CAST([' + name + '] AS NVARCHAR(MAX))'
                    END
                    FROM sys.columns 
                    WHERE object_id = OBJECT_ID('[{schema}].[{table_name}]')
                    ORDER BY column_id
                    FOR XML PATH(''), TYPE
                ).value('.', 'NVARCHAR(MAX)'), 1, 9, '') + ');'
            
            -- Ejecutar para máximo 1000 filas para evitar timeout
            DECLARE @RowCount INT;
            SELECT @RowCount = COUNT(*) FROM [{schema}].[{table_name}];
            
            IF @RowCount > 0
            BEGIN
                DECLARE @Counter INT = 1;
                DECLARE @BatchSize INT = 100;
                
                WHILE @Counter <= @RowCount AND @Counter <= 1000
                BEGIN
                    DECLARE @CurrentSQL NVARCHAR(MAX) = REPLACE(@SQL, 'INSERT', 'SELECT TOP 1 ''INSERT''')
                    EXEC sp_executesql @CurrentSQL;
                    SET @Counter = @Counter + 1;
                END
            END
            """
            
            cmd = [
                'sqlcmd',
                '-S', self._get_server_string(db_config),
                '-U', db_config.user,
                '-P', db_config.password,
                '-d', database_name,
                '-Q', insert_query,
                '-y', '0',
                '-w', '8000',
                '-C',
                '-f', '65001'
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300, encoding='utf-8')
            
            if result.returncode == 0 and result.stdout.strip():
                with open(script_file, 'a', encoding='utf-8-sig', errors='ignore') as f:
                    f.write(f"\n-- Datos de [{schema}].[{table_name}] (método alternativo)\n")
                    
                    # Verificar si tiene IDENTITY
                    identity_query = f"""
                    SELECT COUNT(*) 
                    FROM sys.columns 
                    WHERE object_id = OBJECT_ID('[{schema}].[{table_name}]') 
                    AND is_identity = 1;
                    """
                    
                    cmd_identity = [
                        'sqlcmd',
                        '-S', self._get_server_string(db_config),
                        '-U', db_config.user,
                        '-P', db_config.password,
                        '-d', database_name,
                        '-Q', identity_query,
                        '-h', '-1',
                        '-W',
                        '-C'
                    ]
                    
                    result_identity = subprocess.run(cmd_identity, capture_output=True, text=True, timeout=10)
                    has_identity = result_identity.stdout.strip() == '1'
                    
                    if has_identity:
                        f.write(f"SET IDENTITY_INSERT [{schema}].[{table_name}] ON;\nGO\n")
                    
                    f.write(result.stdout)
                    
                    if has_identity:
                        f.write(f"SET IDENTITY_INSERT [{schema}].[{table_name}] OFF;\nGO\n")
                    
                    f.write("\n")
                return True
            else:
                self.logger.warning(f"No se pudieron exportar datos de {schema}.{table_name}")
                return True
                
        except Exception as e:
            self.logger.warning(f"Error en método alternativo para {schema}.{table_name}: {e}")
            return True
    
    def _get_server_string(self, db_config):
        """Genera el string de conexión al servidor"""
        if db_config.port and db_config.port != 1433:
            return f"{db_config.host},{db_config.port}"
        return db_config.host