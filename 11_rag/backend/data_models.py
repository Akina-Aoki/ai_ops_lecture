"""
This is the shared vocabulary of the whole project. 
Article describes what gets stored; 
Prompt describes what comes in from the user; 
RagResponse describes what goes out as the answer.
"""

from pydantic import BaseModel, Field
from lancedb.embeddings import get_registry
from lancedb.pydantic import LanceModel, Vector
from dotenv import load_dotenv

# Loads variables from a .env file (e.g. the Gemini API key) into the environment
# so the embedding model below can authenticate.
load_dotenv()

# "get_registry()" is LanceDB's list of embedding models it knows how to use.
# .get("gemini-text") picks Google's Gemini embedding model, and .create(...)
# actually sets it up with the specific model name "gemini-embedding-001".
# An "embedding model" takes a piece of text and turns it into a list of
# numbers that represents what that text *means* (not just its words).
embedding_model = get_registry().get("gemini-text").create(name="gemini-embedding-001")

# This specific embedding model always outputs a list of exactly 3072 numbers
# for any piece of text, no matter how long or short the text is.
EMBEDDING_DIM = 3072


class Article(LanceModel):
    """
    This class defines the "shape" of one row in our database table —
    called a schema. Every document we store must have exactly these
    fields. LanceModel (from LanceDB) understands this shape and uses it
    to create a real database table matching it.
    """
    doc_id: str       # unique key (the file's stem); used to delete old rows before re-adding on re-ingestion
    file_path: str    # absolute path to the source .txt file
    filename: str = Field(description = "the stem of the file i.e without the suffix")  # "stem" = filename without ".txt" at the end

    # SourceField() marks this as the field whose TEXT gets fed into the embedding model. We write text here ourselves.
    content: str = embedding_model.SourceField()   

    # VectorField() marks this as where the embedding model's OUTPUT numbers
    # get stored. We never write this ourselves — LanceDB fills it in
    # automatically, by running `content` through embedding_model.
    embedding: Vector(EMBEDDING_DIM) = embedding_model.VectorField()  

class Prompt(BaseModel):
    """
    This is the shape of what a user sends in when they ask a question.
    FastAPI (in api.py) uses this to check that an incoming request
    actually contains a "prompt" field with text in it, and rejects
    anything that doesn't match.
    """
    prompt: str = Field(description = "prompt from user, if empty consider prompt as missing.")


class RagResponse(BaseModel):
    """
    This is the shape we FORCE the AI's answer into. Instead of letting
    the AI just reply with free-form text, we tell it: your answer must
    fill in exactly these three fields. That makes the response
    predictable and easy for app.py (the Streamlit page) to read.
    """
    filename: str = Field(description="filename of the retrieved file without suffix")
    filepath: str = Field(description="absolute path to the retrieved file")
    answer: str = Field(description="answer based on the retrieved file")