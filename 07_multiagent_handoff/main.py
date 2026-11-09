"""main.py - entry point: run `python main.py` to start the whole system.

Role in the project
-------------------
This file only does two things:
  1. builds the client profile (ClientDeps, from dependencies.py)
  2. sends one question to the `coach_agent` (from agents.py)
The coach then decides on its own to call the study/career agents and export
a report - nothing about that is written here.

Run order:  main.py -> coach_agent -> (study_agent, career_agent) -> export_report
"""

import asyncio

# ClientDeps is re-exported by agents.py (it imports it from dependencies.py)
from agents import ClientDeps, coach_agent


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
        goal="Looking for study opportunities and work opportunities within data engineering as a junior level",
        experience_lvl="intermediate",
        weekly_hours=10,
        current_role="Data Engineer graduate",
    )
    # asyncio.run starts the event loop and runs our async main() until finished.
    asyncio.run(
        main(
            "I'm learning AI Engineering and want to become a data engineer. What should I do?",
            deps=client,
        ),
    )
