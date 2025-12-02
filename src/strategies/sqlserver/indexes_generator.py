from pathlib import Path

class IndexGenerator:
    def __init__(self, logger):
        self.logger = logger

    def generate(self, conn, script_file: Path):
        try:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT 
                    i.name,
                    s.name,
                    t.name,
                    STUFF((
                        SELECT ', ' + c.name
                        FROM sys.index_columns ic2
                        INNER JOIN sys.columns c
                            ON c.object_id = ic2.object_id 
                            AND c.column_id = ic2.column_id
                        WHERE ic2.object_id = i.object_id
                        AND ic2.index_id = i.index_id
                        ORDER BY ic2.key_ordinal
                        FOR XML PATH(''), TYPE
                    ).value('.', 'NVARCHAR(MAX)'), 1, 2, '') AS cols
                FROM sys.indexes i
                INNER JOIN sys.tables t ON t.object_id = i.object_id
                INNER JOIN sys.schemas s ON s.schema_id = t.schema_id
                WHERE i.is_primary_key = 0
                AND i.is_unique_constraint = 0
                AND i.index_id > 0
            """)

            rows = cursor.fetchall()

            with open(script_file, 'a', encoding='utf-8') as f:
                f.write("\n-- =============================================\n")
                f.write("-- INDEXES\n")
                f.write("-- =============================================\n\n")

                for idx_name, schema, table, cols in rows:
                    if cols:
                        f.write(
                            f"CREATE INDEX [{idx_name}] "
                            f"ON [{schema}].[{table}] ({cols});\nGO\n"
                        )

            return True

        except Exception as e:
            self.logger.error(f"[INDEXES] ERROR: {e}")
            return False