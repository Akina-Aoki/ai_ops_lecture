"""
tools.py - the Python functions the AI is ALLOWED TO CALL ("tools").

WHY DO TOOLS EXIST? (the key idea of this whole folder)
    An LLM only produces text. It cannot check today's weather, query your
    database or call an API - and if you ask, it may confidently make something
    up. A "tool" fixes that: you write a normal Python function, and tell the
    LLM "you may ask me to run this". The LLM never runs anything itself.

    What really happens (the "tool loop"), for "What is the weather in Skövde?":

      1. Your code sends the question + a menu of tools to the LLM.
      2. LLM replies NOT with an answer but with a request:
             "please call geocode(city='Skövde')"
      3. PydanticAI (the library) runs your real Python function geocode()
         and sends the return value back to the LLM.
      4. LLM now knows lat/lon and requests: "call get_weather(lat=..., lon=...)"
      5. PydanticAI runs get_weather(), sends the result back.
      6. LLM writes the final sentence using the real data.
    Steps 2-5 can repeat as many times as the LLM needs.

    Data-engineering view: tools are how an LLM reads from the outside world
    (APIs, databases, files). The LLM is the "orchestrator" that decides WHICH
    function to call and with WHAT arguments; your function does the real work.

HOW DOES THE LLM KNOW WHAT A TOOL DOES?
    PydanticAI builds a description (a JSON schema) of each tool from:
      - the function NAME            (get_weather)
      - the PARAMETER names + TYPES  (lat: float, lon: float)
      - the DOCSTRING                ("get current weather for ...")
    The LLM only sees that description, never your code. So clear names, type
    hints and a good docstring directly improve how well the LLM uses a tool.

THE API BEHIND THE TOOLS: Open-Meteo (free, no API key needed)
    - geocoding-api.open-meteo.com : city name  -> latitude/longitude
    - api.open-meteo.com           : lat/lon    -> current weather
    That is why there are TWO tools: the weather API wants coordinates, but
    users talk about city names. The LLM chains them: geocode first, then weather.

HOW IT CONNECTS TO THE OTHER FILES:
    tools.py  <--  agents.py imports `get_weather`, `geocode` and `WeatherDeps`
                   and registers them on the weather agent.
    tools.py  <--  main.py imports `WeatherDeps` to pass context into a run.
"""

import httpx
from dataclasses import dataclass
from pydantic_ai import RunContext


@dataclass
class WeatherDeps:
    """Dependencies ("deps"): extra data we hand to the tools, but NOT to the LLM.

    A dataclass is a simple container with named fields (like a row with typed
    columns). Here it carries just the city's display name.

    WHY "DEPS"? Some information is something your CODE knows (the logged-in
    user's name, a database connection, a config value) and the LLM should not
    have to guess or be trusted with. You pass it when you run the agent
    (see main.py: deps=WeatherDeps(city="Skövde")) and tools read it through
    `ctx.deps`. The LLM never sees these values unless a tool returns them.
    """

    city: str


def get_weather(ctx: RunContext[WeatherDeps], lat: float, lon: float) -> str:
    """get current weather for latitude and longitude"""
    # ^ This docstring is NOT just documentation: the LLM reads it to decide
    #   when to use this tool. Keep it short and accurate.
    #
    # `ctx: RunContext[WeatherDeps]` is a special first parameter. PydanticAI
    # fills it in automatically and it is HIDDEN from the LLM (the LLM only
    # chooses lat and lon). Through it we reach `ctx.deps`, our WeatherDeps.

    # Call the Open-Meteo forecast API. `params` becomes the URL query string:
    #   .../forecast?latitude=57.7&longitude=11.9&current=temperature_2m
    # `current=temperature_2m` asks only for the current temperature at 2 m height.
    response = httpx.get(
        "https://api.open-meteo.com/v1/forecast",
        params={"latitude": lat, "longitude": lon, "current": "temperature_2m"},
        timeout=30,  # give up after 30 seconds instead of hanging forever
    )
    # Turn HTTP errors (404, 500, ...) into Python exceptions instead of
    # silently continuing with bad data.
    response.raise_for_status()

    # The API answers with JSON like:
    #   {"current": {"time": "...", "temperature_2m": 12.3}, ...}
    current = response.json().get("current")
    temperature = current.get("temperature_2m")

    # Whatever a tool RETURNS is sent back to the LLM as text. The city name
    # comes from deps (what our code said), not from the coordinates.
    return f"Current temperature in {ctx.deps.city} is {temperature}°C"


def geocode(city: str) -> dict:
    # Note: this tool has no docstring, so the LLM only sees its name and
    # parameter ("geocode", city: str). It works, but adding a docstring like
    # """get latitude and longitude for a city name""" would make the tool's
    # purpose clearer to the LLM.

    # Ask Open-Meteo's geocoding API for places matching the name.
    # count=1 -> only the best match.
    response = httpx.get(
        "https://geocoding-api.open-meteo.com/v1/search",
        params={"name": city, "count": 1},
    )
    response.raise_for_status()

    # The JSON looks like {"results": [{"name": ..., "latitude": ..., ...}]}.
    # [0] takes the first (best) match. If the city doesn't exist, "results" is
    # missing (None) and this line raises an error - a real project would handle that.
    place = response.json().get("results")[0]

    # Return a dict: PydanticAI converts it to JSON text for the LLM.
    return {"latitude": place.get("latitude"), "longitude": place.get("longitude")}


# --- Leftover test lines from the lecture --------------------------------
# Handy for trying a tool by hand without involving the LLM.
# WARNING: the second line is NOT commented out, so it runs (and makes a real
# web request) every time ANY file imports tools.py - e.g. each time you run
# main.py you'll see its printed output first. Delete it once you're done testing.
# print(get_weather(23, 41))
# print(geocode("gothenburg"))
