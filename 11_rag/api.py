"""
it’s the “front door” — the only way outside code (like our Streamlit app) can reach rag_agent is through this HTTP endpoint.
"""

from fastapi import FastAPI
from backend.rag import rag_agent
from backend.data_models import Prompt

# FastAPI is a web framework: it lets other programs (like our Streamlit app) 
# talk to this Python code over the network, using HTTP requests.

app = FastAPI()

# @app.get("/test") means: "when someone sends a GET request to /test,
# run this function." It's just a quick way to check the server is alive.

@app.get("/test")
async def test():
    return {"test": "hello"}


# @app.post("/rag/query") means: "when someone sends a POST request (i.e.
# they're submitting data, not just asking for a page) to /rag/query,
# run this function." FastAPI automatically checks the incoming data
# matches the Prompt shape from data_models.py before even calling this.
@app.post("/rag/query")
async def query_documentation(query:Prompt):
    # "async def" + "await" let this function pause while waiting on the
    # slow part (calling the AI model) without freezing the whole server —
    # other requests can still be handled in the meantime.
    result = await rag_agent.run(query.prompt)

    # .output is the AI's answer, already shaped like RagResponse.
    # FastAPI automatically converts it to JSON before sending it back.
    return result.output