"""
constants.py - one place to keep the names of the AI models we can use.

WHAT IS THIS FILE FOR?
    Instead of typing a long model string in several files, we store it once
    here and import it where needed (chat_agent.py imports MODEL_SMALL).
    To switch models you change ONE line here, not many files.

HOW TO READ THE MODEL STRINGS:
    "<provider>:<model-name>"
        - "google" = call a Gemini model through Google's API
          (it reads your key from the .env file: GOOGLE_API_KEY or GEMINI_API_KEY).
        - "-latest" = an alias that always points to a current version, because
          Google retires specific model versions quite often.

    Free-tier models can be rate-limited (429) or overloaded (503), and old
    ones get retired (404). If one stops working, try another model name and
    replace the string here.

HOW IT CONNECTS TO THE OTHER FILES:
    chat_agent.py  <-- imports MODEL_SMALL from here.
    (MODEL_MEDIUM and MODEL_LARGE are not used yet; they are ready to swap in
    if you want smarter, but slower, answers.)

BIG PICTURE (the whole project):
    frontend.py  -> Streamlit web page the user types into
    api.py       -> FastAPI server that receives the chat messages
    chat_agent.py-> the AI agent that writes the replies
    data_models.py -> the shape of the data sent between frontend and API
    constants.py -> (this file) which AI model to use
"""

# Smallest and fastest model: cheap, but gives simpler answers.
# (Tested and working with a free Gemini key.)
MODEL_SMALL = "google:gemini-flash-lite-latest"
# Middle option: a balance between speed and quality.
# (When last tested it was often overloaded, error 503.)
MODEL_MEDIUM = "google:gemini-flash-latest"
# Biggest model: best answers, but slowest.
# (When last tested it was over the free quota, error 429.)
MODEL_LARGE = "google:gemini-pro-latest"
