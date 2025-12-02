from pathlib import Path

class ForeignKeyGenerator:
    def __init__(self, logger):
        self.logger = logger

    def generate(self, conn, script_file: Path):
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
            fk_map = {}

            for fk_name, schema, table, col, ref_s, ref_t, ref_c in rows:
                key = (fk_name, schema, table, ref_s, ref_t)
                fk_map.setdefault(key, []).append((col, ref_c))

            with open(script_file, "a", encoding="utf-8") as f:
                f.write("\n-- =============================================\n")
                f.write("-- FOREIGN KEYS\n")
                f.write("-- =============================================\n\n")

                for (fk_name, schema, table, ref_s, ref_t), cols in fk_map.items():
                    parent_cols = ", ".join(f"[{c}]" for c, _ in cols)
                    ref_cols = ", ".join(f"[{c}]" for _, c in cols)

                    f.write(
                        f"ALTER TABLE [{schema}].[{table}] WITH CHECK "
                        f"ADD CONSTRAINT [{fk_name}] FOREIGN KEY ({parent_cols}) "
                        f"REFERENCES [{ref_s}].[{ref_t}] ({ref_cols});\nGO\n"
                    )

            return True

        except Exception as e:
            self.logger.error(f"[FK] ERROR: {e}")
            return False
