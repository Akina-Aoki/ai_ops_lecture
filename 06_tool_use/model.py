"""
model.py - a tiny helper that builds the connection to the AI model.

WHAT IS THIS FILE FOR?
    An AI agent needs a "model object": which LLM to talk to, where it lives
    (URL), and which key to use. This file builds that object in ONE place so the
    other files can just call `nvidia_model("<model-name>")`.

    (It is the same helper as in 03_pydanticai_structured_output/model.py.
    Python imports files from the folder you run from, so each lecture folder
    needs its own copy.)

WHERE THE MODEL LIVES:
    NVIDIA Build (build.nvidia.com) hosts many models behind an API that copies
    OpenAI's API format ("OpenAI-compatible"). That is why we use PydanticAI's
    OpenAI classes but point them at NVIDIA's URL instead of OpenAI's.

HOW IT CONNECTS TO THE OTHER FILES:
    model.py  <--  agents.py imports `nvidia_model` to create the weather agent
                   (and tools_basics.ipynb imports it for the dice agent).

    Big picture of this folder:
        model.py   -> WHICH AI model to use              (this file)
        tools.py   -> the Python functions the AI can call
        agents.py  -> the agent = model + instructions + tools
        main.py    -> the script you run; asks the agent questions
"""

from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider
import os
from dotenv import load_dotenv

# Reads the .env file (searching in this folder, then parent folders) and puts
# its lines, like NVIDIA_API=..., into environment variables. This keeps the
# secret key out of the code (never commit a key to git).
load_dotenv()


def nvidia_model(model_name: str) -> OpenAIChatModel:
    """Build a PydanticAI model object that talks to NVIDIA Build.

    Args:
        model_name: the model's id on NVIDIA Build,
            e.g. "nvidia/nemotron-3.5-super-vl-120b-a12b".

    Returns:
        An OpenAIChatModel you can pass to `Agent(model=...)`.

    Needs a line `NVIDIA_API=<your key>` in your .env file; otherwise
    os.environ["NVIDIA_API"] raises a KeyError.
    """
    return OpenAIChatModel(
        model_name=model_name,
        provider=OpenAIProvider(
            # Send requests to NVIDIA's server instead of OpenAI's.
            base_url="https://integrate.api.nvidia.com/v1",
            # The key that proves it's you (and counts against your free quota).
            api_key=os.environ["NVIDIA_API"],
        ),
    )
