"""
it’s the one-time (or re-run-when-docs-change) job that actually builds the database rag.py later searches.
"""

from backend.constants import VECTOR_DATABASE_PATH, DATA_PATH
import lancedb
from backend.data_models import Article
import time
from pathlib import Path


def setup_vector_db(path):
    """
    Prepares the database so we can start adding data to it.
    """
    Path(path).mkdir(exist_ok=True)              # create the folder if it doesn't exist yet; exist_ok=True means "don't error if it's already there"
    vector_db = lancedb.connect(uri=path)         # open (or create) the database at that folder
    vector_db.create_table("articles", schema=Article, exist_ok=True)   # create a table named "articles" shaped like our Article class, unless it already exists

    return vector_db


def ingest_docs_to_vector_db(table):
    """
    Loads every .txt file into the table, turning each one's text into
    an embedding along the way.
    """
    for file in DATA_PATH.glob("*.txt"):   # loop over every .txt file in the data folder
        with open(file, "r") as f:
            content = f.read()             # read the whole file's text into a string

        doc_id = file.stem                 # filename without the ".txt" ending, e.g. "holland_lop"

        # If we've already added this document before (e.g. we're re-running
        # the script), remove the old row first so we don't end up with
        # duplicates — this line means "delete any row where doc_id matches".
        table.delete(f"doc_id = '{doc_id}'")

        table.add(
            [
                {
                    "doc_id": doc_id,
                    "filepath": str(file),
                    "filename": file.stem,
                    "content": content,
                    # Notice: no "embedding" key here. LanceDB sees that
                    # Article's embedding field is a VectorField tied to
                    # `content`, so it automatically calls the embedding
                    # model and fills this in for us.
                }
            ]
        )

        print(table.to_pandas().shape)          # prints (number_of_rows, number_of_columns), just to watch progress
        print(table.to_pandas()["filename"])     # prints the filenames added so far
        time.sleep(30)   # pause 30 seconds — Google's embedding API only allows so many requests per minute, so this avoids hitting that limit


# This block only runs when you execute "python -m backend.ingestion" directly.
if __name__ == "__main__":
    vector_db = setup_vector_db(VECTOR_DATABASE_PATH)

    ingest_docs_to_vector_db(vector_db["articles"])