# Exercise 1, Part 2 - Socratic Programming Bot

A chatbot that helps with programming questions by asking short, guiding
questions back instead of giving the answer directly.

## Files

| File | What it does |
| --- | --- |
| [data_models.py](data_models.py) | `ChatRequest` / `ChatResponse`: the shape of a chat message |
| [chat_agent.py](chat_agent.py) | The PydanticAI agent and `chat()`, which actually talks to the LLM |
| [api.py](api.py) | FastAPI app with one endpoint: `POST /chat` |
| [frontend.py](frontend.py) | Streamlit chat page that calls the API |

Flow: `frontend.py` sends your question to `api.py`, which calls `chat()` in
`chat_agent.py`, which asks the LLM and returns a short, Socratic reply.

## How to run it

**1. Open a terminal and move into this folder:**
```bash
cd exercises/exercise_1/chatbot
```

**2. Start the API** (leave this terminal running):
```bash
uv run uvicorn api:app --reload
```
Wait for `Uvicorn running on http://127.0.0.1:8000`.

**3. Open a second terminal, move into this folder again:**
```bash
cd exercises/exercise_1/chatbot
```

**4. Start the Streamlit frontend** (leave this terminal running too):
```bash
uv run streamlit run frontend.py
```
This opens `http://127.0.0.1:8501` in your browser.

**5. Try it** - type a programming question in the chat box, e.g. "Why is my
for loop skipping the last item?". You should get a short guiding question
back, not the answer.

To stop either one, click into that terminal and press `Ctrl+C`.
