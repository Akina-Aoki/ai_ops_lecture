"""
api.py - the web API that sits between the frontend and the AI agent.

WHAT IS THIS FILE FOR?
    It starts a FastAPI server with ONE endpoint, POST /chat. The frontend
    sends a chat message to it, it hands the message to the agent in
    chat_agent.py, and it returns the answer as JSON.

    Why not let the frontend call the agent directly? Putting an API in
    between ("decoupling") means the frontend and the AI logic are separate
    parts. You could replace Streamlit with another frontend (a mobile app,
    another website) and the backend would not change.

HOW ALL THE FILES CONNECT (what happens when you send a message):

    frontend.py (Streamlit page in your browser)
        |  1. POST http://127.0.0.1:8000/chat  {"question": ..., "message_history": [...]}
        v
    api.py  (this file)
        |  2. FastAPI checks the JSON against ChatRequest        (data_models.py)
        |  3. calls chat(request)                                (chat_agent.py)
        v
    chat_agent.py
        |  4. asks the LLM named in constants.py, using the system prompt + history
        v
    api.py
        |  5. returns a ChatResponse {"response": ..., "message_history": [...]}
        v
    frontend.py shows the answer and stores the new history

HOW TO RUN (two terminals, both inside this folder):
    Terminal 1 (backend):   uv run uvicorn api:app --reload
    Terminal 2 (frontend):  uv run streamlit run frontend.py
    The API's test page is at http://127.0.0.1:8000/docs
    Make sure your .env file contains the API key for the model provider.
"""

from fastapi import FastAPI
from chat_agent import chat
from data_models import ChatResponse, ChatRequest

# The web application object; the decorator below registers endpoints on it.
app = FastAPI()


# @app.post = "when someone sends a POST request to /chat, run this function".
# response_model=ChatResponse tells FastAPI to check and format the returned
# data as a ChatResponse (and to document it on the /docs page).
@app.post("/chat", response_model=ChatResponse)
async def joke_chat(request: ChatRequest):
    """Receive a chat message, get the AI's answer, return it.

    `request: ChatRequest` makes FastAPI read the JSON body, validate it, and
    give us a ready-to-use object. Invalid JSON gets an automatic 422 error
    before this function even runs.
    """
    # All the AI work happens in chat_agent.py; this function only passes data through.
    chat_response = await chat(request)

    return chat_response
