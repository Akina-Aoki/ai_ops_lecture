"""dependencies.py - the "customer file" shared by every agent in a run.

Role in the project
--------------------
In PydanticAI, "dependencies" (deps, for short) are extra data or helper
objects you hand to an agent at RUN time, WITHOUT typing them into the
prompt text. Here the deps are facts about the customer who is messaging
support - the kind of thing a real support tool would already know from
being logged in (name, account id, which plan they pay for), so the bot
does not have to ask for it again.

Flow through the project
-------------------------
main.py      creates one `CustomerDeps(...)` per customer and passes it to
             `triage_agent.run(message, deps=customer)`
agents.py    declares `deps_type=CustomerDeps` on every agent, then reads
             the values with `ctx.deps.name`, `ctx.deps.account_id`, etc.
             inside instructions functions and tool functions.

Why a dataclass and not a plain dict?
--------------------------------------
A dataclass gives every field a declared type, so your editor autocompletes
`ctx.deps.name` and warns you if you typo a field name. A dict (`deps["name"]`)
would accept any key, including a typo, and fail silently or at runtime.
"""


# decorator - automatically inspects the class’s type‑annotated fields
from dataclasses import dataclass 
#  lets you restrict a variable, parameter, or return value to one or more exact constant values
from typing import Literal


@dataclass # autogenerates __init__, __repr__, etc from the fields below
class CustomerDeps:
    """Who is messaging support. One instance is shared by every agent that
    gets involved in answering a single customer message (triage + whichever
    specialist gets picked).

    Fields without a default (name, email, account_id) are required and must
    be supplied every time one of these is created; `plan` has a default and
    is therefore optional.
    """    
    name: str
    email: str
    account_id: str
    plan: Literal["free", "pro", "enterprise"] = "free"
    # Literal = only these exact strings are allowed; a type checker (and
    # your editor) will flag anything else, e.g. CustomerDeps(plan="gold")