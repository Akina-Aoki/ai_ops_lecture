"""
The AI that answers questions using our documents.
Sets up an AI that, when asked a question, can look through our rabbit-breed documents
and answer using what it finds.
"""

from pydantic_ai import Agent
from backend.data_models import RagResponse
from backend.constants import VECTOR_DATABASE_PATH
import lancedb
from backend.model import nvidia_model
from pydantic_ai.settings import ModelSettings

# Connect to the vector database we already built with ingestion.py.
vector_db = lancedb.connect(uri=VECTOR_DATABASE_PATH)

# This is our "AI agent" — think of it as a chatbot with three extra powers:
# 1. It has a personality/instructions (system_prompt)
# 2. It's allowed to use a tool to search our documents (defined below)
# 3. Its final answer is forced into the RagResponse shape, not free text
rag_agent = Agent(
    model=nvidia_model(),
    model_settings=ModelSettings(timeout=30, thinking="minimal"),
    retries=1,   # if the AI's answer doesn't match our required shape, try one more time
    system_prompt=(
        "You are an expert in rabbit races and knows how to distinguish between the rabbits",
        "Always answer based on the retrieved knowledge, but you can mix in your expertise to make the answer more coherent",
        "Don't hallucinate, rather say you can't answer it if the user prompts outside of the retrieved knowledge",
        "Make sure tho keep the answer clear and concise, getting to the point directly, max 6 sentences",
        "Also describe which file you have used as source",
    ),
    output_type=RagResponse,   # force the answer into our RagResponse format
)


# This line (a "decorator") tells pydantic_ai: "the AI is now allowed to
# call this function by itself, whenever it decides it needs to look
# something up to answer the question."
@rag_agent.tool_plain
def retrieve_top_documents(query: str) -> str:
    """
    Searches our vector database for the document that best matches `query`.
    The AI decides what text to search for — usually the user's question.
    """
    # .search() turns `query` into numbers too, then finds the document
    # whose numbers are the closest match. .to_list() just converts the
    # results into normal Python dictionaries we can read.
    results = vector_db["articles"].search(query=query).to_list()

    # We only use the single best match (results[0]) and hand it back to
    # the AI as plain text, so it can read it and form an answer.
    return f"""
Filename: {results[0]["filename"]},
Filepath: {results[0]["filepath"]},
Content: {results[0]["content"]}
"""