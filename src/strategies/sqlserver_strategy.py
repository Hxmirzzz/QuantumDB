"""
Estrategia de backup para SQL Server usando pyodbc
Genera script SQL completo con estructura y datos
"""
import pyodbc
from pathlib import Path
from datetime import datetime
from .base_strategy import BackupStrategy
from ..models import DatabaseConfig, BackupResult


class SQLServerBackupStrategy(BackupStrategy):
    """Estrategia de backup para SQL Server usando pyodbc"""
    
    def backup(self, db_config: DatabaseConfig, output_file: Path) -> BackupResult:
        """
        Ejecuta backup de SQL Server generando script SQL completo
        """
        try:
            database_name = db_config.database or db_config.name
            script_file = output_file.with_suffix('.sql')
            
            self.logger.info(f"Generando backup SQL completo de: {database_name}")
            self.logger.info(f"Archivo destino: {script_file}")

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
                    error="Variables de entorno no resueltas"
                )

            # Crear directorio
            script_file.parent.mkdir(parents=True, exist_ok=True)

            # Conectar
            conn = self._connect(db_config, database_name)
            if not conn:
                return BackupResult(
                    database_name=db_config.name,
                    success=False,
                    error="No se pudo conectar a SQL Server"
                )

            try:
                # Encabezado general
                with open(script_file, 'w', encoding='utf-8') as f:
                    f.write("-- =============================================\n")
                    f.write(f"-- BACKUP DE BASE DE DATOS: {database_name}\n")
                    f.write(f"-- Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write(f"-- Servidor: {db_config.host}\n")
                    f.write("-- =============================================\n\n")
                    f.write("USE [{}];\nGO\n\n".format(database_name))

                    f.write("-- >>>>>> SECTION: SCHEMA\n\n")

                # 1. Estructura
                self.logger.info("Paso 1/2: Generando estructura...")
                if not self._generate_schema(conn, database_name, script_file):
                    return BackupResult(database_name=db_config.name, success=False,
                                       error="Error generando estructura")

                # 2. Datos
                self.logger.info("Paso 2/2: Generando datos...")
                if not self._generate_data(conn, database_name, script_file):
                    return BackupResult(database_name=db_config.name, success=False,
                                       error="Error generando datos")

                # DEFAULTS
                self.logger.info("Generando defaults…")
                self._generate_defaults(conn, script_file)

                # ÍNDICES
                self.logger.info("Generando índices…")
                self._generate_indexes(conn, script_file)

                # Stored Procedures
                self.logger.info("Generando procedimientos almacenados…")
                self._generate_stored_procedures(conn, script_file)

                # FKs (último siempre)
                self.logger.info("Generando Foreign Keys…")
                self._generate_foreign_keys(conn, script_file)

                # TRIGGERS
                self.logger.info("Generando triggers…")
                self._generate_triggers(conn, script_file)

                # USERS
                self.logger.info("Generando usuarios…")
                self._generate_users(conn, script_file)

                # ROLES Y PERMISOS
                self.logger.info("Generando roles y permisos…")
                self._generate_roles_and_permissions(conn, script_file)

                # COMPUTED COLUMNS
                self.logger.info("Generando columnas calculadas…")
                self._generate_computed_columns(conn, script_file)
                
                file_size = script_file.stat().st_size / (1024 * 1024)
                self.logger.info(f"✓ Backup completado: {script_file.name} ({file_size:.2f} MB)")
                
                return BackupResult(database_name=db_config.name, success=True,
                                    output_file=str(script_file))

            finally:
                conn.close()

        except Exception as e:
            self.logger.error(f"Error: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            return BackupResult(database_name=db_config.name, success=False, error=str(e))


    def _connect(self, db_config: DatabaseConfig, database_name: str):
        """Conecta a SQL Server"""
        try:
            conn_str = (
                f"DRIVER={{ODBC Driver 17 for SQL Server}};"
                f"SERVER={db_config.host};"
                f"DATABASE={database_name};"
                f"UID={db_config.user};"
                f"PWD={db_config.password};"
                f"TrustServerCertificate=yes;"
            )
            
            self.logger.info(f"Conectando a: {db_config.host}")
            conn = pyodbc.connect(conn_str, timeout=30)
            self.logger.info("✓ Conexión establecida")
            return conn
            
        except pyodbc.Error as e:
            self.logger.error(f"Error de conexión: {e}")
            return None


    # -------------------------------------------------------------------------
    # GENERAR ESTRUCTURA
    # -------------------------------------------------------------------------

    def _generate_schema(self, conn, database_name: str, script_file: Path) -> bool:
        """Genera estructura de la BD"""
        try:
            cursor = conn.cursor()

            with open(script_file, 'a', encoding='utf-8') as f:
                f.write("-- >>>>>> SECTION: SCHEMA (CREATE TABLES)\n\n")

            cursor.execute("""
                SELECT s.name, t.name
                FROM sys.tables t
                INNER JOIN sys.schemas s ON t.schema_id = s.schema_id
                WHERE t.is_ms_shipped = 0
                ORDER BY s.name, t.name
            """)
            
            tables = cursor.fetchall()
            if not tables:
                return True

            self.logger.info(f"  Exportando estructura de {len(tables)} tablas...")

            for i, (schema, table) in enumerate(tables, 1):
                self.logger.info(f"    [{i}/{len(tables)}] {schema}.{table}")

                with open(script_file, 'a', encoding='utf-8') as f:
                    f.write(f"\n-- Tabla: [{schema}].[{table}]\n")
                    f.write(f"IF OBJECT_ID('[{schema}].[{table}]', 'U') IS NOT NULL\n")
                    f.write(f"    DROP TABLE [{schema}].[{table}];\nGO\n\n")

                    cursor.execute(f"""
                        SELECT 
                            c.name,
                            TYPE_NAME(c.user_type_id),
                            c.max_length,
                            c.precision,
                            c.scale,
                            c.is_nullable,
                            c.is_identity
                        FROM sys.columns c
                        WHERE c.object_id = OBJECT_ID('[{schema}].[{table}]')
                        ORDER BY c.column_id
                    """)

                    columns = cursor.fetchall()

                    f.write(f"CREATE TABLE [{schema}].[{table}] (\n")

                    for j, col in enumerate(columns):
                        col_name, type_name, max_len, precision, scale, nullable, is_identity = col

                        if type_name in ('varchar', 'char', 'varbinary', 'binary'):
                            type_str = f"{type_name}({max_len if max_len != -1 else 'MAX'})"
                        elif type_name in ('nvarchar', 'nchar'):
                            type_str = f"{type_name}({max_len//2 if max_len != -1 else 'MAX'})"
                        elif type_name in ('decimal', 'numeric'):
                            type_str = f"{type_name}({precision},{scale})"
                        else:
                            type_str = type_name
                        
                        identity_str = " IDENTITY(1,1)" if is_identity else ""
                        null_str = " NULL" if nullable else " NOT NULL"
                        comma = "," if j < len(columns) - 1 else ""

                        f.write(f"    [{col_name}] {type_str}{identity_str}{null_str}{comma}\n")

                    f.write(");\nGO\n\n")

                    cursor.execute(f"""
                        SELECT 
                            i.name,
                            STRING_AGG(c.name, ', ') 
                                WITHIN GROUP (ORDER BY ic.key_ordinal)
                        FROM sys.indexes i
                        INNER JOIN sys.index_columns ic 
                            ON i.object_id = ic.object_id 
                            AND i.index_id = ic.index_id
                        INNER JOIN sys.columns c 
                            ON ic.object_id = c.object_id 
                            AND ic.column_id = c.column_id
                        WHERE i.object_id = OBJECT_ID('[{schema}].[{table}]')
                        AND i.is_primary_key = 1
                        GROUP BY i.name
                    """)

                    pk = cursor.fetchone()
                    if pk:
                        pk_name, cols = pk
                        f.write(
                            f"ALTER TABLE [{schema}].[{table}]\n"
                            f"    ADD CONSTRAINT [{pk_name}] PRIMARY KEY CLUSTERED ({cols});\nGO\n\n"
                        )

            return True
        
        except Exception as e:
            self.logger.error(f"Error en _generate_schema: {e}")
            return False


    # -------------------------------------------------------------------------
    # GENERAR DATOS
    # -------------------------------------------------------------------------

    def _generate_data(self, conn, database_name: str, script_file: Path) -> bool:
        """Genera datos detallados + logs."""
        try:
            cursor = conn.cursor()

            with open(script_file, 'a', encoding='utf-8') as f:
                f.write("\n-- >>>>>> SECTION: DATA\n\n")

            cursor.execute("""
                SELECT s.name, t.name
                FROM sys.tables t
                INNER JOIN sys.schemas s ON t.schema_id = s.schema_id
                WHERE t.is_ms_shipped = 0
                ORDER BY s.name, t.name
            """)

            tables = cursor.fetchall()
            if not tables:
                return True

            for i, (schema, table) in enumerate(tables, 1):
                full = f"{schema}.{table}"
                self.logger.info(f"[{i}/{len(tables)}] Exportando datos de {full}")

                cursor.execute(f"SELECT COUNT(*) FROM [{schema}].[{table}]")
                total = cursor.fetchone()[0]

                if total == 0:
                    continue

                cursor.execute(f"""
                    SELECT c.name 
                    FROM sys.columns c
                    WHERE c.object_id = OBJECT_ID('[{schema}].[{table}]')
                    ORDER BY c.column_id
                """)
                col_names = [c[0] for c in cursor.fetchall()]

                cursor.execute(f"""
                    SELECT COUNT(*) 
                    FROM sys.columns 
                    WHERE object_id = OBJECT_ID('[{schema}].[{table}]')
                    AND is_identity = 1
                """)
                has_identity = cursor.fetchone()[0] > 0

                cursor.execute(f"SELECT * FROM [{schema}].[{table}]")
                rows = cursor.fetchall()

                successes = 0
                fails = 0

                with open(script_file, 'a', encoding='utf-8') as f:
                    f.write(
                        f"\n-- Datos de {full} ({total} registros)\n"
                    )

                    if has_identity:
                        f.write(f"SET IDENTITY_INSERT [{schema}].[{table}] ON;\n")

                    batch_size = 400

                    for batch_start in range(0, len(rows), batch_size):
                        batch = rows[batch_start:batch_start + batch_size]

                        for row_idx, row in enumerate(batch, start=batch_start + 1):
                            try:
                                values = []

                                for v in row:
                                    if v is None:
                                        values.append("NULL")
                                    elif isinstance(v, str):
                                        values.append("'" + v.replace("'", "''") + "'")
                                    elif hasattr(v, "isoformat"):
                                        values.append(f"'{v}'")
                                    elif isinstance(v, (bytes, bytearray)):
                                        values.append("0x" + v.hex())
                                    elif isinstance(v, bool):
                                        values.append("1" if v else "0")
                                    else:
                                        values.append(str(v))

                                cols = ", ".join(f"[{c}]" for c in col_names)
                                vals = ", ".join(values)

                                f.write(
                                    f"INSERT INTO [{schema}].[{table}] ({cols}) "
                                    f"VALUES ({vals});\n"
                                )

                                successes += 1

                            except Exception as e:
                                fails += 1
                                self.logger.warning(
                                    f"Error en fila {row_idx} de {full}: {repr(e)}"
                                )
                                continue

                        f.write("GO\n")

                    if has_identity:
                        f.write(f"SET IDENTITY_INSERT [{schema}].[{table}] OFF;\n")

                self.logger.info(
                    f"✔ {full}: {successes}/{total} insertados. Fallidos: {fails}"
                )

            return True

        except Exception as e:
            self.logger.error(f"Error en _generate_data: {e}")
            return False


    # -------------------------------------------------------------------------
    # DEFAULTS
    # -------------------------------------------------------------------------

    def _generate_defaults(self, conn, script_file: Path):
        try:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT 
                    dc.name AS def_name,
                    s.name AS schema_name,
                    t.name AS table_name,
                    c.name AS column_name,
                    dc.definition
                FROM sys.default_constraints dc
                INNER JOIN sys.columns c ON c.default_object_id = dc.object_id
                INNER JOIN sys.tables t ON t.object_id = c.object_id
                INNER JOIN sys.schemas s ON s.schema_id = t.schema_id
            """)

            rows = cursor.fetchall()
            if not rows:
                return True

            with open(script_file, 'a', encoding='utf-8') as f:
                f.write("\n-- >>>>>> SECTION: DEFAULTS\n\n")

                for def_name, schema, table, col, definition in rows:
                    f.write(
                        f"ALTER TABLE [{schema}].[{table}] "
                        f"ADD CONSTRAINT [{def_name}] DEFAULT {definition} FOR [{col}];\nGO\n"
                    )

            return True
        except Exception as e:
            self.logger.error("Error generando DEFAULTs: " + str(e))
            return False


    # -------------------------------------------------------------------------
    # ÍNDICES
    # -------------------------------------------------------------------------

    def _generate_indexes(self, conn, script_file: Path):
        try:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT 
                    i.name,
                    s.name,
                    t.name,
                    STRING_AGG(c.name, ', ') 
                        WITHIN GROUP (ORDER BY ic.key_ordinal)
                FROM sys.indexes i
                INNER JOIN sys.index_columns ic ON i.object_id = ic.object_id 
                                               AND i.index_id = ic.index_id
                INNER JOIN sys.columns c ON c.object_id = ic.object_id 
                                         AND c.column_id = ic.column_id
                INNER JOIN sys.tables t ON t.object_id = i.object_id
                INNER JOIN sys.schemas s ON s.schema_id = t.schema_id
                WHERE i.is_primary_key = 0
                AND i.is_unique_constraint = 0
                AND i.index_id > 0
                GROUP BY i.name, s.name, t.name
            """)

            rows = cursor.fetchall()
            if not rows:
                return True

            with open(script_file, 'a', encoding='utf-8') as f:
                f.write("\n-- >>>>>> SECTION: INDEXES\n\n")

                for idx_name, schema, table, cols in rows:
                    f.write(
                        f"CREATE INDEX [{idx_name}] ON "
                        f"[{schema}].[{table}] ({cols});\nGO\n"
                    )

            return True

        except Exception as e:
            self.logger.error("Error generando índices: " + str(e))
            return False


    # -------------------------------------------------------------------------
    # STORED PROCEDURES
    # -------------------------------------------------------------------------

    def _generate_stored_procedures(self, conn, script_file: Path):
        try:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT 
                    s.name,
                    p.name,
                    m.definition
                FROM sys.procedures p
                INNER JOIN sys.schemas s ON s.schema_id = p.schema_id
                INNER JOIN sys.sql_modules m ON m.object_id = p.object_id
                ORDER BY s.name, p.name
            """)

            rows = cursor.fetchall()
            if not rows:
                return True

            with open(script_file, 'a', encoding='utf-8') as f:
                f.write("\n-- >>>>>> SECTION: PROCEDURES\n\n")

                for schema, name, definition in rows:
                    f.write(f"DROP PROCEDURE IF EXISTS [{schema}].[{name}];\nGO\n")
                    f.write(definition + "\nGO\n\n")

            return True
        except Exception as e:
            self.logger.error("Error generando procedimientos: " + str(e))
            return False


    # -------------------------------------------------------------------------
    # FOREIGN KEYS
    # -------------------------------------------------------------------------

    def _generate_foreign_keys(self, conn, script_file: Path):
        try:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT 
                    fk.name,
                    s1.name,
                    t1.name,
                    c1.name,
                    s2.name,
                    t2.name,
                    c2.name
                FROM sys.foreign_keys fk
                INNER JOIN sys.foreign_key_columns fkc
                    ON fkc.constraint_object_id = fk.object_id
                INNER JOIN sys.tables t1 
                    ON t1.object_id = fkc.parent_object_id
                INNER JOIN sys.schemas s1 
                    ON s1.schema_id = t1.schema_id
                INNER JOIN sys.columns c1 
                    ON c1.column_id = fkc.parent_column_id
                    AND c1.object_id = t1.object_id
                INNER JOIN sys.tables t2 
                    ON t2.object_id = fkc.referenced_object_id
                INNER JOIN sys.schemas s2 
                    ON s2.schema_id = t2.schema_id
                INNER JOIN sys.columns c2 
                    ON c2.column_id = fkc.referenced_column_id
                    AND c2.object_id = t2.object_id
                ORDER BY fk.name, fkc.constraint_column_id
            """)

            rows = cursor.fetchall()
            if not rows:
                return True

            # Reagrupar por constraint
            fk_map = {}
            for fk_name, schema, table, col, ref_s, ref_t, ref_c in rows:
                key = (fk_name, schema, table, ref_s, ref_t)
                fk_map.setdefault(key, []).append((col, ref_c))

            with open(script_file, 'a', encoding='utf-8') as f:
                f.write("\n-- >>>>>> SECTION: FOREIGN_KEYS\n\n")

                for (fk_name, schema, table, ref_s, ref_t), cols in fk_map.items():
                    parent_cols = ", ".join(c for c, _ in cols)
                    ref_cols = ", ".join(c for _, c in cols)

                    f.write(
                        f"ALTER TABLE [{schema}].[{table}] WITH CHECK "
                        f"ADD CONSTRAINT [{fk_name}] FOREIGN KEY ({parent_cols}) "
                        f"REFERENCES [{ref_s}].[{ref_t}] ({ref_cols});\nGO\n"
                    )

            return True

        except Exception as e:
            self.logger.error("Error generando FKs: " + str(e))
            return False

    def _generate_triggers(self, conn, script_file: Path):
        """Exporta todos los triggers DML."""
        try:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT 
                    s.name AS schema_name,
                    t.name AS table_name,
                    tr.name AS trigger_name,
                    m.definition
                FROM sys.triggers tr
                INNER JOIN sys.tables t ON t.object_id = tr.parent_id
                INNER JOIN sys.schemas s ON s.schema_id = t.schema_id
                INNER JOIN sys.sql_modules m ON m.object_id = tr.object_id
                WHERE tr.is_ms_shipped = 0
                AND tr.parent_class = 1
                ORDER BY s.name, t.name, tr.name
            """)

            rows = cursor.fetchall()
            if not rows:
                return True

            with open(script_file, "a", encoding="utf-8") as f:
                f.write("\n-- >>>>>> SECTION: TRIGGERS\n\n")

                for schema, table, trigger, definition in rows:
                    f.write(f"DROP TRIGGER IF EXISTS [{schema}].[{trigger}];\nGO\n")
                    f.write(definition + "\nGO\n\n")

            return True

        except Exception as e:
            self.logger.error("Error generando TRIGGERS: " + str(e))
            return False

    def _generate_users(self, conn, script_file: Path):
        """Exporta usuarios locales de la base de datos."""
        try:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT 
                    name, type_desc
                FROM sys.database_principals
                WHERE type IN ('S','U') 
                AND sid IS NOT NULL
                AND name NOT IN ('dbo','guest','INFORMATION_SCHEMA','sys')
            """)

            rows = cursor.fetchall()
            if not rows:
                return True

            with open(script_file, "a", encoding="utf-8") as f:
                f.write("\n-- >>>>>> SECTION: USERS\n\n")

                for name, type_desc in rows:
                    f.write(
                        f"CREATE USER [{name}] FOR LOGIN [{name}] WITH DEFAULT_SCHEMA=[dbo];\nGO\n"
                    )

            return True

        except Exception as e:
            self.logger.error("Error generando USERS: " + str(e))
            return False

    def _generate_roles_and_permissions(self, conn, script_file: Path):
        """Exporta roles y permisos asignados."""
        try:
            cursor = conn.cursor()

            # Roles de base de datos
            cursor.execute("""
                SELECT name 
                FROM sys.database_principals
                WHERE type = 'R' 
                AND name NOT LIKE 'db_%'
            """)

            roles = cursor.fetchall()

            # Miembros de roles
            cursor.execute("""
                SELECT 
                    r.name AS role_name,
                    m.name AS member_name
                FROM sys.database_role_members rm
                INNER JOIN sys.database_principals r ON rm.role_principal_id = r.principal_id
                INNER JOIN sys.database_principals m ON rm.member_principal_id = m.principal_id
            """)

            memberships = cursor.fetchall()

            if not roles and not memberships:
                return True

            with open(script_file, "a", encoding="utf-8") as f:
                f.write("\n-- >>>>>> SECTION: ROLES_AND_PERMISSIONS\n\n")

                # Crear roles
                for (role,) in roles:
                    f.write(f"CREATE ROLE [{role}];\nGO\n")

                # Asignar miembros
                for role, member in memberships:
                    f.write(
                        f"EXEC sp_addrolemember N'{role}', N'{member}';\nGO\n"
                    )

            return True

        except Exception as e:
            self.logger.error("Error generando ROLES: " + str(e))
            return False

    def _generate_computed_columns(self, conn, script_file: Path):
        """Exporta columnas calculadas (computed columns)."""
        try:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT 
                    s.name AS schema_name,
                    t.name AS table_name,
                    c.name AS column_name,
                    cc.definition
                FROM sys.computed_columns cc
                INNER JOIN sys.columns c ON cc.object_id = c.object_id AND cc.column_id = c.column_id
                INNER JOIN sys.tables t ON t.object_id = cc.object_id
                INNER JOIN sys.schemas s ON s.schema_id = t.schema_id
            """)

            rows = cursor.fetchall()
            if not rows:
                return True

            with open(script_file, "a", encoding="utf-8") as f:
                f.write("\n-- >>>>>> SECTION: COMPUTED_COLUMNS\n\n")

                for schema, table, col, definition in rows:
                    f.write(
                        f"ALTER TABLE [{schema}].[{table}] "
                        f"ADD [{col}] AS {definition};\nGO\n"
                    )

            return True

        except Exception as e:
            self.logger.error("Error generando COMPUTED COLUMNS: " + str(e))
            return False
