"""
agents.py - assembles the weather AGENT: model + instructions + tools.

WHAT IS AN AGENT?
    An agent is the LLM wrapped together with everything it needs to do a job:
        - which MODEL to use            (from model.py)
        - INSTRUCTIONS for its behavior (written below)
        - TOOLS it may call             (from tools.py)
    When you call `agent.run("...")`, PydanticAI runs the "tool loop" described
    in tools.py: send question -> LLM asks for a tool -> we run it -> send the
    result back -> repeat until the LLM gives a final text answer.

    This file only BUILDS the agent (like configuring a worker). It doesn't run
    anything; main.py is what actually asks it questions.

HOW IT CONNECTS TO THE OTHER FILES:
    model.py  --> `nvidia_model(...)`: the AI model object
    tools.py  --> `get_weather`, `geocode` (the tools) and `WeatherDeps` (context type)
    main.py   <-- imports `weather_agent` from here and calls `.run(...)`

    Flow:  main.py -> weather_agent (this file) -> LLM <-> tools.py -> Open-Meteo API
"""

from pydantic_ai import Agent
from model import nvidia_model
from tools import geocode, get_weather, WeatherDeps
# A Toolset is a named bundle of tools. FunctionToolset builds one from plain
# Python functions.
from pydantic_ai.toolsets import FunctionToolset

weather_agent = Agent(
    # The LLM to use, hosted on NVIDIA Build (see model.py).
    model=nvidia_model("nvidia/nemotron-3.5-super-vl-120b-a12b"),
    # `instructions` = the agent's job description, sent to the LLM on every run.
    # Tips for reading it:
    #   - "always answer short"      -> keeps output cheap and easy to parse
    #   - "use the available tools"  -> pushes the LLM to fetch real data instead
    #                                   of guessing the weather from memory
    #   - "decline non-weather"      -> a guardrail: keeps the agent on topic
    #                                   (that's why main.py's joke request gets refused)
    instructions=(
        "You are a helpful weather assistant, and always answer "
        "short and concise. Never add more text than neccessary."
        " use the available tools whenever possible. When there "
        " are questions that are not about weather, decline them"
    ),
    # The menu of tools the LLM may request. Order doesn't matter: the LLM
    # chooses based on each tool's name, parameters and docstring (see tools.py).
    # (Alternative style, used in tools_basics.ipynb: decorate each function with
    # @agent.tool / @agent.tool_plain. A toolset is handy when the same tools
    # are shared between several agents.)
    toolsets=[FunctionToolset([get_weather, geocode])],
    # Tells PydanticAI what type of "deps" object this agent expects at run time.
    # It lets tools declare `ctx: RunContext[WeatherDeps]` and get `ctx.deps.city`
    # with proper type hints / editor autocomplete. At run time you must pass
    # an instance: agent.run(..., deps=WeatherDeps(city="..."))
    deps_type=WeatherDeps
)
