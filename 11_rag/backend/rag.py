"""
this is the actual “RAG” (Retrieval-Augmented Generation) logic.
It lets the AI look things up in our database before answering, instead of only relying on what it already “knows”.
"""


from pydantic_ai import Agent
from backend.data_models import RagResponse
from backend.constants import VECTOR_DATABASE_PATH
import lancedb

# Open a connection to the database folder. This runs once, the moment
# this file is imported — not every time a question comes in.
vector_db = lancedb.connect(uri=VECTOR_DATABASE_PATH)

# An "Agent" (from the pydantic-ai library) is basically: 
# an LLM (the AImodel) + instructions for how it should behave + optional tools it's allowed to use.
# Here we build the agent once, and reuse it for every question the app receives.

rag_agent = Agent(
    model = "google-gla:gemini-2.5-flash",   # which AI model answers the question
    retries = 2,                             # if the AI's reply doesn't match RagResponse's shape, try again up to 2 more times
    system_prompt = (
        # These lines are instructions given to the AI before every conversation —
        # they're not shown to the user, they just steer how it behaves.
        "You are an expert in rabbit races and knows how to distinguish between the rabbits",
        "Always answer based on the retrieved knowledge, but you can mix in your expertise to make the answer more coherent",
        "Don't hallucinate, rather say you can't answer it if the user prompts outside of the retrieved knowledge",
        "Make sure tho keep the answer clear and concise, getting to the point directly, max 6 sentences",
        "Also describe which file you have used as source",
    ),
    output_type = RagResponse,              # forces the AI's final answer to match the RagResponse shape from data_models.py
)


# This decorator (@rag_agent.tool_plain) registers the function below as a
# "tool" the AI is allowed to call on its own, whenever it decides it needs
# more information before answering. The AI itself chooses the `query` text.
@rag_agent.tool_plain
def retrieve_top_documents(query:str, k=3) -> str:
    """
    Uses vector search to find the closest k matching documents to the query

    "Vector search" means: turn `query` into an embedding (a list of numbers,
    same as we did for every stored document), then find the stored
    documents whose embeddings are numerically closest to it. That's how we
    find text that's *similar in meaning*, not just matching keywords.
    """

    results = vector_db["articles"].search(query=query).limit(k).to_list()
    # Heads-up: even though we asked for k=3 results, this only ever reads results[0]. 
    # the single best match. The other 2 are fetched but unused.
    # Worth double-checking if that's intentional in the lecture,  or something to fix as practice.

    return f"""
    
    Filename: {results[0]["filename"]},
    
    Filepath: {results[0]["filepath"]},

    Content: {results[0]["content"]}

    """    