"""
utils.py - a small helper for talking to our DuckDB database.

WHAT IS THIS FILE FOR?
    Instead of repeating "connect to the database, run SQL, close the
    connection" everywhere, we write it once in `query_duckdb` and reuse it.

WHAT IS DUCKDB?
    DuckDB is a lightweight analytical database that lives in a single file
    (here: data/movies.duckdb). There is no server to install or start -
    Python just opens the file.

HOW IT CONNECTS TO THE OTHER FILES:
    - setup_db.py calls query_duckdb(...) to CREATE the `movies` table.
    - movies_api.py calls query_duckdb(...) to read movies (GET /movies)
      and to insert new ones (POST /movie).
"""

from pathlib import Path
import duckdb

# Path(__file__) is this file's location, .parent is its folder (src/),
# and .parent.parent is the folder above it (04_pydantic_fastapi/).
# So DATA_PATH = "04_pydantic_fastapi/data". Building the path from __file__
# means it works no matter which directory you launch the script from.
DATA_PATH = Path(__file__).parent.parent / "data"


def query_duckdb(sql_code: str, parameters=None):
    """Run one SQL statement against data/movies.duckdb.

    Args:
        sql_code: The SQL to run. Use `?` as placeholders for values, e.g.
            "INSERT INTO movies VALUES (?,?,?,?)".
        parameters: A list of values that fill the `?` placeholders in order.
            Passing values this way (instead of pasting them into the SQL
            string yourself) protects against SQL injection.

    Returns:
        - A pandas DataFrame if the statement reads data
          (SELECT / FROM / DESCRIBE / PRAGMA).
        - None for statements that change data (CREATE, INSERT, ...).
    """
    # `with` opens the connection and guarantees it is closed afterwards,
    # even if an error happens. If the .duckdb file doesn't exist yet,
    # DuckDB creates it (the `data/` folder itself must already exist).
    with duckdb.connect(DATA_PATH / "movies.duckdb") as conn:
        # Run the SQL, filling in the `?` placeholders with `parameters`.
        # (parameters=None simply means "no placeholders".)
        cursor = conn.execute(sql_code, parameters)

        # Decide whether the statement returns rows by looking at how it starts.
        # DuckDB also allows the shorthand "FROM movies;" instead of
        # "SELECT * FROM movies;", which is why "from" is in the list.
        lower = sql_code.strip().lower()
        if lower.startswith(("select", "from", "desc", "pragma")):
            # Convert the result rows into a pandas DataFrame.
            return cursor.df()
        # Otherwise (CREATE / INSERT / ...) there is nothing to return.
