"""
main.py - the ENTRY POINT: the script you actually run.

WHAT IS THIS FILE FOR?
    It imports the finished weather agent from agents.py, asks it two questions,
    and prints the answers. It is the "client" that uses everything else.

    Run it from inside the 06_tool_use folder:
        uv run main.py

    Requirements: a .env file containing NVIDIA_API=<your key> (read by model.py),
    and an internet connection (the tools call the Open-Meteo API).

HOW ALL THE FILES CONNECT (what happens when you run it):

    main.py                       "What is the weather in Skövde?"
       |  agent.run(prompt, deps=WeatherDeps(city="Skövde"))
       v
    agents.py  (weather_agent)    model + instructions + tools
       |   asks the LLM (model.py -> NVIDIA Build)
       |   LLM: "call geocode('Skövde')"        --> tools.py runs it -> lat/lon
       |   LLM: "call get_weather(lat, lon)"    --> tools.py runs it -> temperature
       |   LLM writes the short final answer
       v
    main.py                       prints it, e.g. "Current temperature in Skövde is 8.1°C"

WHAT YOU SHOULD SEE:
    Question 1 (weather)     -> the agent uses its tools and answers with real data.
    Question 2 (joke)        -> the agent's instructions say "decline non-weather
                               questions", so it politely refuses. This shows
                               instructions acting as a guardrail.
    (You will also see a printed dict first: a leftover test line at the bottom of
    tools.py runs when tools.py is imported.)
"""

from agents import weather_agent
import asyncio
from tools import WeatherDeps


async def main(prompt, **kwargs):
    """Ask the weather agent one question and print the answer.

    Args:
        prompt: the user's question as plain text.
        **kwargs: extra options passed straight to `agent.run`. We use it to pass
            `deps=...`, the context object the tools can read (see WeatherDeps
            in tools.py).
    """
    # `async`/`await`: the run involves slow network calls (to the LLM and to
    # Open-Meteo). `await` pauses this function while waiting, instead of
    # blocking the whole program. The agent's run() is itself an async function.
    result = await weather_agent.run(prompt, **kwargs)
    # result.output = the final text from the LLM, after all tool calls are done.
    print(result.output)


# Only runs when you start THIS file directly (uv run main.py), not when
# another file imports it.
if __name__ == "__main__":
    # asyncio.run(...) starts the async function from normal synchronous code.
    # `deps=WeatherDeps(city="Skövde")` is data for the TOOLS (get_weather uses it
    # to label the temperature with a city name). The LLM does not see it directly.
    # Heads-up: the question and deps are two separate things - if they named
    # different cities, the printed city label would not match the weather asked for.
    asyncio.run(main("What is the weather in Skövde?", deps = WeatherDeps(city="Skövde")))
    # Off-topic question to test the guardrail. We still must pass deps because
    # the agent was created with deps_type=WeatherDeps.
    asyncio.run(main("Tell me a programming joke", deps=WeatherDeps(city="London")))
