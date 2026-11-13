"""
db_utils.py - one helper function for talking to DuckDB.

WHAT THIS FILE IS FOR:
    Instead of repeating "connect, run SQL, close" everywhere, we write it
    once here and reuse it.

USED BY:
    setup_db.py        -> calls query_duckdb() to CREATE the table.
    restaurant_api.py  -> calls query_duckdb() to SELECT and INSERT.
"""

from pathlib import Path
import duckdb

# Path(__file__).parent = this file's folder (app/). We keep the .duckdb
# file in a "data" subfolder next to the code, no matter where you run from.
DATA_PATH = Path(__file__).parent / "data"
DATA_PATH.mkdir(exist_ok = True)

def query_duckdb(sql_code: str, parameters = None):
    """Run one SQL statement against data/restaurants.duckdb.

    Args:
        sql_code: SQL to run. Use `?` placeholders for values, e.g.
            "INSERT INTO restaurants VALUES (?,?,?)".
        parameters: Values filling those `?` placeholders, in order.
            Passing values this way (not pasted into the SQL string)
            protects against SQL injection.

    Returns:
        A pandas DataFrame for read queries (SELECT/FROM/DESC/PRAGMA),
        or None for statements that change data (CREATE, INSERT, ...).
    """

    # `with` opens the connection and guarantees it closes, even on error
    with duckdb.connect(DATA_PATH / "restaurants.duckdb") as conn:
        cursor = conn.execute(sql_code, parameters)

        # Decide whether this statement returns rows by looking at how it starts
        lower = sql_code.strip().lower()
        if lower.startswith(("select", "from", "desc", "pragma")):
            return cursor.df()
        # Otherwise (CREATE/INSERT) there's nothing to return.