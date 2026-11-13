"""
## 1. FastAPI to serve PydanticAI

Now make a fastapi with a post endpoint in natural language to prompt for a location and what type of food. Based on these it should generate a restaurant and store it in a duckdb database.

Also implement a get endpoint for showing all restaurants in the database. Implement a simple frontend in for example streamlit to consume this API.
"""

########################################################################################################################################################################################################

"""
data_models.py - the "shape" of our data (Pydantic models).

WHAT THIS FILE IS FOR:
    Restaurant: forces the LLM's answer into a strict structure, and is
    also the shape of each row we store/return.
    Prompt: validates what the caller sends to POST /restaurant.

USED BY:
    restaurant_api.py imports both Restaurant and Prompt from here.
"""

from Pydantic import BaseModel, Field

class Restaurant(BaseModel):
    """
    One restaurant suggestion.
    Validate body with Prompt (Pydantic) 
    """

    name: str = Field(description = "The restaurant's name")
    cuisine: str = Field(description = "Type of food served")
    price_level: str = Field(description = "Price level as $, $$, $$$ or $$$$")
    rating: float = Field(ge=0, le=5, description = "Rating out of 5")
    description = str = Field(description = "A short one or two sentence description")
    opening_hours: str = Field(description = "Opening hours, e.g. 'Mon-Sat 11:00-22:00'")
    location: str = Field(description = "Street address or neighborhood of the restaurant")


    class Prompt(BaseModel):
        """
        Ask the LLM for a Restaurant by
        request body for POST /restaurant, e.g.
        {"prompt": "A cheap vegan place near Södermalm, Stockholm"}"""

        prompt: str