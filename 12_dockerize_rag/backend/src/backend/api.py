"""
The door other programs knock on.
Turns our AI agent into a web service other programs (like the Streamlit frontend)
can send questions to over the internet.
"""

from fastapi import FastAPI
from backend.rag import rag_agent
from backend.data_models import Prompt
import logfire

app = FastAPI()

# Logfire is a tool that records what our app is doing behind the scenes
# (which requests came in, how long the AI took, etc.) so we can look at it
# later in a dashboard if something goes wrong.
logfire.configure()
logfire.instrument_pydantic_ai()   # automatically track every AI run
logfire.instrument_fastapi(app)    # automatically track every web request


@app.get("/test")
async def test():
    """
    A simple "is this thing on?" check. If you visit this address in a
    browser and get {"test": "hello"} back, the server is working.
    """
    return {"test": "hello"}


@app.post("/rag/query")
async def query_documentation(query: Prompt):
    """
    This is the main door the frontend knocks on to ask a question.
    FastAPI automatically checks that the incoming data matches our
    Prompt shape before this function even starts running.
    """
    # Hand the user's question to our AI agent and wait for its answer.
    result = await rag_agent.run(query.prompt)

    # .output holds the answer in our RagResponse shape. FastAPI turns it
    # into JSON automatically before sending it back to whoever asked.
    return result.output