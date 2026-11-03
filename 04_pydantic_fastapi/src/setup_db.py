"""
setup_db.py - one-time script that prepares the database.

WHAT IS THIS FILE FOR?
    It creates the `movies` table inside data/movies.duckdb. Run it ONCE
    before starting the API, otherwise the API would have no table to
    read from or insert into.

    Run it from this folder with:
        python setup_db.py        (or: uv run setup_db.py)

HOW IT CONNECTS TO THE OTHER FILES:
    - It uses `query_duckdb` from utils.py to talk to the database.
    - The columns below match the fields of the `Movie` model in
      data_models.py, in the SAME ORDER. That order matters because
      movies_api.py inserts rows positionally:
          INSERT INTO movies VALUES (title, year, genre, rating)
    - Afterwards, movies_api.py reads/writes this table.
"""

from utils import query_duckdb

# "IF NOT EXISTS" makes the script safe to run many times:
# if the table is already there, nothing happens and no data is lost.
query_duckdb("""
    CREATE TABLE IF NOT EXISTS movies (
        title TEXT,        -- movie name, e.g. "Inception"
        year INTEGER,      -- release year, e.g. 2010
        genre TEXT,        -- e.g. "Sci-Fi"
        rating TINYINT     -- small whole number; the API only allows 1-5
    );
    """)
