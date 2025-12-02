import pyodbc
from pathlib import Path

class SchemaGenerator:
    def __init__(self, logger):
        self.logger = logger

    def generate(self, conn, script_file: Path):
        try:
            cursor = conn.cursor()

            with open(script_file, 'a', encoding='utf-8') as f:
                f.write("\n-- =============================================\n")
                f.write("-- SCHEMA: TABLES + PRIMARY KEYS\n")
                f.write("-- =============================================\n\n")

            cursor.execute("""
                SELECT s.name, t.name
                FROM sys.tables t
                INNER JOIN sys.schemas s ON t.schema_id = s.schema_id
                WHERE t.is_ms_shipped = 0
                ORDER BY s.name, t.name
            """)

            tables = cursor.fetchall()
            total = len(tables)

            self.logger.info(f"[SCHEMA] Total tables: {total}")

            for i, (schema, table) in enumerate(tables, 1):
                full = f"{schema}.{table}"
                self.logger.info(f"[SCHEMA] ({i}/{total}) {full}")

                with open(script_file, 'a', encoding='utf-8') as f:
                    f.write(f"\n-- TABLE: {full}\n")
                    f.write(f"IF OBJECT_ID('[{full}]', 'U') IS NOT NULL DROP TABLE [{full}];\nGO\n\n")

                # Columnas
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
                    WHERE c.object_id = OBJECT_ID('[{full}]')
                    ORDER BY c.column_id
                """)

                columns = cursor.fetchall()

                with open(script_file, 'a', encoding='utf-8') as f:
                    f.write(f"CREATE TABLE [{full}] (\n")

                    for idx, col in enumerate(columns):
                        col_name, type_name, max_len, precision, scale, nullable, is_identity = col

                        # tipos
                        if type_name in ('varchar', 'char', 'varbinary', 'binary'):
                            type_str = f"{type_name}({max_len if max_len != -1 else 'MAX'})"
                        elif type_name in ('nvarchar', 'nchar'):
                            type_str = f"{type_name}({max_len//2 if max_len != -1 else 'MAX'})"
                        elif type_name in ('decimal', 'numeric'):
                            type_str = f"{type_name}({precision},{scale})"
                        else:
                            type_str = type_name

                        line = f"    [{col_name}] {type_str}"
                        if is_identity:
                            line += " IDENTITY(1,1)"
                        line += " NULL" if nullable else " NOT NULL"
                        if idx < len(columns) - 1:
                            line += ","
                        f.write(line + "\n")

                    f.write(");\nGO\n\n")

                # PK
                cursor.execute(f"""
                    SELECT 
                        i.name,
                        STUFF((
                            SELECT ', ' + c.name
                            FROM sys.index_columns ic2
                            INNER JOIN sys.columns c 
                                ON ic2.object_id = c.object_id 
                                AND ic2.column_id = c.column_id
                            WHERE ic2.object_id = i.object_id
                            AND ic2.index_id = i.index_id
                            ORDER BY ic2.key_ordinal
                            FOR XML PATH(''), TYPE
                        ).value('.', 'NVARCHAR(MAX)'), 1, 2, '') AS columns
                    FROM sys.indexes i
                    WHERE i.object_id = OBJECT_ID('[{full}]')
                    AND i.is_primary_key = 1
                """)

                pk = cursor.fetchone()
                if pk and pk[1]:
                    pk_name, cols = pk
                    with open(script_file, 'a', encoding='utf-8') as f:
                        f.write(f"ALTER TABLE [{full}] ADD CONSTRAINT [{pk_name}] PRIMARY KEY ({cols});\nGO\n\n")

            return True

        except Exception as e:
            self.logger.error(f"[SCHEMA] ERROR: {e}")
            return False