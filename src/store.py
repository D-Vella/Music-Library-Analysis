"""DuckDB read/write helpers for data/library.duckdb.

Phase 2.
"""


def init_duckdb_connection(db_path):
    """
    Initialize a DuckDB connection.

    Args:
        db_path (str): The path to the DuckDB database file.

    Returns:
        duckdb.DuckDBPyConnection: A DuckDB connection object.
    """
    import duckdb
    return duckdb.connect(database=db_path)

def create_library_table(conn):
    """
    Create the library table in the DuckDB database.

    Args:
        conn (duckdb.DuckDBPyConnection): A DuckDB connection object.
    """
    conn.execute("""
        CREATE TABLE IF NOT EXISTS library (
            relative_path TEXT PRIMARY KEY,
            name TEXT,
            type TEXT,
            size BIGINT,
            modified_time DOUBLE
        )
    """)

def insert_file_records(conn, file_data):
    """
    Insert file records into the library table.

    Args:
        conn (duckdb.DuckDBPyConnection): A DuckDB connection object.
        file_data (dict): A dictionary containing file data to insert.
    """
    for relative_path, data in file_data.items():
        conn.execute("""
            INSERT INTO library (relative_path, name, type, size, modified_time)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(relative_path) DO UPDATE SET
                name=excluded.name,
                type=excluded.type,
                size=excluded.size,
                modified_time=excluded.modified_time
        """, (relative_path, data['name'], data['type'], data['size'], data['modified_time']))