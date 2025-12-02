from pathlib import Path

class DataGenerator:
    def __init__(self, logger):
        self.logger = logger

    def generate(self, conn, script_file: Path):
        try:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT s.name, t.name
                FROM sys.tables t
                INNER JOIN sys.schemas s ON t.schema_id = s.schema_id
                WHERE t.is_ms_shipped = 0
                ORDER BY s.name, t.name
            """)

            tables = cursor.fetchall()
            total_tables = len(tables)

            with open(script_file, 'a', encoding='utf-8') as f:
                f.write("\n-- =============================================\n")
                f.write("-- DATA INSERTS\n")
                f.write("-- =============================================\n\n")

            for i, (schema, table) in enumerate(tables, 1):
                full = f"{schema}.{table}"
                self.logger.info(f"[DATA] ({i}/{total_tables}) {full}")

                cursor.execute(f"SELECT COUNT(*) FROM [{full}]")
                total_rows = cursor.fetchone()[0]

                if total_rows == 0:
                    self.logger.info(f"[DATA]   -> Empty table, skipping")
                    continue

                cursor.execute(f"""
                    SELECT c.name
                    FROM sys.columns c
                    WHERE c.object_id = OBJECT_ID('[{full}]')
                    ORDER BY c.column_id
                """)
                col_names = [c[0] for c in cursor.fetchall()]

                cursor.execute(f"""
                    SELECT COUNT(*) 
                    FROM sys.columns 
                    WHERE object_id = OBJECT_ID('[{full}]')
                    AND is_identity = 1
                """)
                has_identity = cursor.fetchone()[0] > 0

                cursor.execute(f"SELECT * FROM [{full}]")
                rows = cursor.fetchall()

                with open(script_file, 'a', encoding='utf-8') as f:
                    f.write(f"-- DATA: {full} ({total_rows} rows)\n")
                    if has_identity:
                        f.write(f"SET IDENTITY_INSERT [{full}] ON;\n")

                    columns_str = ", ".join(f"[{c}]" for c in col_names)
                    batch_size = 300

                    for start in range(0, len(rows), batch_size):
                        batch = rows[start:start + batch_size]

                        for row in batch:
                            values = []
                            for v in row:
                                if v is None:
                                    values.append("NULL")
                                elif isinstance(v, str):
                                    values.append("'" + v.replace("'", "''") + "'")
                                elif hasattr(v, "isoformat"):
                                    values.append(f"'{v}'")
                                elif isinstance(v, (bytes, bytearray)):
                                    values.append("0x" + v.hex() if v else "NULL")
                                elif isinstance(v, bool):
                                    values.append("1" if v else "0")
                                else:
                                    values.append(str(v))

                            values_str = ", ".join(values)
                            f.write(f"INSERT INTO [{full}] ({columns_str}) VALUES ({values_str});\n")

                        f.write("GO\n")

                    if has_identity:
                        f.write(f"SET IDENTITY_INSERT [{full}] OFF;\n")

            return True

        except Exception as e:
            self.logger.error(f"[DATA] ERROR: {e}")
            return False