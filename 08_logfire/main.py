"""main.py - entry point: run `python main.py` to start the whole system.

Role in the project
-------------------
This file does three things:
  1. turns on Logfire monitoring (traces + system metrics)
  2. builds the client profile (ClientDeps, from dependencies.py)
  3. sends one question to the `coach_agent` (from agents.py)
The coach then decides on its own to call the study/career agents and export
a report - nothing about that is written here. Logfire records every step.

How the files depend on each other
----------------------------------
    .env (NVIDIA_API, LOGFIRE_PROMPTS)
       |
       |   model.py ──────────┐        (nvidia_model: the LLM connection)
       |   dependencies.py ───┼──► agents.py ──► main.py   <── you run this one
       |   prompts.py ────────┘        (get_prompt: prompt text from Logfire)

Run order (what happens, in time):
  1. `from agents import ...` runs agents.py, which imports model.py,
     dependencies.py and prompts.py. prompts.py connects to Logfire and
     agents.py downloads the three prompts.   (this all happens BEFORE line 1
     of the code below the imports)
  2. load_dotenv() + logfire.configure() + the two instrument_* calls
  3. asyncio.run(main(...)) -> coach_agent -> (study_agent, career_agent)
     -> export_report -> print the answer
  4. open the Logfire web app to see the trace of this run.

Setup: `uv run logfire auth` once (see README.md) so logfire.configure() knows
which project to send data to; and a `.env` file with the keys above.
"""

# ClientDeps is re-exported by agents.py (it imports it from dependencies.py)
from agents import coach_agent, ClientDeps
import asyncio
import logfire
from dotenv import load_dotenv


# Load .env into os.environ (API keys etc.). Note that agents.py / model.py /
# prompts.py already called this when they were imported above.
load_dotenv()

# --- Logfire observability setup (the new thing in lecture 08) --------------
# configure(): connect this program to your Logfire project. Everything below
# sends its data there.
logfire.configure()
# Records computer metrics (CPU, memory, ...) over time. Needs the
# `logfire[system-metrics]` extra from the README.
logfire.instrument_system_metrics()
# Automatically records PydanticAI activity as spans: each agent run, each
# LLM request, each tool call, with inputs, outputs, token counts and timings.
# No changes are needed in agents.py for this to work.
logfire.instrument_pydantic_ai()
# NOTE: prompts.py also called logfire.configure(...) with its own API key
# when it was imported, so configure() is called twice in this program.


async def main(prompt: str, **kwargs):
    """Send `prompt` to the coach agent and print its final answer.

    `**kwargs` are passed straight to `Agent.run`, e.g. `deps=client`.
    `async` because PydanticAI's `run` is a coroutine (it waits on network calls).
    """
    result = await coach_agent.run(prompt, **kwargs)
    print(result.output)  # `.output` = the agent's final text reply


# Only runs when you execute this file directly, not when it's imported.
if __name__ == "__main__":
    # The deps object: the data every agent can read via `ctx.deps`.
    client = ClientDeps(
        name="Aira",
        goal="Looking for study opportunities and work opportunities within data engineering",
        experience_lvl="intermediate",
        weekly_hours=16,
        current_role="Data Engineer graduate",
    )
    # asyncio.run starts the event loop and runs our async main() until finished.
    asyncio.run(
        main(
            "I'm learning Data Warehousing and want to become a data engineer. What should I do?",
            deps=client,
        ),
    )
