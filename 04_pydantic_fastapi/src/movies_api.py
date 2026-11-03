"""
movies_api.py - the web API (the "main" file of this project).

WHAT IS THIS FILE FOR?
    It starts a FastAPI web server with two endpoints:

      GET  /movies  -> returns every movie stored in the database.
      POST /movie   -> you send a text prompt (e.g. "a famous 80s horror movie"),
                       an AI model turns it into a structured Movie
                       (title, year, genre, rating), and we save it in the database.

HOW ALL THE FILES CONNECT (data flow of POST /movie):

    user --{"prompt": "..."}--> movies_api.py
                                   |  1. validate request with `Prompt`      (data_models.py)
                                   |  2. ask the LLM, forcing a `Movie` reply (data_models.py + pydantic_ai)
                                   |  3. save the movie with query_duckdb()   (utils.py)
                                   v
                              data/movies.duckdb  <-- table created once by setup_db.py

    Order to get started:
      1. python setup_db.py                    # create the table (once)
      2. put your API key in a .env file       # e.g. Gemini_API_Key=...
      3. fastapi dev movies_api.py             # or: uvicorn movies_api:app --reload
      4. open http://127.0.0.1:8000/docs       # FastAPI's built-in page to try the endpoints
"""

from fastapi import FastAPI
# Note: ModelSettings is imported but not used below; it can be used to tune
# the model (e.g. temperature) if you ever need to.
from pydantic_ai import Agent, ModelSettings
from dotenv import load_dotenv
from utils import query_duckdb
from data_models import Movie, Prompt

# Reads the .env file and loads its values (like your Gemini_API_Key)
# into environment variables, so secrets stay out of the code.
load_dotenv()

# The web application object. The decorators below (@app.get / @app.post)
# register functions as URL endpoints on it.
app = FastAPI()

# An "Agent" from PydanticAI is our wrapper around an LLM.
# The model string is "<provider>:<model-name>". "google:" means: call this
# Gemini model through Google's API. (Older pydantic_ai versions used the
# prefix "google-gla:"; this version no longer recognises it.)
# The API key is read from the GOOGLE_API_KEY (or GEMINI_API_KEY) environment variable.
# Google retires models often (gemini-2.5-flash and gemini-3-pro-preview both return
# 404 now), so we use a "-latest" alias that always points to a current model.
# If you get a 404/429/503 error later, try another model name.
agent = Agent(model="google:gemini-flash-lite-latest", output_type=Movie)


@app.get("/movies")
# `async` lets the server handle other requests while this function waits.
# This function does not wait for anything yet, but it could if we add async work.
async def read_movies():
    """Return all movies in the database as a list of JSON objects."""
    # "FROM movies;" is DuckDB shorthand for "SELECT * FROM movies;".
    # query_duckdb returns a pandas DataFrame for read queries.
    movies = query_duckdb("FROM movies;")
    # orient="records" turns the DataFrame into a list of dicts, one per row:
    # [{"title": "...", "year": 1999, "genre": "...", "rating": 5}, ...]
    # FastAPI converts that into JSON automatically.
    return movies.to_dict(orient="records")


@app.post("/movie")
async def create_movie(query: Prompt):
    """Turn a free-text prompt into a Movie using AI, save it, and return it.

    `query: Prompt` tells FastAPI to expect a JSON body like {"prompt": "..."}
    and to validate it with the Prompt model. A bad body gets an automatic
    422 error before this function even runs.
    """
    # Ask the LLM. `output_type=Movie` makes PydanticAI force the answer into
    # the Movie structure and validate it (e.g. rating must be 1-5).
    # `await` is used because calling the LLM is slow; while we wait,
    # the server can handle other requests.
    result = await agent.run(query.prompt, output_type=Movie)
    # `result.output` is now a real Movie object, not loose text.
    movie = result.output

    # Save to the database. We pass the values separately as `parameters`
    # and use `?` placeholders in the SQL instead of building the string by hand.
    # This protects against SQL injection (e.g. a title like "'); DROP TABLE movies;--"
    # is stored as plain text, never run as SQL).
    # The value order must match the column order created in setup_db.py.
    query_duckdb(
        "INSERT INTO movies VALUES (?,?,?,?)",
        parameters=[movie.title, movie.year, movie.genre, movie.rating],
    )

    # Return the saved movie; FastAPI turns it into JSON for the caller.
    return movie
