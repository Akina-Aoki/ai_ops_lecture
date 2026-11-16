"""
api.py - FastAPI server with one endpoint, POST /chat.

DATA FLOW:
    frontend.py --POST /chat {"question": ..., "message_history": [...]}--> api.py
                                | validates body as ChatRequest   (data_models.py)
                                | calls chat(request)             (chat_agent.py)
                                v
    frontend.py <-- {"response": ..., "message_history": [...]} --

RUN (two terminals, from this folder):
    uvicorn api:app --reload
    streamlit run frontend.py
"""

from fastapi import FastAPI
from chat_agent import chat
from data_models import ChatRequest, ChatResponse

app = FastAPI()


@app.post("/chat", response_model=ChatResponse)
async def socratic_chat(request: ChatRequest):
    """Receive a message, get the bot's Socratic reply, return it.

    `request: ChatRequest` makes FastAPI validate the body before this
    function runs - a missing `question` gets an automatic 422.
    """
    return await chat(request)