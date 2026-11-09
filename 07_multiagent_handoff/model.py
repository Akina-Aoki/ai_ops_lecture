"""model.py - builds the LLM "connection" that every agent shares.

Role in the project
-------------------
agents.py calls `nvidia_model(...)` once and passes the result to all three
agents (study, career, coach). Keeping this in its own file means that if you
ever switch provider (OpenAI, Anthropic, ...) you only change THIS file.

How it works
------------
NVIDIA's API is "OpenAI-compatible": it speaks the same protocol as OpenAI.
So we reuse PydanticAI's OpenAI classes and just point them at NVIDIA's URL.

Setup needed: a `.env` file next to this script containing
    NVIDIA_API=your_key_here
"""

import os

from dotenv import load_dotenv
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

# Reads the `.env` file and puts its values into os.environ, so the secret key
# never has to be written in the code (and never gets committed to git).
load_dotenv()


def nvidia_model(model_name: str) -> OpenAIChatModel:
    """Return a PydanticAI chat model that talks to NVIDIA's hosted API.

    Args:
        model_name: NVIDIA's model id, e.g. "nvidia/nemotron-3.5-super-vl-120b-a12b".

    Returns:
        An `OpenAIChatModel` you pass as `Agent(model=...)` (see agents.py).
    """
    return OpenAIChatModel(
        model_name=model_name,
        # The "provider" = where to send requests + how to authenticate.
        provider=OpenAIProvider(
            base_url="https://integrate.api.nvidia.com/v1",  # NVIDIA, not OpenAI
            api_key=os.environ["NVIDIA_API"],  # KeyError here = .env is missing/wrong
        ),
    )
