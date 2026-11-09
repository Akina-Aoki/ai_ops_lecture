"""dependencies.py - the "client profile" shared by every agent in a run.

Role in the project
-------------------
In PydanticAI, "dependencies" (deps) are extra data/helpers you hand to an
agent at run time, WITHOUT putting them in the prompt text. Here the deps are
information about the person being coached.

Flow:
  main.py      creates a `ClientDeps(...)` and passes it to `coach_agent.run(..., deps=client)`
  agents.py    declares `deps_type=ClientDeps` on each agent, then reads values
               with `ctx.deps.name` inside instructions and tools.
"""

from dataclasses import dataclass
from typing import Literal


@dataclass  # auto-generates __init__, __repr__ etc. from the fields below
class ClientDeps:
    """Who we are coaching. One instance is shared by coach, study and career agents.

    Fields without a default (name, goal) are required; the rest are optional.
    """

    name: str  # used to address the person by name in every agent
    goal: str  # what the client wants to achieve
    # Literal = only these exact strings are allowed (type checkers will warn otherwise)
    experience_lvl: Literal["beginner", "intermediate", "advanced"] = "beginner"
    weekly_hours: int = 8  # study time available per week
    current_role: str | None = None  # None = not provided / unemployed
