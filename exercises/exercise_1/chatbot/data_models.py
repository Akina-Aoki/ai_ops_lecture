"""
data_models.py - the "forms" for the Socratic bot's chat messages.

ChatRequest: what the frontend sends (new question + conversation so far).
ChatResponse: what the API sends back (bot's reply + updated conversation).

USED BY:
    api.py        -> validates incoming JSON as ChatRequest, shapes the
                      reply as ChatResponse.
    chat_agent.py -> chat() takes a ChatRequest, returns a ChatResponse.
"""

from pydantic import BaseModel, Field
from pydantic_ai import ModelMessage

class ChatRequest(BaseModel):
    """This is what the frontend sends for each new message"""

    question:str = Field(description = "The user's programming question")
    # The AI has no memory between calls, so we resend earlier messages everytime
    # empty list = the first message of a new conversation.

    message_history: list[ModelMessage] = []

    model_config = {
        "json_schema_extra": {
            "example": {"question": "Why is my for loop skipping the last item?"}
        }        
    }


class ChatResponse(BaseModel):
    """What the API sends back to frontend after asking the AI"""

    response:str = Field(description = "The bot's short, Socratic reply")
    # old messages + this question + this answer; the frontend stores this
    # and sends it back as message_history next time.

    message_history: list[ModelMessage]