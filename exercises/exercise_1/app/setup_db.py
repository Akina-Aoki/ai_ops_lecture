"""
setup_db.py - one-time script that creates the `restaurants` table.

WHAT THIS FILE IS FOR:
    Must run once before the API starts, otherwise there's no table to
    read from or insert into.

    Run from this folder:
        python setup_db.py

USED BY / DEPENDS ON:
    Uses query_duckdb() from db_utils.py.
    Column order here must match Restaurant's field order in
    data_models.py, because restaurant_api.py inserts rows positionally.
"""

from db_utils import query_duckdb

# "IF NOT EXISTS" makes this safe to re-run: if the table already exists,
# nothing happens and no data is lost.

query_duckdb("""
    CREATE TABLE IF NOT EXISTS restaurants (
    name TEXT,
    cuisine TEXT,
    price_level TEXT,
    rating DOUBLE,
    description TEXT,
    opening_hours TEXT,
    location TEXT
    );
""")