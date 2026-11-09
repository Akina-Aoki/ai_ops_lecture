"""agents.py - defines the three agents and how they hand work to each other.

Same multi-agent "handoff" design as lecture 07, with one change: the static
instruction strings are now fetched from Logfire via `get_prompt(...)`.

The multi-agent "handoff" pattern (agent delegation)
----------------------------------------------------
                  main.py
                     |  coach_agent.run(prompt, deps=client)
                     v
               +-------------+
               | coach_agent |  <- the manager: the only agent main.py talks to
               +-------------+
                 |    |     |  (tools = functions the LLM can choose to call)
     ask_study_agent  |   export_report -> writes exports/<name>_<time>.md
                 |    ask_career_agent
                 v          v
          study_agent    career_agent  <- specialists, each with its own instructions

Key idea: a *tool* of the coach simply calls another agent's `.run()`.
That is all "delegation" is - the specialist's answer comes back to the coach
as a normal string, and the coach combines it into the final reply.

Connections to other files
--------------------------
- model.py         -> `nvidia_model()` gives the LLM used by all agents
- dependencies.py  -> `ClientDeps` is the data (name, goal, ...) all agents can read
- prompts.py       -> `get_prompt()` downloads each agent's instructions from Logfire
- main.py          -> imports `coach_agent` and runs it

What happens when this file is imported (top to bottom)
-------------------------------------------------------
1. imports run; importing prompts.py already connects to Logfire (see prompts.py)
2. `model` is built (needs NVIDIA_API in .env)
3. three `get_prompt(...)` calls fetch the instructions over the network
4. the three Agent objects are created
5. the decorators attach the extra instructions and the coach's tools
"""

from pydantic_ai import Agent
from pydantic_ai import RunContext

# Our own files (all live in this same folder):
from model import nvidia_model  # model.py: builds the NVIDIA LLM connection

from dependencies import ClientDeps  # dependencies.py: the client profile dataclass
# (An earlier version spelled this "depdencies", which crashed with
#  ModuleNotFoundError because the file is named `dependencies.py`.)
from datetime import datetime
from pathlib import Path

# An alternative way to load prompts from Logfire; not used (kept as a note).
# from pydantic_ai_harness.logfire import ManagedPrompt
from prompts import get_prompt  # prompts.py: fetches prompt text from Logfire


# One model object shared by all three agents (one API connection, one config).
model = nvidia_model("nvidia/nemotron-3.5-super-vl-120b-a12b")

# --------------------------------------------------------------------------
# 1) Agent definitions
#    `deps_type=ClientDeps` tells PydanticAI what type `ctx.deps` will be, so
#    editors can autocomplete `ctx.deps.name`. The actual object is supplied
#    later in `.run(..., deps=client)`.
#    `instructions` = the system prompt: static rules for how the agent behaves.
#    NEW vs lecture 07: the text is not written here, it comes from Logfire.
#    The string passed to get_prompt() must match a prompt in your Logfire
#    project, stored under the name "prompt__<that string>".
# --------------------------------------------------------------------------

study_agent = Agent(
    model=model,
    deps_type=ClientDeps,
    instructions=get_prompt("study_agent_instructions"),
)

career_agent = Agent(
    model=model,
    deps_type=ClientDeps,
    instructions=get_prompt("career_agent_instructions"),
)

# The coach's prompt (in Logfire) should tell it to call the tools defined
# further below (`ask_study_agent`, `ask_career_agent`, `export_report`) - the
# tool names in the prompt must match the function names in this file.
coach_agent = Agent(
    model=model,
    deps_type=ClientDeps,
    instructions=get_prompt("coach_agent_instructions"),
)


# --------------------------------------------------------------------------
# 2) Dynamic instructions
#    `@agent.instructions` on a function adds extra prompt text computed at
#    RUN time. Unlike the Logfire prompts above, these can read `ctx.deps`
#    (the ClientDeps from main.py) - that's how each agent learns the name.
#    `ctx: RunContext[ClientDeps]` = "the run's context, whose deps is ClientDeps".
#    Final prompt the LLM sees = Logfire prompt + this extra sentence.
# --------------------------------------------------------------------------


@study_agent.instructions
def study_name(ctx: RunContext[ClientDeps]) -> str:
    return f"Student's name is {ctx.deps.name}. Address them by name"


@career_agent.instructions
def career_name(ctx: RunContext[ClientDeps]) -> str:
    return f"Person you are advising is {ctx.deps.name}. Address them by name"


@coach_agent.instructions
def coach_name(ctx: RunContext[ClientDeps]) -> str:
    return f"Client you are advicing is {ctx.deps.name}. Address them by name"


# --------------------------------------------------------------------------
# 3) Tools on the coach (the "handoff" happens here)
#    `@agent.tool` registers a function the LLM may call. The LLM sees the
#    function NAME, its parameter types, and its DOCSTRING - so the docstrings
#    below are really prompts. Keep them clear.
#    The first parameter `ctx` is injected by PydanticAI (hidden from the LLM);
#    the other parameters (`question`, `text`) are filled in by the LLM.
#    Because main.py calls logfire.instrument_pydantic_ai(), every one of these
#    tool calls (and the nested agent runs) shows up as spans in Logfire.
# --------------------------------------------------------------------------


# delegation tools
@coach_agent.tool
async def ask_study_agent(ctx: RunContext[ClientDeps], question: str) -> str:
    """ask study specialist for advice on learning and studying"""
    # deps=ctx.deps  -> pass the same client profile down, so the study agent
    #                   also knows the client's name.
    # usage=ctx.usage -> share one token/request counter across all agents,
    #                   so the total cost of the whole run is tracked together.
    result = await study_agent.run(question, deps=ctx.deps, usage=ctx.usage)
    return result.output  # returned to the coach LLM as the tool result


@coach_agent.tool
async def ask_career_agent(ctx: RunContext[ClientDeps], question: str) -> str:
    """ask career specialist for advice on what to choose for a career"""
    # Same pattern as ask_study_agent, just a different specialist.
    result = await career_agent.run(question, deps=ctx.deps, usage=ctx.usage)
    return result.output


@coach_agent.tool
def export_report(ctx: RunContext[ClientDeps], text: str):
    """exports the text to specified path"""
    # Plain (non-async) tool: it does no network calls, only a quick file write.
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")  # e.g. 20261109_083600
    exports_dir = Path("exports")  # relative to where you run `python main.py`
    exports_dir.mkdir(exist_ok=True)  # create folder if missing, no error if present
    # Filename example: exports/bobby_20261109_083600.md (casefold = lowercase)
    path = exports_dir / f"{ctx.deps.name.casefold()}_{timestamp}.md"
    # Note: unlike lecture 07, there is no encoding="utf-8" here. On Windows the
    # default encoding can crash on characters like "→" that models often write.
    path.write_text(text)
    # No return value -> the LLM just receives "None" as the tool result.
