"""
chat_agent.py - the "WORKER" of the chatbot (it does the work: it talks to the AI).

THE ONE-SENTENCE VERSION:
    This file takes a filled-in ChatRequest form, asks the AI for an answer, and
    hands back a filled-in ChatResponse form.

THE ANALOGY (continued from data_models.py):
    data_models.py = the blank FORMS (ChatRequest, ChatResponse)
    chat_agent.py  = the WORKER who reads a request form, asks the AI, and fills
                     in the response form.

HOW IT DIFFERS FROM data_models.py:
    data_models.py : describes data         -> classes, no logic, never calls the AI
    chat_agent.py  : does something         -> creates the AI agent and has the
                                               `chat()` function that calls it
    chat_agent.py IMPORTS the forms from data_models.py and uses them as the
    input and output of `chat()`.

THIS FILE KNOWS NOTHING ABOUT WEB SERVERS OR WEB PAGES.
    That is on purpose: api.py handles HTTP, this file only handles the AI.
    You could call `chat()` from a notebook (see chat_eda.ipynb) and it would work.

HOW IT CONNECTS TO THE OTHER FILES:
    constants.py   --> gives the AI model name (MODEL_SMALL)
    data_models.py --> gives the ChatRequest / ChatResponse forms
    api.py         --> calls `chat(request)` from here for every POST /chat

STEP BY STEP, what happens inside `chat()`:
    1. receive a ChatRequest   {"question": "...", "message_history": [...]}
    2. send the question + the earlier messages to the AI model
    3. get the AI's text back
    4. return a ChatResponse   {"response": "...", "message_history": [...updated...]}
"""

from pydantic_ai import Agent
from dotenv import load_dotenv
from constants import MODEL_SMALL
from data_models import ChatRequest, ChatResponse

# Loads the .env file so the API key (your Gemini key) becomes an environment
# variable that PydanticAI can find. This must run BEFORE the Agent is created,
# otherwise the Agent can't find the key. Keeping keys in .env keeps secrets
# out of the code.
load_dotenv()

# The Agent = the AI model + its instructions. Created ONCE when the file loads
# and reused for every chat message.
# - First argument: which model to use (set in constants.py).
# - system_prompt: a hidden instruction sent with every conversation that
#   defines the bot's personality. The user never sees it. Edit the text to
#   change how the bot behaves.
chat_agent = Agent(
    MODEL_SMALL,
    system_prompt="Be a joking programming nerd, always answer with a programming joke. Also add emojis in your language",
)


async def chat(request: ChatRequest):
    """Take one chat message, get the AI's answer, return it.

    Args:
        request: a ChatRequest form (see data_models.py) with
            - `question`: the new user message
            - `message_history`: earlier messages (empty list for the first message)

    Returns:
        A ChatResponse form with
            - `response`: the AI's text answer
            - `message_history`: the updated conversation, to be sent back next time
    """
    # STEP 2 - ask the AI.
    # `await` because the AI takes a few seconds to answer; while we wait, the
    # server is free to handle other users. (`async def` + `await` go together.)
    # `message_history` hands the AI the earlier messages. Without it, every
    # question would be treated as a brand-new chat and the bot would forget
    # what you said before.
    result = await chat_agent.run(
        request.question, message_history=request.message_history
    )

    # STEP 4 - fill in the response form and return it.
    return ChatResponse(
        # result.output = the AI's text answer.
        response=result.output,
        # result.all_messages() = old history + this question + this answer.
        # The frontend stores it and sends it back with the next question.
        message_history=result.all_messages()
    )
