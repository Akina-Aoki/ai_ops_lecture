"""
data_models.py - the "shape" of our data.

WHAT IS THIS FILE FOR?
    It defines Pydantic models: Python classes that describe what a piece of
    data must look like (which fields, which types, which allowed values).
    Pydantic checks the data for us and raises an error if it doesn't fit.

HOW IT CONNECTS TO THE OTHER FILES:
    - movies_api.py imports `Prompt` to validate what the user sends to the API,
      and imports `Movie` to force the AI model to answer in a strict structure.
    - The fields in `Movie` mirror the columns of the `movies` table that
      setup_db.py creates (title, year, genre, rating).

BIG PICTURE (the whole project):
    setup_db.py  -> creates the empty `movies` table in DuckDB
    utils.py     -> helper that runs SQL against that DuckDB file
    data_models.py (this file) -> defines Movie / Prompt data shapes
    movies_api.py -> the FastAPI web app that ties everything together
"""

from pydantic import BaseModel, Field


class Movie(BaseModel):
    """One movie record.

    Used in two places:
      1. As the `output_type` for the AI agent, so the LLM must reply with
         exactly these fields (this is called "structured output").
      2. As the response returned by the POST /movie endpoint.

    Example of valid data:
        Movie(title="Inception", year=2010, genre="Sci-Fi", rating=5)
    """

    title: str
    year: int
    genre: str
    # Field(gt=0, lt=6) = "greater than 0" and "less than 6",
    # so the only valid ratings are 1, 2, 3, 4 or 5.
    # Anything else (0, 6, -1, ...) makes Pydantic raise a ValidationError.
    rating: int = Field(gt=0, lt=6)


class Prompt(BaseModel):
    """The request body a user sends to POST /movie.

    Example JSON body:
        {"prompt": "Tell me about a classic 90s sci-fi movie"}
    """

    prompt: str
