from pathlib import Path

class TriggerGenerator:
    def __init__(self, logger):
        self.logger = logger

    def generate(self, conn, script_file: Path):
        try:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT 
                    s.name,
                    t.name,
                    tr.name,
                    m.definition
                FROM sys.triggers tr
                INNER JOIN sys.tables t ON t.object_id = tr.parent_id
                INNER JOIN sys.schemas s ON s.schema_id = t.schema_id
                INNER JOIN sys.sql_modules m ON m.object_id = tr.object_id
                WHERE tr.is_ms_shipped = 0
                ORDER BY s.name, t.name, tr.name
            """)

            rows = cursor.fetchall()

            with open(script_file, 'a', encoding='utf-8') as f:
                f.write("\n-- =============================================\n")
                f.write("-- TRIGGERS\n")
                f.write("-- =============================================\n\n")

                for schema, table, trigger, definition in rows:
                    f.write(f"IF OBJECT_ID('[{schema}].[{trigger}]', 'TR') IS NOT NULL DROP TRIGGER [{schema}].[{trigger}];\nGO\n")
                    f.write(definition + "\nGO\n\n")

            return True

        except Exception as e:
            self.logger.error(f"[TRIGGERS] ERROR: {e}")
            return False