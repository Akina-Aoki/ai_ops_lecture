"""prompts.py - fetches the agents' instructions (prompts) from Logfire.

What is new in lecture 08 (compared with 07)
--------------------------------------------
In 07 the prompts were plain strings typed inside agents.py. Here they live in
the Logfire web app as "managed variables". That means you can edit a prompt
in the browser, give versions a label (e.g. "production"), and the code picks
up the change on the next run WITHOUT editing or redeploying any Python.

Role in the project
-------------------
agents.py calls `get_prompt("coach_agent_instructions")` (and the study/career
equivalents). This file asks Logfire for the text and hands it back as a str.

IMPORTANT - runs at import time
-------------------------------
The `logfire.configure(...)` call below is NOT inside a function. It runs the
moment anything does `from prompts import get_prompt` (agents.py does this).
So the order of events when you start main.py is:
    main.py imports agents.py -> agents.py imports prompts.py -> configure runs
    -> agents.py then calls get_prompt() three times (network calls to Logfire).

Setup needed in `.env`
----------------------
    LOGFIRE_PROMPTS=...   a Logfire API key that is allowed to read variables
                          (Logfire calls this scope `project:read_variables`)

Connections to other files
--------------------------
- imported by agents.py
- depends on nothing else in this folder
"""

import logfire
from logfire import VariablesOptions
from pydantic import BaseModel  # NOTE: imported but never used in this file
import os
from dotenv import load_dotenv

# NOTE: also imported but never used here. The commented-out import in
# agents.py hints that this was an alternative way to load prompts.
from pydantic_ai_harness.logfire import ManagedPrompt

# Load .env first so os.environ["LOGFIRE_PROMPTS"] below can be found.
load_dotenv()

# Connect to Logfire with an API key that can READ variables.
# `VariablesOptions()` switches on the "variables" feature (this is why the
# README installs `logfire[variables]`). With no arguments it uses defaults.
logfire.configure(
    api_key=os.environ["LOGFIRE_PROMPTS"],  # requires project:read_variables
    variables=VariablesOptions(),
)



def get_prompt(
    name: str = "coach_agent_instructions", default: str = "be a jokey assistant", label: str = "latest"
):
    """Fetch one prompt from Logfire and return its text.

    Args:
        name: the prompt's name in Logfire WITHOUT the prefix, e.g.
            "coach_agent_instructions". The variable in Logfire is called
            "prompt__coach_agent_instructions" (the prefix is added below).
        default: fallback text used if Logfire has no value for this variable.
            If your agent suddenly sounds like a joker, the fetch failed or
            the variable name/label does not exist in Logfire.
        label: which version to use. Labels are like bookmarks on versions
            (e.g. "production", "staging"), so you can test a new prompt
            without touching the live one.

    Returns:
        The prompt text (str), ready for `Agent(instructions=...)`.
    """
    # Declare a managed variable: its name in Logfire, its type, and a fallback.
    prompt = logfire.var(
        name=f"prompt__{name}",
        type=str,
        default=default,
    )
    # Download the latest values from Logfire now. `force=True` skips the local
    # cache; `_sync` means this call blocks until done (fine at start-up).
    prompt.refresh_sync(force=True)
    # Pick the version that carries the requested label.
    resolved = prompt.get(label=label)
    # Debug print so you can see WHICH version/label was loaded in the terminal.
    # print(resolved.version, resolved.label)
    return resolved.value  # the actual prompt text


# Handy for testing this file alone: `python prompts.py` prints one prompt.
if __name__ == "__main__":
    print(get_prompt(label="production"))
