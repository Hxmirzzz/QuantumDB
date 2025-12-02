from pathlib import Path

class DefaultConstraintGenerator:
    def __init__(self, logger):
        self.logger = logger

    def generate(self, conn, script_file: Path):
        try:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT 
                    dc.name,
                    s.name,
                    t.name,
                    c.name,
                    dc.definition
                FROM sys.default_constraints dc
                INNER JOIN sys.columns c ON c.default_object_id = dc.object_id
                INNER JOIN sys.tables t ON t.object_id = c.object_id
                INNER JOIN sys.schemas s ON s.schema_id = t.schema_id
            """)

            rows = cursor.fetchall()

            with open(script_file, 'a', encoding='utf-8') as f:
                f.write("\n-- =============================================\n")
                f.write("-- DEFAULT CONSTRAINTS\n")
                f.write("-- =============================================\n\n")

                for def_name, schema, table, col, definition in rows:
                    f.write(
                        f"ALTER TABLE [{schema}].[{table}] "
                        f"ADD CONSTRAINT [{def_name}] DEFAULT {definition} FOR [{col}];\nGO\n"
                    )

            return True

        except Exception as e:
            self.logger.error(f"[DEFAULTS] ERROR: {e}")
            return False