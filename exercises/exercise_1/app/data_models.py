"""
data_models.py - the "shape" of our data (Pydantic models).

WHAT THIS FILE IS FOR:
    Restaurant: forces the LLM's answer into a strict structure, and is
    also the shape of each row we store/return.
    Prompt: validates what the caller sends to POST /restaurant.

USED BY:
    restaurant_api.py imports both Restaurant and Prompt from here.
"""

from pydantic import BaseModel, Field


class Restaurant(BaseModel):
    """One restaurant suggestion.

    Fields mirror the columns of the `restaurants` table created in
    setup_db.py - keep them in the same order if you add/remove a field.
    """

    name: str = Field(description="The restaurant's name")
    cuisine: str = Field(description="Type of food served, e.g. Italian, Sushi, Vegan")
    price_level: str = Field(description="Price level as $, $$, $$$ or $$$$")
    rating: float = Field(ge=0, le=5, description="Rating out of 5")
    description: str = Field(description="A short one or two sentence description")
    opening_hours: str = Field(description="Opening hours, e.g. 'Mon-Sat 11:00-22:00'")
    location: str = Field(description="Street address or neighborhood of the restaurant")


class Prompt(BaseModel):
    """The request body for POST /restaurant.

    Example JSON body:
        {"prompt": "A cheap vegan place near Södermalm, Stockholm"}
    """

    prompt: str
