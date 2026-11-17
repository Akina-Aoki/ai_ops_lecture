"""
Load our text files created by pdfs_to_text.py
into the searchable database that the AI can later search through.
"""

from backend.constants import VECTOR_DATABASE_PATH, DATA_PATH
import lancedb
from backend.data_models import Article
import time
from pathlib import Path


def setup_vector_db(path):
    """
    Makes sure the vector database exists on disk, and that it has a table
    called "articles" shaped like our Article class from data_models.py.
    If it already exists, we just reuse it instead of erroring out.
    """
    Path(path).mkdir(exist_ok=True)   # create the folder if it doesn't exist yet
    vector_db = lancedb.connect(uri=path)

    # exist_ok=True means "don't crash if this table is already there."
    vector_db.create_table("articles", schema=Article, exist_ok=True)

    return vector_db


def ingest_docs_to_vector_db(table):
    """
    Goes through every .txt file in our data folder and adds it to the
    vector database, so it becomes searchable later.
    """
    for file in DATA_PATH.glob("*.txt"):
        with open(file, "r") as f:
            content = f.read()

        doc_id = file.stem   # e.g. "holland_lop" from "holland_lop.txt"

        # Before adding this document, delete any older version of it with
        # the same id. This stops us from getting duplicate copies if we
        # run this script more than once.
        table.delete(f"doc_id = '{doc_id}'")

        # Adding a row here automatically triggers LanceDB to turn
        # `content` into a vector (a list of numbers) using the
        # embedding_model we set up in data_models.py.
        table.add(
            [
                {
                    "doc_id": doc_id,
                    "filepath": str(file),
                    "filename": file.stem,
                    "content": content,
                }
            ]
        )

        # Just so we can watch progress in the terminal: show how many rows
        # are in the table now, and which filenames are in there.
        print(table.to_pandas().shape)
        print(table.to_pandas()["filename"])

        # Wait 10 seconds before the next document. This is likely here to
        # avoid hitting a rate limit (a "slow down, too many requests" rule)
        # from the embedding service we're using.
        time.sleep(10)


if __name__ == "__main__":
    vector_db = setup_vector_db(VECTOR_DATABASE_PATH)
    ingest_docs_to_vector_db(vector_db["articles"])