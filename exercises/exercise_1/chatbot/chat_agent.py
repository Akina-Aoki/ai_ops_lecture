"""
chat_agent.py - the AI logic for the Socratic programming bot.

Knows nothing about HTTP - api.py handles that. This file only builds the
Agent and exposes chat(), so it could just as well be called from a notebook.

HOW IT CONNECTS:
    data_models.py --> ChatRequest / ChatResponse shapes
    api.py          --> calls chat(request) for every POST /chat
"""

import os
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider
from dotenv import load_dotenv

from data_models import ChatRequest, ChatResponse

load_dotenv()

model = OpenAIChatModel(
    "nvidia/nemotron-3.5-lightning-30b-a3b",
    provider=OpenAIProvider(
        base_url="https://integrate.api.nvidia.com/v1",
        api_key=os.environ["NVIDIA_API"],
    ),
)

# This system prompt is what makes the bot "Socratic": told to ask guiding
# questions instead of giving the solution, and to keep replies short.
socratic_agent = Agent(
    model,
    system_prompt=(
        "You are a Socratic programming tutor. Never give the direct answer "
        "or write the solution code. Instead, respond with a short guiding "
        "question (1-3 sentences) that helps the student figure it out "
        "themselves. Keep every reply brief - no long explanations."
    ),
)


async def chat(request: ChatRequest) -> ChatResponse:
    """Take one chat message, ask the AI, return its reply + updated history.

    Args:
        request: `question` (the new message) and `message_history`
            (earlier turns, empty on the first message).

    Returns:
        A ChatResponse with the bot's reply and the full updated history.
    """
    # message_history lets the agent "remember" earlier turns; without it,
    # every question would be treated as a brand-new conversation.
    result = await socratic_agent.run(
        request.question, message_history=request.message_history
    )

    return ChatResponse(
        response=result.output,
        # old history + this question + this answer, ready to send back next time.
        message_history=result.all_messages(),
    )