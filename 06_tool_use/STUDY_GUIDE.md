# Study guide: 06 Tool use

Keep this open next to the code in VS Code. Open the file named in the table, then read the matching section here.
This guide explains the **why**. The docstrings and comments in the files already explain the **what**.

This lecture has five Python files, one small leftover file, and one notebook. References look like `tools.py` line 80, or notebook cell `[3]`.

| When you are reading... | Read this section |
| --- | --- |
| The big idea | [1. The 30-second version](#1-the-30-second-version) and [2. The pictures](#2-the-pictures-to-understand) |
| `model.py` | [4.1 model.py](#41-modelpy--which-model) |
| `tools.py` | [4.2 tools.py](#42-toolspy--the-functions-the-ai-may-call) |
| `agents.py` | [4.3 agents.py](#43-agentspy--putting-it-together) |
| `main.py` | [4.4 main.py](#44-mainpy--the-script-you-run) |
| `deps.py` | [4.5 deps.py](#45-depspy--an-unused-copy) |
| `tools_basics.ipynb` | [5. The notebook](#5-the-notebook-tools_basicsipynb) |
| Any later lecture | [9. Where this connects](#9-where-this-connects) |

---

## 1. The 30-second version

An LLM only produces **text**. It cannot look up today's weather, query your database or call an API. If you ask, it may make something up. (You saw this in lecture 02 with the foggy Göteborg question, and in lecture 05 with "what is the weather in Stockholm?".)

A **tool** fixes that. You write an ordinary Python function and tell the model "you may ask me to run this". The model never runs anything. It **asks**, your code runs the function, and the result goes back to the model, which then writes the final answer using the real data.

> **The model is the decision-maker. Your code is the worker.** The model decides *which* function to call and with *which arguments*. Your function does the real work.

> **Data engineer view:** tools are how an LLM reads from the outside world: APIs, databases, files. The LLM is an orchestrator that chooses which step to run, and your functions are the steps.

---

## 2. The pictures to understand

### Picture A: how the files connect

```
 model.py      nvidia_model("...")        which AI model
 tools.py      get_weather, geocode,      the functions the AI may call, and the extra data they can read
               WeatherDeps
      │             │
      ▼             ▼
 agents.py     weather_agent = model + instructions + tools       (builds the agent, runs nothing)
      │
      ▼
 main.py       asks the agent two questions and prints the answers     ◄── you run this one
      │
      ▼
 Nvidia model  ◄──►  Open-Meteo weather API (free, no key)
```

`deps.py` is not part of this picture. Nothing imports it (see 4.5).

### Picture B: the tool loop

I ran your real agent, tools and `main.py` flow with a **fake model** and fake web replies, and printed every message. For "What is the weather in Skövde?":

```
You ──► Agent ──► model
                   │ call 1: sees the question + the menu of tools
                   │ answers NOT with text, but with a request:  geocode(city="Skövde")
                   ▼
        your function geocode() runs ──► {'latitude': 58.39, 'longitude': 13.85}
                   │ the result goes back to the model
                   ▼
                  model
                   │ call 2: now asks for:  get_weather(lat=58.39, lon=13.85)
                   ▼
        your function get_weather() runs ──► "Current temperature in Skövde is 8.1°C"
                   │ the result goes back to the model
                   ▼
                  model
                   │ call 3: writes the final answer in words
                   ▼
              "It is 8.1 degrees in Skövde."
```

The messages in `result.all_messages()` follow the same order:

```
ModelRequest   UserPromptPart    "What is the weather in Skövde?"
ModelResponse  ToolCallPart      geocode  {'city': 'Skövde'}
ModelRequest   ToolReturnPart    {'latitude': 58.39, 'longitude': 13.85}
ModelResponse  ToolCallPart      get_weather  {'lat': 58.39, 'lon': 13.85}
ModelRequest   ToolReturnPart    Current temperature in Skövde is 8.1°C
ModelResponse  TextPart          It is 8.1 degrees in Skövde.
```

Look at the new part types: `ToolCallPart` (the model asks) and `ToolReturnPart` (your function answers). The loop can repeat as many times as the model needs.

**What this costs.** That one question took **3 model calls** and 2 web calls. Every call sends the growing message list again (lecture 02 and 05). Tools make the bot capable, and also slower and more expensive.

### Picture C: what the model is shown about each tool

The model never sees your code. It sees a description. I printed exactly what your two tools look like to the model:

| Tool | Description shown | Parameters shown |
| --- | --- | --- |
| `get_weather` | `get current weather for latitude and longitude` | `lat` (number), `lon` (number), both required |
| `geocode` | **none** | `city` (string), required |

Two things to notice:

1. The `ctx: RunContext[WeatherDeps]` parameter of `get_weather` is **not shown**. It is hidden from the model. The model only chooses `lat` and `lon`.
2. `geocode` has **no docstring**, so it reaches the model with only a name and one parameter. It works, because the name is clear. A docstring would help.

The description comes from three places: the **function name**, the **parameter names and types**, and the **docstring**. That is why those matter. It is the same idea as `Field(description=...)` in lecture 03.

---

## 3. Ideas worth understanding

### 3.1 Why two tools for one question?

The weather API wants coordinates (latitude, longitude). People say city names. So there are two tools, and the model **chains** them: `geocode` first, then `get_weather` with the result. Nobody wrote code that says "call geocode first". The model worked that out from the descriptions.

### 3.2 Deps: data for the tools that the model does not see

Some information your **code** knows and the model should not have to guess: the logged-in user, a database connection, a setting. You pass it when you run the agent, and tools read it through `ctx.deps`.

```python
@dataclass
class WeatherDeps:
    city: str                                   # tools.py lines 51 to 65

weather_agent.run(prompt, deps=WeatherDeps(city="Skövde"))      # main.py line 66
...
return f"Current temperature in {ctx.deps.city} is {temperature}°C"     # tools.py line 96
```

| Part | Meaning |
| --- | --- |
| `@dataclass` | A simple container with named fields. Like a typed row. |
| `deps_type=WeatherDeps` (agents.py line 57) | Tells Pydantic AI and your editor what type `ctx.deps` has. It gives autocomplete. |
| `deps=WeatherDeps(...)` at run time | The actual object |
| `ctx: RunContext[WeatherDeps]` | The hidden first parameter that gives a tool access to `ctx.deps` |

### 3.3 `instructions` as a guardrail

`agents.py` lines 41 to 46 tell the agent to answer short, to use the tools, and to **decline non-weather questions**. So "Tell me a programming joke" in `main.py` is refused. That is a guardrail written as a sentence.

It is a request to the model, not a lock. A determined user might talk the model into answering anyway. Real guardrails need checks in code too. (Evaluation and hallucination detection come later in the course.)

### 3.4 `instructions` vs `system_prompt`

Lecture 05 used `system_prompt`, here it is `instructions`. For a single run they act the same. They differ when you pass a `message_history` (lecture 02, section 4): a `system_prompt` is stored in the history, while `instructions` come from the current agent on each run. This agent has no history, so it does not matter here.

---

## 4. The files

### 4.1 `model.py` — which model

| Lines | Code | Meaning |
| --- | --- | --- |
| 29 to 32 | imports | Same as lecture 01 |
| 37 | `load_dotenv()` | Loads `NVIDIA_API` from `.env`. It searches this folder, then the parent folders. |
| 40 to 61 | `def nvidia_model(model_name: str) -> OpenAIChatModel:` | Lecture 01's Provider + Model, wrapped in a function |
| 57 | `base_url="https://integrate.api.nvidia.com/v1"` | Nvidia's address |
| 59 | `api_key=os.environ["NVIDIA_API"]` | The key from the environment |

- This is the same helper as `03_pydanticai_structured_output/model.py`. The docstring explains why each folder needs its own copy: Python imports files from the folder you run from.
- It is lecture 01 cell `[2]` as a function, so you write `nvidia_model("<name>")` and get a model back.
- Lecture 05 used a model **string** (`"google:..."`). Here you are back on Nvidia.

### 4.2 `tools.py` — the functions the AI may call

#### `WeatherDeps` (lines 51 to 65)

See section 3.2.

#### `get_weather` (lines 68 to 96)

```python
def get_weather(ctx: RunContext[WeatherDeps], lat: float, lon: float) -> str:
    """get current weather for latitude and longitude"""
```

| Lines | What it does |
| --- | --- |
| 68 | The signature. `ctx` is hidden from the model. `lat` and `lon` are what it chooses. The `float` hints become the parameter types. |
| 69 | The docstring. **This is what the model reads** to decide when to use the tool. |
| 80 to 84 | `httpx.get(...)` calls the Open-Meteo forecast API. `params` becomes the query string. `timeout=30` stops it hanging. |
| 87 | `response.raise_for_status()` turns an HTTP error (404, 500) into a Python exception instead of continuing with bad data |
| 91 to 92 | Pull `temperature_2m` out of the JSON |
| 96 | Return a string. **Whatever a tool returns is sent back to the model as text.** |

Notice that the city name in the reply comes from `ctx.deps.city`, **not** from the coordinates or the question. See the gotchas.

#### `geocode` (lines 99 to 119)

| Lines | What it does |
| --- | --- |
| 99 | `def geocode(city: str) -> dict:`, no docstring |
| 107 to 110 | Calls Open-Meteo's geocoding API. `count=1` asks for the best match only. |
| 111 | `raise_for_status()` |
| 116 | `place = response.json().get("results")[0]` takes the first match |
| 119 | Returns `{"latitude": ..., "longitude": ...}`. A dict is converted to text for the model. |

If the city does not exist, `"results"` is missing, `.get("results")` is `None`, and `[0]` fails. The file's comment says so (lines 114 to 115).

#### The leftover line (line 128)

```python
print(geocode("gothenburg"))
```

This line is **not** commented out (line 127, `get_weather`, is). It runs **every time any file imports `tools.py`**, so it makes a real web call and prints a dict before anything else. I confirmed it: just importing `tools` made one request to the geocoding API (I intercepted it with a fake). The file's own comment warns about it. Delete or comment out this line when you are done testing.

### 4.3 `agents.py` — putting it together

The whole file builds one object.

| Lines | Code | Meaning |
| --- | --- | --- |
| 24 to 29 | imports | `Agent`, `nvidia_model`, the tools, `FunctionToolset` |
| 31 | `weather_agent = Agent(` | |
| 33 | `model=nvidia_model("nvidia/nemotron-3.5-super-vl-120b-a12b")` | A bigger Nvidia model than lecture 01's `lightning-30b` (see the numbers in the names) |
| 41 to 46 | `instructions=(...)` | The agent's job description (section 3.3) |
| 52 | `toolsets=[FunctionToolset([get_weather, geocode])]` | The menu of tools |
| 57 | `deps_type=WeatherDeps` | The type of the extra data |

**What an agent is now** (the docstring puts it well):

```
Agent = MODEL (model.py) + INSTRUCTIONS (the sentence) + TOOLS (tools.py)
```

This file only **builds** the agent, like configuring a worker. It runs nothing. `main.py` is what asks it questions.

**Two ways to register tools:**

| Way | Where | When it fits |
| --- | --- | --- |
| `toolsets=[FunctionToolset([...])]` | `agents.py` line 52 | Tools written in another file, or **shared between several agents** |
| `@agent.tool` / `@agent.tool_plain` | The notebook, cell `[3]` | The tool belongs to one agent and is defined right next to it |

Pydantic AI works out from the signature whether a function wants the `ctx` parameter. I confirmed that `get_weather` (with `ctx`) and `geocode` (without) both work in one toolset.

### 4.4 `main.py` — the script you run

| Lines | Code | Meaning |
| --- | --- | --- |
| 36 to 38 | imports | The agent, `asyncio`, `WeatherDeps` |
| 41 to 55 | `async def main(prompt, **kwargs)` | Asks the agent one question and prints `result.output` |
| 53 | `result = await weather_agent.run(prompt, **kwargs)` | `**kwargs` passes `deps=...` straight through |
| 60 | `if __name__ == "__main__":` | Runs only when you start this file directly |
| 66 | `asyncio.run(main("What is the weather in Skövde?", deps=WeatherDeps(city="Skövde")))` | Question 1: a weather question |
| 69 | `asyncio.run(main("Tell me a programming joke", deps=WeatherDeps(city="London")))` | Question 2: off topic, to test the guardrail |

- **`asyncio.run(...)`** starts an async function from normal code. This is the "plain `.py` file" case from lecture 01, where there is no notebook event loop.
- **Question 2 still needs `deps`**, because the agent was built with `deps_type=WeatherDeps`. The city "London" there is just filler.
- **What you see:** first the leftover printed dict from `tools.py`, then the temperature for Skövde, then a polite refusal of the joke. (Run it with `uv run main.py` from inside `06_tool_use/`.)

### 4.5 `deps.py` — an unused copy

```python
@dataclass
class WeatherDeps:
    city: str
```

Five lines, and **nothing imports it**. `agents.py` and `main.py` both import `WeatherDeps` from `tools.py`. I checked: `deps.WeatherDeps` and `tools.WeatherDeps` are two **different** classes with the same shape. Harmless, but it can confuse you: if you edit this file nothing changes. It looks like an earlier version from before the class moved into `tools.py`.

---

## 5. The notebook: `tools_basics.ipynb`

A smaller, self-contained version of the same idea: a **dice game**, with the tools defined by decorators.

Cell numbers follow the same rule as the other guides: `[3]` is the 3rd **code** cell from the top, the one that shows `[3]` after Restart, then Run All.

| Cell | How it starts | What it shows | Saved badge |
| --- | --- | --- | --- |
| title | markdown | `# PydanticAI tools` | none |
| **[1]** | `from pydantic_ai import Agent` | Builds `dice_agent` with `nvidia_model`, `instructions` and `ModelSettings(thinking="minimal")` | [3] |
| **[2]** | `result = await dice_agent.run("What is the capital of Sweden?")` | **The guardrail.** It declines in a nerdy joke and steers back to the game. No tools yet. | [4] |
| **[3]** | `from pydantic_ai import RunContext` | Registers two tools, then `await dice_agent.run("i guess 16", deps="Adam")` | none |

The saved badges are out of order. After **Restart, then Run All** they match the first column.

### Cell `[1]`

- `instructions` is a game description: roll the die, compare with the guess, use the player's name, answer in a nerdy jokey way, decline anything off topic.
- `model_settings=ModelSettings(thinking="minimal")` asks the model to think as little as possible. Lecture 02 showed that a reasoning model can spend ~1,000 hidden tokens on a tiny question, so this saves time and money.

### Cell `[3]`: the two decorators

```python
@dice_agent.tool_plain
def roll_dice() -> str:
    """roll 20 sided die and return result"""
    return str(random.randint(1, 20))

@dice_agent.tool
def get_player_name(ctx: RunContext[str]) -> str:
    """Get players name"""
    return ctx.deps
```

| Decorator | The function... | Use it when |
| --- | --- | --- |
| `@agent.tool_plain` | does **not** take `ctx` | The tool needs nothing from your code |
| `@agent.tool` | takes `ctx: RunContext[...]` as its first parameter | The tool needs `ctx.deps` (or other run information) |

- `roll_dice` rolls **in Python**, using `random`. The model cannot roll a die. It would invent a number. That is exactly why this needs a tool.
- `get_player_name` shows that **deps can be any type**. Here it is a plain string, `RunContext[str]`, and `deps="Adam"` is passed at run time. In `tools.py` the deps were a dataclass.
- The docstrings (`"roll 20 sided die..."`, `"Get players name"`) are what the model reads.
- The saved result is a win: the guess was 16 and the d20 rolled 16. That is a 1 in 20 chance, so your run was lucky. A re-run will usually say the player lost.

**One mismatch to be aware of.** The tool rolls a **20-sided** die, but the `instructions` never say how many sides there are. In cell `[2]` the model improvised "a number between 1 and 6". The game rules in `instructions` and the tool should agree.

**Note that `dice_agent` is changed after it is created.** Decorating adds tools to the existing agent. So cell `[2]` ran on an agent without tools, and cell `[3]` ran on the same agent with tools. Re-running from the top gives the same order.

---

## 6. Running it

From the docstring in `main.py`. In a terminal **inside `06_tool_use/`**:

```bash
cd 06_tool_use
uv run main.py
```

Needs:

| Need | Why |
| --- | --- |
| `NVIDIA_API=...` in the repo's `.env` | `model.py` reads it |
| An internet connection | The model and Open-Meteo are both on the internet |
| No weather API key | Open-Meteo is free without one |

Run it from inside the folder, because `main.py` does `from agents import weather_agent` and Python finds `agents.py` in the current folder (the same reason as lectures 04 and 05).

The notebook needs the `.venv` kernel and the same `.env`.

---

## 7. What I tested

I ran your real `tools.py`, `agents.py` and `model.py` on a **copy**, with a fake model and fake web replies, so there were no real requests and no quota used.

| Test | Result |
| --- | --- |
| Import `tools.py` | One call to the geocoding API (faked in my test) and one printed dict, both from line 128 |
| What the model is shown | `get_weather`: described, params `lat`, `lon`. `geocode`: **no description**, param `city`. `ctx` hidden. |
| The tool loop for "weather in Skövde" | 3 model calls, 2 web calls, messages in the order shown in picture B |
| Ask about "Paris" with `deps=WeatherDeps(city="London")` | The tool returned "Current temperature in **London** is ..." |
| Run the agent with no `deps` at all | `AttributeError: 'NoneType' object has no attribute 'city'` |
| `geocode` for a city the API does not know | `TypeError: 'NoneType' object is not subscriptable`. The whole run fails. |
| `deps.py` vs `tools.py` | Two different `WeatherDeps` classes |

I did **not** test the real Nvidia model, so I cannot say how well it follows the "decline non-weather questions" instruction. Your `main.py` is meant to show that.

---

## 8. Gotchas

| Gotcha | Why | What to do |
| --- | --- | --- |
| **`print(geocode("gothenburg"))` runs on every import** (`tools.py` line 128) | It is not commented out | Delete it, or comment it out |
| **The city label can be wrong** | The reply uses `ctx.deps.city`, not the question. Asking about Paris with `deps=WeatherDeps(city="London")` returns "London". | Keep the question and the deps in agreement, or have the tool use the coordinates to find the name |
| **Unknown city crashes the run** | `geocode` indexes `[0]` on a missing result | Check for `None` first. A tool can raise `ModelRetry("...")` to tell the model to try again with different arguments. I tested it: the message went back to the model, and it called the tool again with a different city. |
| **Forgot `deps=`** | `ctx.deps` is `None` | Always pass `deps=` when the agent has `deps_type` |
| **`geocode` has no docstring** | The model sees only the name | Add `"""get latitude and longitude for a city name"""` |
| **Tool calls are extra model calls** | Each step is another request with the whole history | Keep tools few and clear. Watch cost and speed. |
| **The guardrail is only a sentence** | `instructions` is a request to the model | Do not rely on it for anything important |
| **`temperature_2m` is "current"** | The API returns the latest value for that place | It is not a forecast |
| **Weather API down or slow** | `get_weather` has `timeout=30`, `geocode` has no timeout | Add `timeout=` to `geocode` too (httpx waits only 5 seconds by default) |
| **Wrong folder** | Imports are by file name | `cd 06_tool_use` first |
| **`deps.py` is unused** | An older copy | Safe to ignore, or delete |
| **Cell order in the notebook** | Cell `[3]` adds tools to the same agent | Run top to bottom |
| **The dice rules disagree** | The tool is a d20, the instructions do not say | Put the sides in `instructions` |
| **The model hallucinates** | Even with tools it can ignore them and guess | Tell it to use the tools (as the instructions do), and check the messages for `ToolCallPart` |

---

## 9. Where this connects

| In 06 | Comes from | Goes to |
| --- | --- | --- |
| The model cannot know the weather | Lecture 02 (foggy Göteborg), lecture 05 notebook cell `[7]` | Solved here |
| `ToolCallPart` / `ToolReturnPart` | Lecture 02, picture B (message parts) | The tool loop is more entries in the same message list |
| Tool description from name, types and docstring | Lecture 03 (`Field(description=...)`, JSON schema) | |
| `instructions=` | Lecture 03 | |
| `nvidia_model()` | Lecture 01 cell `[2]` and `03/model.py` | |
| `asyncio.run` | Lecture 01 (`await`, `run_sync`) | |
| `deps` and `RunContext` | New | Anything an agent needs from your code, like a database connection |
| `ModelSettings(thinking="minimal")` | Lecture 02 (tokens, reasoning, settings) | |
| The tool loop makes several model calls | Lecture 05 picture C (history grows) | Tracing with Logfire later shows each call |
| Tools read from the outside world | | The root `README.md` lists **RAG**, **LanceDB** and **MCP** later. A RAG retriever is a tool that reads your documents. I have not read that material yet, so treat this as the likely direction. |

```
01   ask a question
02   control it and look inside it
03   get structured answers
04   put it behind a web address and a database
05   add memory and a web page
06   let the model call YOUR functions to get real data      ◄── you are here
07+  see what it did (tracing), judge it (evaluation), feed it documents (RAG), deploy it
```

---

## 10. Glossary (new words in 06)

| Term | Meaning |
| --- | --- |
| **Tool** | A Python function the model may ask your code to run. |
| **Tool call** | The model's request: "run this function with these arguments". |
| **Tool return** | The function's result, sent back to the model as text. |
| **Tool loop** | Ask, call, return, repeat, until the model writes the final answer. |
| **Orchestrator** | The part that decides which step to run. Here, the model. |
| **Deps** (dependencies) | Extra data your code gives the tools, which the model does not see. |
| **`RunContext`** | The hidden first parameter that gives a tool access to `ctx.deps`. |
| **`deps_type`** | Declares the type of the deps, for checking and autocomplete. |
| **Dataclass** | A simple container class with named, typed fields. |
| **Toolset** | A named bundle of tools that can be shared between agents. |
| **`tool` vs `tool_plain`** | Decorators for tools with and without `ctx`. |
| **Guardrail** | A rule that keeps the agent on topic. Here, a sentence in `instructions`. |
| **Geocoding** | Turning a place name into latitude and longitude. |
| **`ModelRetry`** | An exception a tool can raise to make the model try again. |

---

## 11. Check yourself

Try to answer before opening each one.

<details><summary>1. Who actually runs <code>get_weather</code>: the model or your code?</summary>

Your code. The model only returns a request ("call `get_weather` with lat and lon"). Pydantic AI runs your function and sends the return value back.
</details>

<details><summary>2. How does the model know what a tool does?</summary>

From a description built from the function name, the parameter names and types, and the docstring. It never sees the function body.
</details>

<details><summary>3. Why are there two tools for one weather question?</summary>

The weather API needs coordinates, but users give city names. `geocode` turns a name into coordinates, then `get_weather` uses them. The model chains them itself.
</details>

<details><summary>4. How many model calls did "weather in Skövde" take, and why?</summary>

Three in my test: one that requested `geocode`, one that requested `get_weather`, and one that wrote the final answer.
</details>

<details><summary>5. What are deps, and why not just put the city in the prompt?</summary>

Deps are data your code hands to the tools, hidden from the model. Information your code knows (a user, a connection, a setting) should not depend on the model guessing it correctly.
</details>

<details><summary>6. Why is the <code>ctx</code> parameter missing from what the model sees?</summary>

Pydantic AI fills it in and hides it. The model only chooses the real parameters, `lat` and `lon`.
</details>

<details><summary>7. What is the difference between <code>@agent.tool</code> and <code>@agent.tool_plain</code>?</summary>

`tool` functions take `ctx: RunContext[...]` first and can use `ctx.deps`. `tool_plain` functions take no context.
</details>

<details><summary>8. Why must <code>main.py</code> pass <code>deps</code> even for the joke question?</summary>

The agent was built with `deps_type=WeatherDeps`, and the tools read `ctx.deps`. Without `deps`, a tool that uses `ctx.deps.city` raises an `AttributeError`. For the joke question no tool should run, but passing deps keeps the call consistent.
</details>

<details><summary>9. What happens if you ask for a city that does not exist?</summary>

`geocode` finds no results, tries `[0]` on `None`, and raises a `TypeError`. The whole run fails, because nothing catches it.
</details>

<details><summary>10. Why is the "decline non-weather questions" rule not a real guardrail?</summary>

It is a sentence the model is asked to follow. Nothing in your code enforces it.
</details>

---

## 12. My questions

Add questions here as you read, then ask Claude to answer them in this file.

- [ ]
