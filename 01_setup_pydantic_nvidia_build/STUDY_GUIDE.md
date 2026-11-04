# Study guide: 01 Setup Pydantic AI + Nvidia Build

Keep this open next to `pydanticai_nvidia.ipynb`. Read a cell in the notebook, then read the matching section here.
This guide explains the **why**. The notebook and its comments already explain the **what**.

**How cells are numbered here.** VS Code shows a badge like `[2]` to the left of each **code** cell after it runs. In this guide `[2]` means the **2nd code cell from the top**, which is the cell that shows `[2]` after **Restart, then Run All**. Markdown cells have no badge, so I call them by their heading. Line numbers are lines **inside** the cell.

| Guide label | Type | How the cell starts | Badge saved in the file today |
| --- | --- | --- | --- |
| title | markdown | `# Pydantic AI and Nvidia Build models` | none |
| **[1]** | code (2 lines) | `# Agent: ...` then `from pydantic_ai import Agent` | [1] |
| "It imports the Agent class..." | markdown | explains the import | none |
| **[2]** | code (34 lines) | `# OpenAIChatModel: a wrapper...` then all imports, model, agent, first question | [2] |
| **[3]** | code | `result = await agent.run("Tell a joke", timeout = 120)` | [5] |
| **[4]** | code | `result.output` | [6] |
| "Update the model on the fly" | markdown | `# Update the model on the fly` | none |
| **[5]** | code | `new_model = OpenAIChatModel(` | [7] |
| "This model just HALLUCINATED" | markdown | `### This model just HALLUCINATED` | none |
| **[6]** | code | `result = await agent.run(` then "Explain how Pydanticai differs..." | [9] |
| **[7]** | code | `with open("pydanticai.md", "w") as file:` | none |

The saved badges are out of order for cells [3] to [6] because they were run in a different order. After **Restart, then Run All** every badge matches the guide label. If a number ever disagrees with what you see, match the cell by how it starts (third column).

| When you are reading... | Read this section |
| --- | --- |
| `README.md` (uv, `uv add`) | [3. The setup half](#3-the-setup-half-why-each-piece-exists) |
| Notebook cell [1] (`import Agent`) | [4. Cell [1]](#cell-1--import-agent) |
| Notebook cell [2] (the big one) | [4. Cell [2]](#cell-2--the-main-cell-built-from-the-inside-out) |
| Notebook cells [3] to [7] | [5. Cells [3] to [7]](#5-cells-3-to-7-what-each-experiment-teaches) |
| Any later lecture | [6. Where this reappears](#6-where-this-reappears-in-later-lectures) |

---

## 1. The 30-second version

An **LLM** (large language model) is a program that takes text in and gives text back. It is too big to run on your laptop, so a company runs it on their servers and lets you use it over the internet. Here the company is **Nvidia** (build.nvidia.com).

**Pydantic AI** is a Python library that makes that internet call easy. Without it you would write the web request, the JSON, the login header and the error handling yourself. With it you write about 10 lines.

Everything in lecture 01 is answering one question:

> How do I make Python send a question to an AI model and get the answer back?

The answer is **three objects and one call**:

```
Provider  = where the server is + my password
Model     = which AI brain, reached through that provider
Agent     = the thing I talk to (wraps the model)
agent.run = send the question, get the answer
```

---

## 2. The one picture to understand

### What you build (once), and what happens (each question)

```
BUILD, once (cell [2])                    RUN, every question

provider = OpenAIProvider(                 result = await agent.run("question")
    base_url=..., api_key=...)                          │
        │ goes inside                                   ▼
model = OpenAIChatModel(name, provider)               Agent
        │ goes inside                                   │ asks its model
agent = Agent(model)                                    ▼
                                                      Model
                                                        │ uses its provider
                                                        ▼
                                                     Provider
                                                        │   HTTPS request over the internet
                                                        ▼
                                  https://integrate.api.nvidia.com/v1/chat/completions
                                                        │   Nvidia runs the AI
                                                        ▼
                                                  text answer comes back
                                                        │
                                                        ▼
                                            result.output   (a plain Python string)
```

### What actually travels over the internet

Pydantic AI is not magic. When you call `agent.run(...)`, it sends one web request, roughly like this:

```
POST https://integrate.api.nvidia.com/v1/chat/completions
Authorization: Bearer <your NVIDIA_API key>
Body (JSON): { "model": "nvidia/nemotron-3.5-lightning-30b-a3b",
               "messages": [ {"role": "user", "content": "What is the capital of Sweden?"} ] }
```

Nvidia replies with JSON that contains the answer text. Pydantic AI unpacks that JSON and gives you `result.output`.

> **Data engineer view:** it is the same as calling any REST API with `requests.post(...)`, except the library builds the request and parses the response for you.
> This is why you can see all five boxes in the notebook: each box is just one piece of that web request.
> `base_url` = the host and path, `api_key` = the `Authorization` header, model name = a field in the JSON body.

---

## 3. The setup half: why each piece exists

You do not need to memorize these. You need to know **what breaks if the piece is missing**.

| Piece | What it is | Why it exists | If it was missing |
| --- | --- | --- | --- |
| GitHub repo + `git clone` | A folder that git tracks | Versioned history, and a way to share the course | No history, no sharing |
| `uv` | One tool for Python version, packages and virtual env | Replaces pip + venv + pyenv with one command | You juggle three tools |
| `.python-version` | One line: `3.13` | Everyone runs the same Python | "Works on my machine" bugs |
| `pyproject.toml` | The project's ID card. Holds the package list (`dependencies`). | Anyone can recreate your setup | Nobody knows what to install |
| `uv.lock` | The exact version of every package, including packages of packages | Same versions on every machine | A new release can break your code a month later |
| `.venv/` | A private folder of installed packages for this project | Project A's packages never clash with project B's | Packages mix up across projects |
| `.env` | A text file of secrets: `NVIDIA_API=...` | Keeps the key out of your code | The key ends up in git history |
| `.gitignore` (line 131 is `.env`) | A list of files git refuses to upload | Stops `.env` and `.venv` reaching GitHub | You publish your key |

### Commands

| Command | What it does | Think of it as |
| --- | --- | --- |
| `uv init --no-package --python 3.13` | Creates the starter files. `--no-package` = "scripts and notebooks, not a library". | `git init` for a Python project |
| `uv add <package>` | Installs the package **and** writes it into `pyproject.toml` | `pip install` + editing `requirements.txt` in one step |
| `uv sync` | Makes `.venv` match `pyproject.toml` / `uv.lock` | Run it after cloning someone's repo |
| `uv run <command>` | Runs a command inside the project's `.venv` | No need to "activate" anything |

### Why does `01/README.md` line 48 install so many packages?

```
uv add pandas pydantic-ai ipykernel duckdb fastapi matplotlib python-dotenv streamlit uvicorn
```

Lecture 01 only **needs** three:

| Package | Role in lecture 01 |
| --- | --- |
| `pydantic-ai` | The framework: `Agent`, `OpenAIChatModel`, `OpenAIProvider` |
| `python-dotenv` | Reads `.env` into environment variables (`load_dotenv`) |
| `ipykernel` | Lets VS Code run `.ipynb` cells with this project's Python |

The other six are installed now because **the whole course shares one environment** (the one `.venv` and one root `pyproject.toml`). Later lectures use them:

| Package | Used from lecture |
| --- | --- |
| `duckdb` | 04 (movie database) |
| `fastapi`, `uvicorn` | 04, 05 (web API and the server that runs it) |
| `streamlit` | 05 (chat web page) |
| `pandas`, `matplotlib` | data handling and charts |

---

## 4. The notebook, cell by cell

### The title cell (markdown)

Only thing to take away: "PydanticAI is model agnostic". It means the same code shape works with Nvidia, OpenAI, Google and others. Only the model object changes. You will see this in lecture 05, where the model is a short string instead.

### Cell [1] — import Agent

```python
from pydantic_ai import Agent
```

- **What:** makes the name `Agent` available.
- **Why:** Python only knows names you import. Nothing is contacted. No cost, no internet.
- **If missing:** `NameError: name 'Agent' is not defined`.

### Cell [2] — the main cell, built from the inside out

The cell is long, but it has only **six jobs**, in this order:

| Lines | Job | Why this order |
| --- | --- | --- |
| 1 to 9 | Imports | Python needs the names before it can use them |
| 13 | `load_dotenv()` | The key must be in memory **before** line 21 reads it |
| 19 to 22 | Build the Provider (address + key) | It is the innermost object, so it must exist first |
| 17 to 23 | Build the Model (name + provider) | It needs the provider |
| 26 | Build the Agent | It needs the model |
| 31 to 34 | Ask, print | It needs the agent |

**The rule behind the order:** an object that goes *inside* another must be created *first*. In the notebook the Provider is written inside the Model call, so Python builds it first, then the Model, then you wrap it in the Agent. Same idea as nested function calls: `f(g(h(x)))` runs `h` first.

The same thing written flat, which is easier to read:

```python
provider = OpenAIProvider(base_url="https://integrate.api.nvidia.com/v1",
                          api_key=os.environ["NVIDIA_API"])
model = OpenAIChatModel("nvidia/nemotron-3.5-lightning-30b-a3b", provider=provider)
agent = Agent(model)
```

Both versions do exactly the same thing.

#### Why `OpenAI...` classes for an Nvidia model?

OpenAI was first and popular, so its web request format became a **de facto standard** ("OpenAI-compatible"). Many companies copy it, including Nvidia. So Pydantic AI needs only one set of classes to talk to many servers. You change `base_url` and the model name, and the same code works.

> **Analogy:** many databases speak the Postgres protocol, so one Postgres client can connect to all of them. `OpenAIProvider` is the "Postgres client". Nvidia's server is a "Postgres-compatible" server.

#### Why `os.environ["NVIDIA_API"]` and not the key itself?

```
.env file (your laptop only)
   NVIDIA_API=nvapi-....
        │ load_dotenv()  copies each line into...
        ▼
environment variables (this notebook's memory)
        │ os.environ["NVIDIA_API"]  reads one by name
        ▼
api_key=...   (used in the Authorization header)
```

The key is never typed in the code, so the code can go to GitHub safely. `os.environ[...]` raises a `KeyError` if the name is missing, which is good: you find out immediately, not after a confusing 401 later.

#### Why `await`?

`agent.run` sends a request over the internet and the reply takes seconds. During those seconds Python has nothing to do. `await` says: "pause **this** task until the answer arrives". In a program that does many things at once (like a web server), Python can use that waiting time to serve other people.

| Where | How to call it |
| --- | --- |
| Notebook | `result = await agent.run(...)`. Jupyter already runs an event loop in the background, so a top-level `await` works. |
| Plain `.py` script | `agent.run_sync(...)`, or wrap with `asyncio.run(...)` |
| Inside a web app | `async def` function containing `await agent.run(...)`. See lecture 05 `chat_agent.py` line 59 and 78. |

#### What are `result` and `result.output`?

`result` is a wrapper object (`AgentRunResult`). It holds the answer **and** extras: token counts, the message history, timestamps. The answer is `result.output`.

> This wrapper is on purpose. In lecture 03 `result.output` stops being plain text and becomes a *validated Python object*. That is the "Pydantic" in Pydantic AI.

#### `timeout=60` (line 31 of cell [2])

The maximum time in seconds to wait for the reply. The first call to a model can be slow.

---

## 5. Cells [3] to [7]: what each experiment teaches

| Cell | What it does | The lesson |
| --- | --- | --- |
| [3] | Asks for a joke (`timeout = 120`), and shows `result` | The output is an `AgentRunResult(output=...)` wrapper. A longer `timeout` leaves more time for a reply. Each run gives a different joke. |
| [4] | `result.output` | Shows the difference between the wrapper and the text. |
| [5] | Builds `new_model` and calls `agent.run(..., model=new_model)` | **A model passed to `run` overrides the agent's model for that one call only.** The agent itself is not changed. |
| [6] | Under the heading "This model just HALLUCINATED", asks "how does Pydanticai differ from other AI frameworks?" | **The model does not know about this library.** See below. |
| [7] | Saves the answer to a file and fails with `UnicodeEncodeError` | Windows' default file encoding cannot write some characters (the arrow `→`). Fix: `open("file.md", "w", encoding="utf-8")`. |

### Cell [6] is the most important example in the notebook

The model said "Pydanticai" is not a widely recognized name, guessed it might mean Pydantic, and then compared that with PyTorch, TensorFlow and JAX. It did not recognize the framework you asked about. Why?

- An LLM learned from text collected up to some date. It may know little or nothing about newer or niche things.
- It still produces fluent, confident text. It does not reliably say "I don't know".
- This is called **hallucination** when the answer is made up, and it is one of the main reasons for the second half of the course.

How the course deals with it:

| Problem | Fix in the course |
| --- | --- |
| The model doesn't know my data or recent facts | **Tools** (lecture 06, the model calls a weather API) and **RAG** (retrieve documents first) |
| I can't tell when the model is wrong | **Evaluation**, **LLM judge**, **hallucination detection** |
| I can't see what the model did | **Tracing** with Logfire |

---

## 6. Where this reappears in later lectures

The three objects from cell [2] never go away. They only get wrapped, shortened, or given more options.

| Idea from 01 | Where it appears next | What changes |
| --- | --- | --- |
| Provider + Model + Agent written inline (cell [2]) | `02_llm_intro/llm_intro.ipynb` | Same code. The Agent gets a `system_prompt`. |
| The same three objects | `03_pydanticai_structured_output/model.py` lines 8 to 14, and `06_tool_use/model.py` | **Wrapped into a function** `nvidia_model("<name>")` so you do not copy 10 lines each time. |
| `Agent(model)` | `06_tool_use/agents.py` line 31 | The Agent gets `instructions`, `toolsets` and `deps_type`. |
| `Agent(model)` | `05_pydanticai_fastapi_chatbot/chat_agent.py` line 53 | The Agent gets a `system_prompt`. |
| Model object | `05_.../constants.py` | **Shortcut:** the model is a string like `"google:gemini-flash-lite-latest"`. Pydantic AI builds the provider for you and reads the key from the environment. Same idea, fewer lines. |
| `await agent.run(...)` | `05_.../chat_agent.py` lines 59 and 78 | Inside an `async def` that FastAPI calls for each chat message. Gets `message_history=` so the bot remembers. |
| `result.output` | `05_.../chat_agent.py` line 85 | Put into a `ChatResponse` to send back to the web page. |
| `result.output` (plain text) | `03_.../pydanticai_pydantic_model.ipynb`, and `04_pydantic_fastapi/src/data_models.py` | `output_type=list[EmployeeModel]` / `Movie` makes the output a **validated Pydantic object**. |
| `.env` + `load_dotenv()` | Every folder | One `.env` in the repo root works for all folders, because `load_dotenv()` searches up through parent folders (explained in `06_tool_use/model.py` line 34). |
| One `.venv`, one `pyproject.toml` at the root | Every folder | Each lecture folder uses the same environment. |
| Cell [6]: model doesn't know | `06_tool_use` and later RAG | Tools and retrieval give the model facts it does not have. |

### How the course grows from this one cell

```
01  ask a question                          Provider → Model → Agent → run
 │
02  control the answer                      + system_prompt, temperature, tokens, message history
 │
03  get structured answers                  + output_type = a Pydantic model (validated data)
 │
04  put it behind a web API                 + FastAPI + DuckDB; Movie is both the AI's output and the API's response
 │
05  build a chatbot                         Streamlit page → FastAPI → Agent (+ message_history)
 │
06  let the AI call your code               + tools (functions the model may request)
 │
07+ run it properly (from the root README) Logfire traces, LLM judge, LanceDB + RAG, Docker, Azure, CI/CD, MCP
```

---

## 7. Glossary (plain words)

| Term | Meaning |
| --- | --- |
| **LLM** | A program that predicts and writes text. You send text, it sends text back. |
| **Model** | One specific LLM, e.g. `nvidia/nemotron-3.5-lightning-30b-a3b`. |
| **Provider** | The company or server that hosts models and lets you call them, plus the login details. |
| **API** | A way for programs to talk to each other, here over the internet. |
| **API key** | A password string that identifies you to the provider. |
| **Agent** (Pydantic AI) | A Python object that wraps a model so you can call `.run(...)`. Later also holds instructions and tools. |
| **Prompt** | The text you send. |
| **`result.output`** | The model's answer, as a Python value. |
| **Environment variable** | A named value in the process's memory, e.g. `NVIDIA_API`. |
| **Virtual environment** (`.venv`) | A private folder of packages for one project. |
| **Dependency** | A package your project needs. |
| **`async` / `await`** | Python's way to wait for slow things (like the internet) without freezing everything else. |
| **Hallucination** | A fluent answer that is wrong or made up. |

---

## 8. Check yourself

Try to answer before opening each one.

<details><summary>1. Why are there three objects (Provider, Model, Agent) and not one?</summary>

Each answers a different question. Provider: *where is the server and who am I?* Model: *which brain?* Agent: *how do I talk to it, and later with what instructions and tools?* Splitting them lets you swap one without touching the others (see cell [5], where only the Model changes).
</details>

<details><summary>2. Why must <code>load_dotenv()</code> run before <code>os.environ["NVIDIA_API"]</code>?</summary>

`load_dotenv()` is what copies the key from `.env` into memory. Before it runs, the name does not exist and Python raises `KeyError`.
</details>

<details><summary>3. Why is it safe to commit the notebook but not <code>.env</code>?</summary>

The notebook only contains the **name** `NVIDIA_API`, never the key. `.env` contains the key itself, so `.gitignore` blocks it.
</details>

<details><summary>4. What does <code>await</code> do, and why does a plain <code>.py</code> file need something different?</summary>

It pauses until the reply arrives. A notebook already runs an event loop, so top-level `await` works. A plain script has none, so you use `agent.run_sync(...)` or `asyncio.run(...)`.
</details>

<details><summary>5. What is the difference between <code>result</code> and <code>result.output</code>?</summary>

`result` is a wrapper holding the answer plus usage and messages. `result.output` is the answer itself.
</details>

<details><summary>6. Why did the model get cell [6] wrong, and which part of the course addresses it?</summary>

It does not reliably know newer or niche topics and still sounds confident. Tools (06), RAG, and evaluation/hallucination detection address it.
</details>

<details><summary>7. In cell [5], what happens to the agent's own model after the call?</summary>

Nothing. `model=new_model` applies to that one call. The agent still uses its original model next time.
</details>

---

## 9. My questions

Add questions here as you read, then ask Claude to answer them in this file.

- [ ]
