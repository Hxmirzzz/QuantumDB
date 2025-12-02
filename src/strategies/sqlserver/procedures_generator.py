from pathlib import Path

class StoredProcedureGenerator:
    def __init__(self, logger):
        self.logger = logger

    def generate(self, conn, script_file: Path):
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

            procs = cursor.fetchall()

            with open(script_file, 'a', encoding='utf-8') as f:
                f.write("\n-- =============================================\n")
                f.write("-- STORED PROCEDURES\n")
                f.write("-- =============================================\n\n")

                for schema, name, definition in procs:
                    f.write(f"IF OBJECT_ID('[{schema}].[{name}]', 'P') IS NOT NULL DROP PROCEDURE [{schema}].[{name}];\nGO\n")
                    f.write(definition + "\nGO\n\n")

            return True

        except Exception as e:
            self.logger.error(f"[PROCS] ERROR: {e}")
            return False