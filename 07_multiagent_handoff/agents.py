"""agents.py - defines the three agents and how they hand work to each other.

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
- main.py          -> imports `coach_agent` and runs it
"""

from datetime import datetime
from pathlib import Path

from pydantic_ai import Agent, RunContext

from dependencies import ClientDeps  # (the original lecture file was spelled "depdencies")
from model import nvidia_model

# One model object shared by all three agents (one API connection, one config).
model = nvidia_model("nvidia/nemotron-3.5-super-vl-120b-a12b")

# --------------------------------------------------------------------------
# 1) Agent definitions
#    `deps_type=ClientDeps` tells PydanticAI what type `ctx.deps` will be, so
#    editors can autocomplete `ctx.deps.name`. The actual object is supplied
#    later in `.run(..., deps=client)`.
#    `instructions` = the system prompt: static rules for how the agent behaves.
# --------------------------------------------------------------------------

study_agent = Agent(
    model=model,
    deps_type=ClientDeps,
    instructions=(
        "You are a study expert. Give concrete study plans and learning techniques."
    ),
)

career_agent = Agent(
    model=model,
    deps_type=ClientDeps,
    instructions=(
        # NOTE: the trailing comma after this string makes it a 1-item tuple, not a str.
        # PydanticAI accepts a sequence so it still works, but it's probably unintended.
        "You are a career advisor. Give practical advice on jobs, resumes, and career paths.",
    ),
)

# The coach's prompt is a numbered workflow. LLMs follow explicit step lists
# well, and the step names match the tool names defined further below.
coach_agent = Agent(
    model=model,
    deps_type=ClientDeps,
    instructions=(
        "You are a personal coach. Follow these steps IN ORDER:\n"
        "1. Call `ask_study_agent` for study questions.\n"
        "2. Call `ask_career_agent` for career questions.\n"
        "3. Combine the answers into ONE short, simple response.\n"
        "4. Call `export_report` with that final response as `text`.\n"
        "5. Reply to the user with the final response."
    ),
)

# --------------------------------------------------------------------------
# 2) Dynamic instructions
#    `@agent.instructions` on a function adds extra prompt text computed at
#    RUN time. Unlike the static strings above, these can read `ctx.deps`
#    (the ClientDeps from main.py) - that's how each agent learns the name.
#    `ctx: RunContext[ClientDeps]` = "the run's context, whose deps is ClientDeps".
# --------------------------------------------------------------------------


@study_agent.instructions
def study_name(ctx: RunContext[ClientDeps]) -> str:
    return f"Student's name is {ctx.deps.name}. Address them by name"


@career_agent.instructions
def career_name(ctx: RunContext[ClientDeps]) -> str:
    return f"Person you are advising is {ctx.deps.name}. Address them by name"


@coach_agent.instructions
def coach_name(ctx: RunContext[ClientDeps]) -> str:
    return f"Client you are advising is {ctx.deps.name}. Address them by name"


# --------------------------------------------------------------------------
# 3) Tools on the coach (the "handoff" happens here)
#    `@agent.tool` registers a function the LLM may call. The LLM sees the
#    function NAME, its parameter types, and its DOCSTRING - so the docstrings
#    below are really prompts. Keep them clear.
#    The first parameter `ctx` is injected by PydanticAI (hidden from the LLM);
#    the other parameters (`question`, `text`) are filled in by the LLM.
# --------------------------------------------------------------------------


@coach_agent.tool
async def ask_study_agent(ctx: RunContext[ClientDeps], question: str) -> str:
    """Ask the study specialist for advice on learning and studying."""
    # deps=ctx.deps  -> pass the same client profile down, so the study agent
    #                   also knows the client's name.
    # usage=ctx.usage -> share one token/request counter across all agents,
    #                   so the total cost of the whole run is tracked together
    #                   (and usage limits apply to the full run).
    result = await study_agent.run(question, deps=ctx.deps, usage=ctx.usage)
    return result.output  # returned to the coach LLM as the tool result


@coach_agent.tool
async def ask_career_agent(ctx: RunContext[ClientDeps], question: str) -> str:
    """Ask the career specialist for advice on what to choose for a career."""
    # Same pattern as ask_study_agent, just a different specialist.
    result = await career_agent.run(question, deps=ctx.deps, usage=ctx.usage)
    return result.output


@coach_agent.tool
def export_report(ctx: RunContext[ClientDeps], text: str):
    """Export the final text to a markdown file in the `exports/` folder."""
    # Plain (non-async) tool: it does no network calls, only a quick file write.
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")  # e.g. 20261109_083600
    exports_dir = Path("exports")  # relative to where you run `python main.py`
    exports_dir.mkdir(exist_ok=True)  # create folder if missing, no error if present
    # Filename example: exports/bobby_20261109_083600.md (casefold = lowercase)
    path = exports_dir / f"{ctx.deps.name.casefold()}_{timestamp}.md"
    # encoding="utf-8" is required on Windows: the default (cp1252) cannot write
    # characters like "→" that the model often uses, and the run would crash.
    path.write_text(text, encoding="utf-8")
    # No return value -> the LLM just receives "None" as the tool result.
    # Returning the path (str(path)) would let the coach tell the user where it was saved.
