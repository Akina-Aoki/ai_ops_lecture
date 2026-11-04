# Study guide: 05 Chatbot (Streamlit + FastAPI + Pydantic AI)

Keep this open next to the code in VS Code. Open the file named in the table, then read the matching section here.
This guide explains the **why**. The docstrings and comments in the files already explain the **what**.

This lecture has five Python files and one notebook. References look like `chat_agent.py` line 78, or notebook cell `[8]`.

| When you are reading... | Read this section |
| --- | --- |
| The big picture | [2. The pictures](#2-the-pictures-to-understand) |
| `constants.py` | [4.1 constants.py](#41-constantspy--which-model) |
| `data_models.py` | [4.2 data_models.py](#42-data_modelspy--the-forms) |
| `chat_agent.py` | [4.3 chat_agent.py](#43-chat_agentpy--the-worker) |
| `api.py` | [4.4 api.py](#44-apipy--the-middle-layer) |
| `frontend.py` | [4.5 frontend.py](#45-frontendpy--the-web-page) |
| `chat_eda.ipynb` | [5. The notebook](#5-the-notebook-chat_edaipynb) |
| Running it | [6. Running it](#6-running-it) |
| Any later lecture | [9. Where this connects](#9-where-this-connects) |

---

## 1. The 30-second version

Lecture 04 put an AI behind a web address. Lecture 05 builds a **chatbot** with it: a web page where you type, and a bot that remembers what you said earlier.

There are **two programs** running at the same time:

| Program | File | Job | Knows about the AI? |
| --- | --- | --- | --- |
| **Frontend** (a web page) | `frontend.py` | Draws the chat, sends what you type to the API | No |
| **Backend** (an API) | `api.py` + `chat_agent.py` | Receives a message, asks the AI, returns the answer | Yes |

and three supporting files:

| File | Job |
| --- | --- |
| `data_models.py` | The shape of a chat request and a chat response (Pydantic) |
| `constants.py` | The name of the AI model, kept in one place |
| `chat_eda.ipynb` | A notebook for exploring the same things by hand |

The one idea that makes it a *chatbot* and not a one-shot question:

> The AI **remembers nothing**. So after every answer the backend hands back the whole conversation, the frontend stores it, and sends it again with the next question.

That is lecture 02's picture A, now built for real.

---

## 2. The pictures to understand

### Picture A: two programs and how the files connect

```
 Browser                         Terminal 2                    Terminal 1
 ┌──────────────┐  you type      ┌───────────────┐   POST      ┌───────────────┐
 │  chat page   │ ─────────────► │  frontend.py  │ ──────────► │    api.py     │
 │ (Streamlit)  │ ◄───────────── │  (Streamlit)  │ ◄────────── │   (FastAPI)   │
 └──────────────┘  shows answer  └───────────────┘   JSON      └──────┬────────┘
                                                                       │ chat(request)
   data_models.py  ◄── imported by api.py and chat_agent.py            ▼
   constants.py    ◄── imported by chat_agent.py             ┌───────────────┐
                                                             │ chat_agent.py │
                                                             └──────┬────────┘
                                                                    │ over the internet
                                                                    ▼
                                                              Gemini model
```

The frontend never imports the agent. It only knows the address `http://127.0.0.1:8000/chat` and the field names.

### Picture B: one message, step by step

```
1. You type "what did I ask first?" in the page.
2. frontend.py POSTs  {"question": "...", "message_history": [ ...earlier messages... ]}
3. api.py: FastAPI checks that JSON against ChatRequest   → wrong shape = 422, nothing else runs
4. api.py calls chat(request) in chat_agent.py
5. chat_agent.py: agent.run(question, message_history=history)   → asks Gemini
6. chat_agent.py returns ChatResponse(response=text, message_history=result.all_messages())
7. api.py returns it as JSON
8. frontend.py shows "response" and stores the new "message_history" for next time
```

### Picture C: the history grows every turn

I ran the real API with a fake model and printed the message history after each turn.

```
turn 1:  [request, response]                                     2 messages    1.5 KB of JSON
turn 2:  [request, response, request, response]                  4 messages    2.7 KB
turn 3:  [req, resp, req, resp, req, resp]                       6 messages    3.9 KB
```

Two things to notice:

| Fact | Consequence |
| --- | --- |
| The history **grows by two messages every turn** | Every turn sends more text to the model, so more input tokens (lecture 02, section 5). A long chat gets slower and costs more. |
| The **system prompt appears once**, in the first request only | On turn 2 the model received: the first request (system prompt + "hello"), the first response, and the new question without a system prompt. It is carried in the history, not added again. |

---

## 3. Ideas worth understanding

### 3.1 Why split frontend and backend? ("decoupling")

`api.py` explains it in its docstring: if the page and the AI code are separate programs, you can replace one without touching the other. A mobile app or a different website could call the same `/chat` endpoint.

> **Data engineer view:** it is the same as separating a dashboard from the service that computes the numbers. The dashboard only needs the contract (the JSON fields). That is what `data_models.py` defines.

### 3.2 The API is stateless; the history lives in the browser tab

The backend remembers **nothing** between requests. It receives the history, uses it, returns the new history, and forgets. The page keeps the history in `st.session_state`.

| What happens | Result |
| --- | --- |
| You refresh the page | The chat is gone (new session state) |
| You open a second tab | A separate chat |
| You restart the API | Nothing is lost. It never stored anything. |

### 3.3 How Streamlit works (the confusing part)

Streamlit **re-runs the whole script from top to bottom** every time you do something (type a message, click a button). Ordinary variables reset on each run. That is why `frontend.py` needs two things:

1. `st.session_state`, a dictionary that survives between re-runs (one per browser tab), and
2. `display_chat_messages()`, which redraws all the old messages at the start of every run.

If you remember one sentence about Streamlit: **"the script runs again from the top after every click."**

### 3.4 `ModelMessage` and why the history is JSON

The conversation is a list of Pydantic AI message objects (lecture 02, picture B). To send it over HTTP it has to become JSON, and back. `list[ModelMessage]` in `data_models.py` lets Pydantic do both. I checked: the history from `result.all_messages()` goes out as JSON and comes back in as the same list.

In the notebook, cell `[12]` shows what that JSON looks like: each message has `parts`, a `kind` (`request` or `response`), timestamps, and each part has a `part_kind` such as `system-prompt` or `user-prompt`.

---

## 4. The files

### 4.1 `constants.py` — which model

| Line | Constant | Value |
| --- | --- | --- |
| 35 | `MODEL_SMALL` | `"google:gemini-flash-lite-latest"` (used) |
| 38 | `MODEL_MEDIUM` | `"google:gemini-flash-latest"` (not used yet) |
| 41 | `MODEL_LARGE` | `"google:gemini-pro-latest"` (not used yet) |

- The string is `"<provider>:<model>"`. This is the shortcut from lecture 04: Pydantic AI builds the provider and finds the key in the environment.
- Why a separate file: to switch models you change **one line**, not several files.
- The comments record real failures: the medium model returned 503 (overloaded), the large one 429 (over free quota). Models and free tiers change, so expect to edit these.

### 4.2 `data_models.py` — the forms

| Model | Lines | Fields |
| --- | --- | --- |
| `ChatRequest` | 47 to 72 | `question: str` (required), `message_history: list[ModelMessage] = []` |
| `ChatResponse` | 75 to 86 | `response: str`, `message_history: list[ModelMessage]` |

- **Line 67** `message_history = []`: the default is an empty list, which is what the very first message uses. If the frontend leaves the field out, the request is still valid (I tested this: `200`).
- **Line 86** `ChatResponse.message_history` has **no default**: the response always includes it.
- **Lines 70 to 72** `model_config = {"json_schema_extra": ...}` only changes the pre-filled example on the `/docs` page.
- `Field(description=...)` on lines 59 and 79 is documentation here. It shows on `/docs`. (In lecture 03 the same thing was also read by the AI. Here nothing is sent to the AI from these.)

> **Why is `ChatResponse` the same shape as part of `ChatRequest`?** Because the history the backend returns is exactly what the frontend sends back next time. The response of turn N becomes part of the request of turn N+1.

### 4.3 `chat_agent.py` — the worker

| Lines | Code | Meaning |
| --- | --- | --- |
| 36 to 39 | imports | `Agent`, `load_dotenv`, `MODEL_SMALL` from `constants.py`, the two models from `data_models.py` |
| 45 | `load_dotenv()` | Loads the key. **Must run before the Agent exists** (line 53). |
| 53 to 56 | `chat_agent = Agent(MODEL_SMALL, system_prompt=...)` | Created **once** when the file loads, reused for every message |
| 59 | `async def chat(request: ChatRequest):` | Takes a request form, returns a response form |
| 78 to 80 | `await chat_agent.run(request.question, message_history=request.message_history)` | Ask the AI, passing the earlier messages |
| 83 to 89 | `return ChatResponse(response=result.output, message_history=result.all_messages())` | Fill in the response form |

The two lines that matter most:

```python
result = await chat_agent.run(request.question, message_history=request.message_history)   # line 78-80
... message_history=result.all_messages()                                                   # line 88
```

- `message_history=` **in**: gives the model the earlier messages, so it can answer "what did I ask first?".
- `result.all_messages()` **out**: the old history plus this question plus this answer. That is what the frontend stores.

**This file knows nothing about web servers.** You could call `chat()` from a notebook. That separation is on purpose (the docstring says so).

**The system prompt** (line 55) is "Be a joking programming nerd, always answer with a programming joke. Also add emojis in your language". The page calls the bot "Ro Båt". The notebook uses a slightly different prompt (see section 5).

### 4.4 `api.py` — the middle layer

Only 23 lines of real code.

| Line | Code | Meaning |
| --- | --- | --- |
| 38 to 40 | imports | `FastAPI`, `chat`, and the two models |
| 43 | `app = FastAPI()` | The web application |
| 49 | `@app.post("/chat", response_model=ChatResponse)` | POST endpoint at `/chat`. `response_model` makes FastAPI check and document the reply. |
| 50 | `async def joke_chat(request: ChatRequest):` | `request: ChatRequest` makes FastAPI read the JSON body and validate it |
| 58 | `chat_response = await chat(request)` | Hands over to `chat_agent.py` |
| 60 | `return chat_response` | FastAPI turns it into JSON |

The function does no AI work and no validation of its own. It is a thin layer: **check the form, pass it on, return the answer**.

Compared with lecture 04: there the endpoint called the agent directly (`movies_api.py` line 81). Here the agent lives in its own file, and the endpoint only calls `chat()`.

### 4.5 `frontend.py` — the web page

No AI code at all. It draws a page and calls the API.

| Lines | Function | What it does |
| --- | --- | --- |
| 32 to 42 | `init_session_states()` | Creates two memory slots, only the first time: `messages` and `message_history` |
| 45 to 50 | `display_chat_messages()` | Redraws every earlier message, because the script re-runs |
| 53 to 91 | `handle_user_input()` | Reads the new message, calls the API, shows the answer |
| 94 to 102 | `layout()` | Title, description, old messages, then the input box |
| 107 to 109 | `if __name__ == "__main__":` | Entry point: init, then layout |

**Two lists, two jobs** (lines 34 to 42):

| Slot | Holds | Used for |
| --- | --- | --- |
| `st.session_state.messages` | `{"role": "user" or "assistant", "content": text}` | **Showing** the chat on screen |
| `st.session_state.message_history` | The Pydantic AI messages returned by the API | **Sending** back to the API so the AI remembers |

They are different because the AI needs its own message format, while the page only needs text and a role.

**Inside `handle_user_input()`:**

| Line | Code | Meaning |
| --- | --- | --- |
| 58 | `if prompt := st.chat_input("Talk to the JokeBot"):` | Draws the input box. When you press Enter it returns your text. Otherwise `None`, and the block is skipped. (`:=` assigns and tests in one step.) |
| 60 | `messages.append({"role": "user", ...})` | Remember it for the next re-run |
| 64 to 69 | `httpx.post("http://127.0.0.1:8000/chat", json={"question": ..., "message_history": ...}).json()` | The call to the backend. The JSON matches `ChatRequest`. |
| 72 | `message_history = response.get("message_history")` | Store the updated conversation |
| 75 | `bot_response = response.get("response")` | The answer text |
| 78 | `st.write(bot_response)` | Prints the raw answer. It shows up twice on the page, once raw and once in the bubble. The comment calls it a debugging aid. |
| 81 | `response = f"Ro Båt: {bot_response}"` | Adds a name label **for display only** |
| 85 to 91 | `st.chat_message(...)` | Draws the two newest bubbles and stores the bot message |

**`httpx`** is a library for making web requests from Python, like `requests`. It is what the frontend uses to call the API. The notebook uses it too.

---

## 5. The notebook: `chat_eda.ipynb`

"EDA" means exploratory data analysis. This notebook is a scratchpad for trying the agent and the API by hand, before building the pages.

**Cell numbers** here follow the same rule as the other guides: `[3]` is the 3rd **code** cell from the top, the one that shows `[3]` after Restart, then Run All. Markdown cells are called by name.

| Cell | How it starts | What it shows | Saved badge |
| --- | --- | --- | --- |
| title | markdown | `# Exploring chatting with PydanticAI and own FastAPI endpoint` | none |
| **[1]** | `from dotenv import load_dotenv` | Builds the same kind of Agent as `chat_agent.py`: `MODEL_SMALL` plus a system prompt | [1] |
| **[2]** | `result = await chat_agent.run("hello")` | First message | [2] |
| **[3]** | `print(result.output)` | The text | [3] |
| **[4]** | `chat_agent.run("what did I ask first?")` | **No history, so the bot cannot know.** It answers with an unrelated joke. | [4] |
| **[5]** | `result.all_messages()` | One request and one response. Only this run's messages. | none |
| **[6]** | `result.all_messages()[1]` | The model's response, including token usage | [3] |
| **[7]** | `chat_agent.run("what is the weather in stockholm?")` | The bot **cannot know the weather** and jokes about its API key. A tool (lecture 06) fixes this. | [5] |
| **[8]** | `chat_agent.run(..., message_history=result.all_messages())` | **With history, the bot remembers.** | [4] |
| "Testing out endpoint" | markdown | From here the notebook calls **your running API** | none |
| **[9]** | `httpx.post("http://localhost:8000/chat", json={"question": ...})` | `<Response [200 OK]>`. Needs the API running. | [8] |
| **[10]** | `result.json()["response"]` | The answer text | [9] |
| **[11]** | `result.json().keys()` | `response` and `message_history` | [10] |
| **[12]** | `msg_history = result.json()["message_history"]` | The history as JSON | [11] |
| **[13]** | `type(msg_history)` | `list` | [12] |
| **[14]** | `httpx.post(..., json={"question": ..., "message_history": msg_history})` | Sends the history back. "What did I just ask you?" gets the right answer. | [13] |
| **[15]** | `result.json()["message_history"][2]` | The new question is the third message, and it has **no system prompt** | [14] |

The saved badges are out of order, because cells were run in a different order and over different sessions. After **Restart, then Run All** they match the labels in the first column. The cells from `[9]` on need the API running at port 8000.

**The lesson of cells `[4]` and `[8]`:** the same agent, the same style of question. Without `message_history` it cannot answer. With it, it can. That is the whole difference between a one-shot call and a chatbot.

**A trap in cell `[8]`:** it passes `result.all_messages()` of whichever `result` exists at that moment. The saved answer says "You asked me 'hello'", which suggests `result` was the `hello` run when it ran. If you run cell `[7]` (weather) first, `result` is the weather run and the right answer would be "weather".

**Cell `[15]`** confirms the earlier finding: the system prompt is in the history only once, at the start. Message 3 (index 2) is just the user's new question.

---

## 6. Running it

From the docstrings in `api.py` and `frontend.py`. Use **two terminals**, both inside `05_pydanticai_fastapi_chatbot/`.

```bash
uv run uvicorn api:app --reload          # terminal 1: the backend, on port 8000
```

```bash
uv run streamlit run frontend.py         # terminal 2: the page (Streamlit opens it in your browser)
```

| Check | Address |
| --- | --- |
| Backend test page | `http://127.0.0.1:8000/docs` |
| The chat page | the address Streamlit prints (usually `http://localhost:8501`) |

Start the **backend first**. The frontend calls it on every message.

**Do not open `http://127.0.0.1:8000/chat` in the browser** (the README lists it). The browser sends a GET, and `/chat` only accepts POST, so you get `405 Method Not Allowed`. I checked. Use `/docs` and its **Try it out** button, or the page.

You need the Gemini key in the repo's `.env` (as in lecture 04).

---

## 7. What I tested

I ran your real code on **copies**, with a fake AI model, so no quota was used and no files changed.

| Test | Result |
| --- | --- |
| `POST /chat` with only `question` | `200`, response has `response` and a 2-message `message_history` |
| Send the returned history back with a second question | `200`, history now has 4 messages. The model received the first request (with the system prompt), the first answer, and the new question. |
| Third turn | 6 messages, and only **one** system prompt in the whole history |
| `message_history` set to `null` | `422` |
| `question` as a number, or missing | `422` |
| `GET /chat` | `405 Method Not Allowed` |
| Frontend after the API returns an error body | `message_history` becomes `None`, the page prints `None`, and the next request sends `null` (see gotchas) |

---

## 8. Gotchas

| Gotcha | Why | What to do |
| --- | --- | --- |
| **The chat breaks after one error.** | If the API returns an error, `response.get("message_history")` is `None` (line 72). The next request sends `null`, which `ChatRequest` rejects with `422`. I reproduced this. | Refresh the page to reset. A real fix would check the status code before saving. |
| **API not running** | `frontend.py` calls `127.0.0.1:8000` with no error handling | Start the backend first. You get a connection error from `httpx`. |
| **Slow model, `ReadTimeout`** | `httpx` waits **5 seconds** by default and `frontend.py` sets no timeout | Add `timeout=60` to `httpx.post` if the model is slow. (Lecture 01 used `timeout=` on the agent for the same reason.) |
| **Long chats get slower and costlier** | The whole history is sent every turn (picture C) | Trim old messages for long chats. This is a later topic. |
| **Refresh = lost chat** | The history lives in the tab's session state, not in a database | Fine for a demo. A real app would store it. |
| **`/chat` in the browser gives 405** | GET is not allowed | Use `/docs` |
| **404 / 429 / 503 from Gemini** | Retired model, free quota used, or overload | Change the string in `constants.py` |
| **Key not found, server will not start** | The Agent is created at import and needs the key | Check `.env`, and that `load_dotenv()` is before `Agent(...)` |
| **Port in use** | An old server is still running | Stop it, or use another port |
| **Two system prompts** | `chat_agent.py` line 55 and notebook cell `[1]` differ slightly | The page uses the one in `chat_agent.py` |
| **"Ro Båt:" is not in the history** | The label is added for display only (line 81) | The AI never sees it |
| **Raw answer shown twice** | Line 78 `st.write` plus the bubble | Delete line 78 if it bothers you |
| **The address is hard-coded** | `http://127.0.0.1:8000/chat` in line 65 | Deploying later means this changes |
| **Valid is not true** | The bot can say anything, and it still passes `ChatResponse` | Content checking comes later in the course |

---

## 9. Where this connects

| In 05 | Comes from | Goes to |
| --- | --- | --- |
| `Agent(MODEL, system_prompt=...)` | Lecture 02 (`system_prompt`) | Lecture 06 uses `instructions` instead |
| `message_history` / `all_messages()` | Lecture 02 (picture B) | The root `README.md` topics on tracing, where you can see every message |
| `async def` + `await agent.run` | Lecture 01 (`await`) | Lecture 06 `main.py` |
| `app = FastAPI()` + `@app.post` | Lecture 04 | Same pattern |
| `ChatRequest` validating input | Lecture 04 (`Prompt`) | |
| `ChatResponse` | Lecture 04 (`Movie` as response) | |
| `MODEL_SMALL` string | Lecture 04 (`"google:..."`) | Lecture 06 goes back to the Nvidia helper `model.py` |
| Notebook cell `[7]`: the bot cannot know the weather | Lecture 02 (the foggy Göteborg question) | **Lecture 06: a weather tool fixes exactly this** |
| Two programs, two terminals | New | Deployment later in the course: two things to run, so two things to deploy |

```
04   Agent behind one endpoint  ─►  stores a Movie
05   Agent behind /chat         ─►  + history, + a web page that calls it
06   Agent that can call your Python functions (tools), so it can answer "the weather in Stockholm"
```

---

## 10. Glossary (new words in 05)

| Term | Meaning |
| --- | --- |
| **Frontend** | The part the user sees and clicks (here Streamlit). |
| **Backend** | The part that does the work (here FastAPI + the agent). |
| **Decoupling** | Splitting parts so each can change without breaking the other. |
| **Streamlit** | A library that turns a Python script into a web page. |
| **Session state** | Streamlit's dictionary that survives re-runs. One per browser tab. |
| **Re-run** | Streamlit runs the whole script again after every interaction. |
| **`httpx`** | A library for calling web APIs from Python. |
| **Message history** | The earlier messages of the conversation, sent again every turn. |
| **`ModelMessage`** | Pydantic AI's type for one message. |
| **Stateless** | Remembers nothing between requests. The API is stateless. |
| **`response_model`** | A FastAPI option that checks and documents what an endpoint returns. |
| **405** | "Method not allowed": you used GET where only POST is accepted. |
| **Timeout** | How long to wait for a reply before giving up. |

---

## 11. Check yourself

Try to answer before opening each one.

<details><summary>1. Why are there two programs, and which file does each one start from?</summary>

The page (`frontend.py`, run with Streamlit) and the backend (`api.py`, run with uvicorn). Splitting them means the AI code and the page can change independently, and another frontend could call the same API.
</details>

<details><summary>2. The model has no memory. How does the bot remember what you said earlier?</summary>

The backend returns `result.all_messages()` after every answer. The frontend stores it in `st.session_state.message_history` and sends it back with the next question. The agent receives it through `message_history=`.
</details>

<details><summary>3. Why does <code>frontend.py</code> keep both <code>messages</code> and <code>message_history</code>?</summary>

`messages` is for display (role and text). `message_history` is in Pydantic AI's format and goes back to the AI. They hold different formats for different jobs.
</details>

<details><summary>4. What does it mean that Streamlit "re-runs the script"?</summary>

After every interaction the whole script runs again from the top, so ordinary variables reset. Anything to remember goes in `st.session_state`, and old messages have to be redrawn each time.
</details>

<details><summary>5. Which file validates the incoming JSON, and what happens if it is wrong?</summary>

FastAPI does, using `ChatRequest` in `api.py` (the `request: ChatRequest` parameter). A wrong shape gets an automatic `422` and `chat()` is never called.
</details>

<details><summary>6. Why does a long conversation get more expensive?</summary>

The entire history is sent to the model every turn, so the input grows by two messages each turn.
</details>

<details><summary>7. In the notebook, why can the bot answer "what did I ask first?" in cell <code>[8]</code> but not in cell <code>[4]</code>?</summary>

Cell `[8]` passes `message_history=`. Cell `[4]` does not, so the model sees only the new question.
</details>

<details><summary>8. What happens in the page after the API returns an error, and why?</summary>

`response.get("message_history")` returns `None` and is saved. The next request sends `null`, which `ChatRequest` rejects with `422`, so the chat stays broken until you refresh.
</details>

<details><summary>9. Why does opening <code>/chat</code> in the browser give 405?</summary>

A browser address bar sends GET, and the endpoint only accepts POST.
</details>

---

## 12. My questions

Add questions here as you read, then ask Claude to answer them in this file.

- [ ]
