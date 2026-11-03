"""
data_models.py - the "FORMS" of the chatbot (it describes data, it does NOT do work).

THE ONE-SENTENCE VERSION:
    This file defines what a chat message must LOOK LIKE.
    Nothing in here runs the AI, calls a server or sends anything.

THE ANALOGY - think of paper forms:
    ChatRequest  = the form the user FILLS IN   (question + earlier messages)
    ChatResponse = the form the bot FILLS IN    (answer + updated messages)
    These are just blank forms with labelled boxes. The code that actually fills
    them in lives in chat_agent.py (the "worker").

    Pydantic is the form checker: if someone hands in a form with a missing or
    wrong box (e.g. "question" is a number, or is missing), Pydantic rejects it
    with a clear error before any of our real code runs.

HOW IT DIFFERS FROM chat_agent.py:
    data_models.py : "What does a message look like?"   -> classes, no logic
    chat_agent.py  : "How do we get an answer for it?"  -> a function that calls the AI
    Both are needed: chat_agent.py takes a ChatRequest IN and gives a ChatResponse OUT.

WHO USES THIS FILE:
    - api.py        imports both. FastAPI uses them to check incoming JSON
                    (ChatRequest) and to format the reply JSON (ChatResponse).
    - chat_agent.py imports both. `chat()` receives a ChatRequest and returns a
                    ChatResponse.
    - frontend.py   does not import them, but it sends and reads JSON with the
                    SAME field names ("question", "message_history", "response").

A MESSAGE'S JOURNEY (what each form looks like in JSON):
    1. frontend sends a ChatRequest:
           {"question": "Tell me a joke", "message_history": []}
    2. api.py checks it against ChatRequest, passes it to chat_agent.py
    3. chat_agent.py asks the AI and builds a ChatResponse:
           {"response": "Why do Python devs wear glasses? ...",
            "message_history": [ ...2 messages... ]}
    4. frontend shows "response" and keeps "message_history" for the next question.
"""

from pydantic import BaseModel, Field
# ModelMessage is PydanticAI's type for ONE message in a conversation
# (a system prompt, a user message, or an AI reply).
from pydantic_ai import ModelMessage


class ChatRequest(BaseModel):
    """The form the FRONTEND fills in and sends to the API for each new message.

    Example that passes the check:
        ChatRequest(question="Tell me a joke about Python")
    Example that FAILS the check (Pydantic raises an error):
        ChatRequest()                  # "question" is missing
        ChatRequest(question=123)      # "question" must be text
    """

    # Box 1: the user's new message. Required (no default value).
    # Field(description=...) is only documentation; it appears on FastAPI's /docs page.
    question: str = Field(
        description="users message or question to JokeBot",
    )

    # Box 2: the conversation so far. Optional: it defaults to an empty list [],
    # which is what the very first message of a chat uses.
    # WHY SEND IT AT ALL? An AI model has NO memory between calls. To make it
    # "remember", we send the earlier messages again with every new question.
    message_history: list[ModelMessage] = []

    # Only affects the /docs page: the pre-filled example in the "Try it out" box.
    model_config = {
        "json_schema_extra": {"example": {"question": "Tell me a joke about Python"}}
    }


class ChatResponse(BaseModel):
    """The form the BOT fills in and the API sends back to the frontend."""

    # Box 1: the AI's text answer (what the user reads).
    response: str = Field(
        description="The JokeBot's response including a programming joke and emojis"
    )

    # Box 2: the updated conversation = old messages + the new question + the new answer.
    # The frontend stores this and sends it back as `message_history` next time.
    # No default value here: the response always includes it.
    message_history: list[ModelMessage]
