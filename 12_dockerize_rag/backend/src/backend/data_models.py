"""
What does our data look like?
It’s the shared “contract” 
ingestion.py writes Article rows in.
rag.py reads them back out api.py
the frontend pass Prompt and RagResponse back and forth. 
Changing a field here changes it everywhere.
"""


from pydantic import BaseModel, Field
from lancedb.embeddings import get_registry
from lancedb.pydantic import LanceModel, Vector
from dotenv import load_dotenv

"""
Importing this does something invisible but important: just by being
imported, it tells LanceDB "hey, here's a custom way to turn text into
numbers if you ever need it." We're not using any function from it directly
that's why there's a `# noqa` next to it (it tells code-checkers
"don't warn me that this import looks unused, I know what I'm doing").
"""
from backend.custom_embeddings import nvidia_nemotron  # noqa

# Loads secret values (like API keys) from a hidden .env file into the
# program, so the next line can actually authenticate with Cohere.
load_dotenv()

# Here we pick which "text-to-numbers" tool we want to use: Cohere's
# multilingual embedding model. Think of this as a translator that turns
# any sentence into a list of numbers that represents its meaning.
embedding_model = get_registry().get("cohere").create(name="embed-multilingual-v3.0")


class Article(LanceModel):
    """
    This describes one row in our vector database — basically, one
    document we've stored. Every document we save must have these fields.
    """

    doc_id: str          # a unique name/id for this document
    filepath: str         # where the original .txt file lives on disk
    filename: str = Field(description="the stem of the file i.e. without the suffix")
    # "stem" is just the filename without ".txt" at the end,
    # e.g. "Holland_Lop.txt" -> "Holland_Lop"

    # This marks "content" as the text that should be fed into the
    # embedding_model to create its number-list (its "vector").
    content: str = embedding_model.SourceField()

    # This is where that resulting number-list actually gets stored.
    # `# type: ignore` just tells code-checkers "trust me, this is fine" —
    # it's a quirk of how LanceDB builds this field dynamically.
    embedding: Vector(embedding_model.ndims()) = embedding_model.VectorField()  # type: ignore


class Prompt(BaseModel):
    """This is the shape of the question coming in from the user."""

    prompt: str = Field(
        description="prompt from user, if empty consider prompt as missing"
    )


class RagResponse(BaseModel):
    """
    This is the shape of the answer our AI must give back.
    By forcing the AI to always answer in this exact shape, our frontend
    always knows exactly where to find the answer, filename, and filepath —
    no guessing or text-parsing needed.
    """

    filename: str = Field(description="filename of the retrieved file without suffix")
    filepath: str = Field(description="absolute path to the retrieved file")
    answer: str = Field(description="answer based on the retrieved file")