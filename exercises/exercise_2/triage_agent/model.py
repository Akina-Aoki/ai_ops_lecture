"""
model.py - Builds the LLM connection that every agent in this folder shares.

Role in the project
----------------------

- agents.py calls `nvidia_model()` ONCE and passes that single object to all 4 agents (triage, billing, technical, sales).
Code on it's own file means that if ever we switch provider (OpenAI, Google, Nvidia, etc),
we only have to change THIS file. Nothing in agents.py changes.

This is an exact copy of the helper used in 07_multiagent_handoff/model.py
and exercises/exercise_1/chatbot/chat_agent.py - same idea, same NVIDIA
endpoint, reused here so the pattern stays consistent across the course.

How it works
------------
NVIDIA hosts an "OpenAI-compatible" API: it accepts requests in the exact
same shape OpenAI's API does. So instead of writing a new client from
scratch, PydanticAI's own OpenAI classes are reused and simply pointed at
NVIDIA's URL instead of OpenAI's.

Setup needed: a `.env` file (this project keeps it at the repo root, next to
pyproject.toml) containing:
    NVIDIA_API=your_key_here
"""

import os
from dotenv import load_dotenv
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers import OpenAIProvider

# Reads the .env file and copies its key=value lines into os.environ, so the
# secret API key never has to be written directly into the code (and so it
# never ends up committed to git, since .env is in .gitignore).
load_dotenv()

def nvidia_model(model_name: str) -> OpenAIChatModel:
    """Return a PydanticAI chat model that talks to NVIDIA's hosted API.

    Args:
        model_name: NVIDIA's model id, e.g. "nvidia/nemotron-3.5-lightning-30b-a3b".

    Returns:
        An `OpenAIChatModel` you pass straight into `Agent(model=...)`
        (see agents.py).
    """    
    return OpenAIChatModel(
        model_name = model_name,
        # provider - where to send requests + how to authenticate
        provider = OpenAIProvider(
            base_url = "https://integrate.api.nvidia.com/v1",  # NVIDIA, not OpenAI
            api_keys = os.environ["NVIDIA_API"], # KeyError here = .env is missing/wrong
        ),
    )

