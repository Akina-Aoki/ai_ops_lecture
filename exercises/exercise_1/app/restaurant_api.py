"""
restaurant_api.py - the FastAPI app (the file you run with uvicorn).

WHAT THIS FILE IS FOR:
    GET  /restaurants  -> every restaurant stored in the database.
    POST /restaurant    -> you send a free-text prompt describing a
                            location (and optionally a food type); the
                            AI turns it into one structured Restaurant,
                            which gets saved and returned.

DATA FLOW of POST /restaurant:
    caller --{"prompt": "..."}--> restaurant_api.py
                                     | 1. validate body with Prompt      (data_models.py)
                                     | 2. ask the LLM for a Restaurant   (data_models.py + pydantic_ai)
                                     | 3. save it with query_duckdb()    (db_utils.py)
                                     v
                                data/restaurants.duckdb  <- table made once by setup_db.py

RUN ORDER:
    1. python setup_db.py                 (creates the table, once)
    2. NVIDIA_API=... in your .env        (same key as exercise_0)
    3. uvicorn restaurant_api:app --reload
    4. open http://127.0.0.1:8000/docs
"""

import os
from fastapi import FastAPI
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider
from dotenv import load_dotenv

from db_utils import query_duckdb
from data_models import Restaurant, Prompt

# Reads the .env file so the API key stays out of the code.
load_dotenv()

# The web app object; @app.get/@app.post below register functions as routes on it.
app = FastAPI()

model = OpenAIChatModel(
    "nvidia/nemotron-3.5-lightning-30b-a3b",
    provider=OpenAIProvider(
        base_url="https://integrate.api.nvidia.com/v1",
        api_key=os.environ["NVIDIA_API"],
    ),
)

# output_type=Restaurant forces the LLM's reply into that exact structure;
# an invalid reply (e.g. rating out of range) gets sent back for a retry.
restaurant_agent = Agent(
    model,
    output_type = Restaurant,
    instructions = (
                "You suggest one restaurant based on a free-text request describing "
        "a location and, optionally, a type of food the user wants. "
        "Fill in every field. It is fine to invent a plausible restaurant "
        "that may not actually exist."
    ),
)

@app.get("/restaurants")
async def read_restaurants():
    """Return all restaurants in the database as a list of JSON objects."""
    # "FROM restaurants;" is DuckDB shorthand for "SELECT * FROM restaurants;".
    restaurants = query_duckdb("FROM restaurants;")


@app.post("/restaurant")
async def create_restaurant(query:Prompt):
    """Turn a free-text prompt into a Restaurant using AI, save it, return it.

    `query: Prompt` makes FastAPI validate the body as {"prompt": "..."}
    before this function runs - a wrong shape gets an automatic 422.
    """
    # await: the LLM call is slow; while we wait, the server can handle other requests.

    result = await restaurant_agent.run(query.prompt, model_settings={"timeout": 120})
    # result.output is now a real Restaurant object, not loose text.
    restaurant = result.output


    # Values passed separately as `parameters`, with `?` placeholders in the
    # SQL - never build the SQL string by hand with f-strings (SQL injection).
    # Order here must match the column order from setup_db.py.

    query_duckdb(
        "INSERT INTO restaurants VALUES (?,?,?,?,?,?,?)",
        parameters = [
            restaurant.name,
            restaurant.cuisine,
            restaurant.price_level,
            restaurant.rating,
            restaurant.description,
            restaurant.opening_hours,
            restaurant.location,
        ],
    )

    # FastAPI turns this Restaurant into JSON for the caller.
    return restaurant