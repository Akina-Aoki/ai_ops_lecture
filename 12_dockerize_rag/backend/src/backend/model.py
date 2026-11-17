"""
Which AI brain are we using?
"""

from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider
import os
from dotenv import load_dotenv

load_dotenv()

"""
Sets up and returns the AI model we'll ask questions to.
We keep this in its own small function so that if we ever switch AI
providers, we only change it here — not everywhere rag.py uses it.
"""

def nvidia_model(
    model_name: str = "nvidia/nemotron-3.5-super-vl-120b-a12b",
) -> OpenAIChatModel:
    return OpenAIChatModel(
        model_name=model_name,
        provider=OpenAIProvider(
            base_url="https://integrate.api.nvidia.com/v1",
            api_key=os.environ["NVIDIA_API"],
        ),
    )