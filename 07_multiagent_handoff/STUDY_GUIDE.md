# Study guide: 07 Multi-agent handoff

| When you are reading... | Read this section |
| --- | --- |
| The big idea | [1. The 30-second version](#1-the-30-second-version) and [2. The pictures](#2-the-pictures-to-understand) |
| `model.py` | [4.1 model.py](#41-modelpy--which-model) |
| `dependencies.py` | [4.2 dependencies.py](#42-dependenciespy--who-we-are-coaching) |
| `agents.py` | [4.3 agents.py](#43-agentspy--three-agents-and-the-handoff) |
| `main.py` | [4.4 main.py](#44-mainpy--the-script-you-run) |
| `multiagent_handoff.ipynb` | [5. The notebook](#5-the-notebook-multiagent_handoffipynb) |
| Things that can bite you | [6. Gotchas](#6-gotchas-and-things-to-improve) |

---

## 1. The 30-second version

In lecture 06 one agent used **functions** as tools. Here a tool is **another agent**.

There are three agents:

| Agent | Job | Talks to |
| --- | --- | --- |
| `coach_agent` | The manager. Receives the question, delegates, combines the answers, saves a report. | The user (via `main.py`) |
| `study_agent` | Specialist in study plans and learning techniques. | Only the coach |
| `career_agent` | Specialist in jobs, resumes and career paths. | Only the coach |

The coach has three tools. Two of them just call `.run()` on a specialist, and one writes a file. That is all a "handoff" is: **a tool whose body calls another agent and returns its answer as a string.**

> **Why split into agents?** Each agent has a short, focused prompt and is an "expert" in one area (separation of concerns). The notebook warns that for simple systems one agent is often better, so you need to *evaluate* whether splitting is worth the extra cost.

> **Data engineer view:** think of the coach as an orchestrator (like an Airflow DAG) and the specialists as tasks. The difference is that the *model* decides the order at run time, guided by the numbered steps in its instructions.

---

## 2. The pictures to understand

### Picture A: how the files connect

```
 model.py          nvidia_model("...")      which AI model (one connection, shared)
 dependencies.py   ClientDeps               the client profile (name, goal, ...)
        │                 │
        ▼                 ▼
 agents.py   study_agent ─┐
             career_agent ─┼─ all built from the same model + deps_type
             coach_agent ──┘   + 3 tools: ask_study_agent, ask_career_agent, export_report
        │
        ▼
 main.py     creates ClientDeps, runs coach_agent, prints the answer     ◄── you run this one
        │
        ▼
 Nvidia model (the API)       exports/<name>_<time>.md  (written by export_report)
```

### Picture B: the handoff flow

I ran your real `agents.py` with a **fake model** (no API calls) that follows the coach's steps, and printed every message:

```
You ──► coach_agent
          │ call 1: model answers with a request:  ask_study_agent(question=...)
          ▼
        ask_study_agent() runs ──► study_agent.run(question, deps, usage)
                                     └─ its own model call ──► "study answer"
          │ result goes back to the coach as text
          │ call 2: ask_career_agent(question=...)
          ▼
        ask_career_agent() runs ──► career_agent.run(...) ──► "career answer"
          │ call 3: export_report(text=...)
          ▼
        export_report() writes exports/bobby_20261109_084045.md ──► returns None
          │ call 4: writes the final reply in words
          ▼
        "FINAL"  ──► main.py prints it
```

The coach's message list (`result.all_messages()`):

```
ModelRequest   UserPromptPart   "q"
ModelResponse  ToolCallPart     {'question': 'How to learn Python?'}      ← ask_study_agent
ModelRequest   ToolReturnPart   specialist answer
ModelResponse  ToolCallPart     {'question': 'How to become DE?'}         ← ask_career_agent
ModelRequest   ToolReturnPart   specialist answer
ModelResponse  ToolCallPart     {'text': 'FINAL'}                         ← export_report
ModelRequest   ToolReturnPart   None
ModelResponse  TextPart         FINAL
```

Notice what is **not** in the coach's list: the specialists' own conversations. The coach only sees what each tool *returns*. The specialist runs are separate, short conversations.

**What this costs.** In that fake run the shared usage counter said `requests=6, tool_calls=3`: 4 calls for the coach and 1 for each specialist. A **real** run (Nvidia model, after the encoding fix) said `requests=5, tool_calls=3`: the real coach asked for both specialists in one response, so it needed only 3 calls itself. Delegation gives you experts, and it also makes things slower and more expensive.

### Picture C: what the coach model is shown about its tools

As in lecture 06, the model never sees your code. It sees the **function name**, the **parameters** and the **docstring**:

| Tool | Docstring the model reads | Parameter the model fills in |
| --- | --- | --- |
| `ask_study_agent` | Ask the study specialist for advice on learning and studying. | `question` (string) |
| `ask_career_agent` | Ask the career specialist for advice on what to choose for a career. | `question` (string) |
| `export_report` | Export the final text to a markdown file in the `exports/` folder. | `text` (string) |

The `ctx` parameter is hidden from the model. The tool names also appear **inside the coach's instructions** (`Call \`ask_study_agent\``), so the names in the prompt and the function names must match exactly.

---

## 3. Ideas worth understanding

Four ideas, in the order they happen when you run `main.py`. Keep the code open next to this.

**The office analogy used below:**

| In the office | In the code |
| --- | --- |
| The manager | `coach_agent` |
| Two experts, one for studying, one for careers | `study_agent`, `career_agent` |
| The client's file card (name, goal, hours...) | the `ClientDeps` object, called **deps** |
| The manager's "phone the expert" button | a **tool**: `ask_study_agent`, `ask_career_agent` |
| The manager's "save the report" button | the tool `export_report` |
| The manager's to-do list on the wall | the numbered steps in `coach_agent`'s `instructions` |

### 3.1 Agent as a tool: "the manager phones an expert"

The question this section answers: **how can one AI use another AI?** The answer is a normal function in the middle.

#### Step 1: the model never runs anything

The coach model can only write text. When it "calls a tool", it writes a request, roughly:

```
please run ask_study_agent with question="Give a study plan for Python"
```

PydanticAI sees that request and runs **your Python function** with those arguments. Whatever the function returns goes back to the coach as text. This is the same as lecture 06.

#### Step 2: a tool is input text in, output text out

Compare the two kinds of tool with the extra plumbing removed:

```python
# lecture 06 tool: inside is a web call
def get_weather(city: str) -> str:
    return requests.get(...).text

# lecture 07 tool: inside is an AI call
def ask_study_agent(question: str) -> str:
    return study_agent.run(question).output
```

Both take a string and return a string. **The coach cannot tell the difference.** The only change is what happens inside: one calls a weather website, the other calls a second AI. That is the whole idea of "agent as a tool". There is no special "handoff" feature.

#### Step 3: who is active, in order

```
User ──► COACH (AI #1) thinks: "I need study advice"
              │ writes: run ask_study_agent(question="...")
              ▼
         your Python function ask_study_agent()     ← plain code on your computer
              │ calls study_agent.run(question)
              ▼
         STUDY AGENT (AI #2)    ← a separate AI call with its own instructions
              │ writes its answer
              ▼
         the function returns that text
              ▼
         COACH reads it as the tool result and continues
```

There are **two separate AI calls**. The Python function in the middle connects them.

#### Step 4: the real code

Now the real version. It is the two-line function from step 2 plus three extras:

```python
@coach_agent.tool
async def ask_study_agent(ctx: RunContext[ClientDeps], question: str) -> str:
    result = await study_agent.run(question, deps=ctx.deps, usage=ctx.usage)
    return result.output
```

| Extra | Why it is there |
| --- | --- |
| `ctx` | Gives the function access to `ctx.deps` (the client card) and `ctx.usage` |
| `deps=ctx.deps` | "Here is the client's card too." Without it the study agent would not know the client's name. |
| `usage=ctx.usage` | "Count your tokens on the same bill as mine." Without it you would not see the real total. |
| `async` / `await` | The study agent call waits on the internet, so it is written the async way |

On a first read you can ignore all four and see the two-line function.

#### Step 4b: that one line, word by word

```python
result = await study_agent.run(question, deps=ctx.deps, usage=ctx.usage)
```

Read it from the right side to the left side, one piece at a time.

**`study_agent.run(...)`: "start the study agent"**

`.run()` is the same method `main.py` uses on the coach (`coach_agent.run(prompt, deps=client)`). It starts a full agent run: build the prompt from the agent's instructions, call the model, run any tools, and return the final answer. Here it is called from *inside* a tool, so a second agent runs inside the first one's run.

```
main.py ──► coach_agent.run(...)
               └─ inside, a tool runs ──► study_agent.run(...)     ← the line you asked about
```

**`question`: the first argument, "what to ask"**

Positionally this is the user prompt of the study agent, the same slot as `"I'm learning Python..."` in `main.py`. The coach model wrote this text when it called the tool.

**`deps=ctx.deps`: "pass the client card along"**

Break it in two:

| Part | Meaning |
| --- | --- |
| `ctx.deps` (right side) | The client card the **coach** received from `main.py` (`ClientDeps(name="Bobby", ...)`) |
| `deps=` (left side) | The slot on `.run()` where the **study agent** wants its own card |

So the line says: "study agent, use the same card that I (the coach) have." Nothing is copied or changed. The same object is handed on.

This is not optional. I tested it: running `study_agent.run("q")` without `deps` crashes with

```
AttributeError: 'NoneType' object has no attribute 'name'
```

because `study_name()` does `ctx.deps.name`, and with no `deps` passed, `ctx.deps` is `None`.

**`usage=ctx.usage`: "add your counting to mine"**

Every agent run counts its tokens and model requests in a usage counter. Without this argument, the study agent starts a **new** counter, and the coach's counter never knows the study agent's calls happened.

| | Without `usage=` | With `usage=ctx.usage` |
| --- | --- | --- |
| Counters | one per agent, separate | one shared counter |
| Total of the whole run | You must add them up yourself | `result.usage` of the coach already includes everything |
| Usage limits | A limit on the coach does not cover the experts | The limit covers the whole run |

Unlike `deps`, leaving it out does not crash. The code still works, you just lose the combined total. In a real run the shared counter showed `requests=5, tool_calls=3`.

**`await`: "wait here until it finishes"**

`study_agent.run(...)` sends a request over the internet and the answer takes seconds. `await` means "pause this function until the answer arrives, and let Python do other work while waiting". It is allowed only inside an `async def`, which is why the tool is written `async def ask_study_agent(...)`. Without `await`, you would get a "coroutine" object (a promise of a result) instead of the answer.

**`result = `: "keep what came back"**

`.run()` does not return a plain string. It returns an **`AgentRunResult`**, a small object holding several things:

| Attribute | What it is |
| --- | --- |
| `result.output` | The final answer text. This is what the next line returns. |
| `result.usage` | Tokens and requests used by this run |
| `result.all_messages()` | The study agent's whole mini-conversation |

That is why the next line is `return result.output`, to pull out just the text the coach needs.

**The whole line in plain English:**

> "Study agent, here is a question. Use the same client card I have. Count your tokens together with mine. I will wait until you finish, and I will keep your full result."

#### Step 5: walk through one real run

The user asks: *"I'm learning Python and want to become a data engineer. What should I do?"*

1. The coach reads its steps and decides to use `ask_study_agent`. It **writes the argument itself**, for example `question="Give a study plan for learning Python for data engineering"`.
2. Python runs `ask_study_agent(question="Give a study plan...")`.
3. Inside, `study_agent.run(...)` starts a **brand new mini-conversation** with the study expert.
4. The expert answers, for example "Bobby, spend 16 hours a week on...".
5. `return result.output` sends that text back to the coach as the **tool result**.
6. The coach reads it and moves on to the next step.

> **If you remember one thing:** the coach talks to an expert *through a function*, and the function returns a string.

### 3.2 Deps: "one client card that every agent can read"

**The problem.** Three agents all need the client's name. You could type "Bobby" into three prompts by hand, but then the code is not reusable for the next client.

**The solution.** Make one object, `ClientDeps(name="Bobby", ...)`, in `main.py` and give it to the coach once:

```python
coach_agent.run(prompt, deps=client)          # main.py: hand over the card
```

Inside the coach's tools the card is available as `ctx.deps`. The tools pass it on to the experts (`deps=ctx.deps` from 3.1). Everyone reads the same card:

```
main.py      client = ClientDeps(name="Bobby", ...)
   │  deps=client
   ▼
coach_agent ── ctx.deps.name = "Bobby"
   │  deps=ctx.deps  (passed along inside the tool)
   ├──► study_agent  ── ctx.deps.name = "Bobby"
   └──► career_agent ── ctx.deps.name = "Bobby"
```

**What each agent actually knows.** This is the part that surprises people:

| Agent | Knows the user's original question? | Knows the client card (deps)? | Knows what else? |
| --- | --- | --- | --- |
| `coach_agent` | **Yes** | Yes | Its own steps |
| `study_agent` | **No** | Yes | Its own instructions, plus only the `question` text the coach wrote |
| `career_agent` | **No** | Yes | Its own instructions, plus only the `question` text the coach wrote |

The experts are **not listening in**. They only get the question the coach chose to send. A vague question from the coach gives a vague answer from the expert.

Also, having the card does not mean an agent *uses* it. `ClientDeps` has five fields, but the code only ever reads `ctx.deps.name`. The other four are available and ignored (gotcha 6.1).

### 3.3 Static vs dynamic `instructions`: "a fixed script plus one filled-in line"

`instructions` is the text that tells an agent who it is. There are two kinds, and they are added together.

**Static = written once, the same every time:**

```python
study_agent = Agent(..., instructions="You are a study expert. Give concrete study plans and learning techniques.")
```

**Dynamic = a function, so it can use the client card:**

```python
@study_agent.instructions
def study_name(ctx):
    return f"Student's name is {ctx.deps.name}. Address them by name"
```

The line `@study_agent.instructions` means "add the text this function returns to the study agent's instructions, every time it runs".

**What the study agent really receives** when the client is Bobby (roughly):

```
Instructions, part 1 (static):   You are a study expert. Give concrete study plans and learning techniques.
Instructions, part 2 (dynamic):  Student's name is Bobby. Address them by name
User message:                    <the question the coach wrote>
```

Why not put the name into the static string? The static string is fixed when the file loads, **before** you know who the client is. The dynamic function runs later, at `.run()` time, when `deps` exists. Use dynamic whenever the text depends on run-time data.

| Is the text the same for every run? | Use |
| --- | --- |
| Yes ("You are a study expert") | static `instructions="..."` |
| No, it needs `ctx.deps` ("The client is Bobby") | an `@agent.instructions` function |

### 3.4 The numbered steps: "a to-do list the model is asked to follow"

The coach's instructions are a list of five steps:

```
1. Call `ask_study_agent` for study questions.
2. Call `ask_career_agent` for career questions.
3. Combine the answers into ONE short, simple response.
4. Call `export_report` with that final response as `text`.
5. Reply to the user with the final response.
```

**Why it works.** The model re-reads these steps each time it decides what to do next. The names in backticks must match the real function names, so the model knows which tool each step means. After a tool result comes back, it looks at the list again and picks the next step.

**Why it can still go wrong.** Your Python code never says "do step 1, then 2, then 3". Only the model decides. It *usually* follows the list, but it might skip `export_report`, call a tool twice, or answer without delegating at all.

| Normal Python | Model following a list |
| --- | --- |
| `step1(); step2(); step3()` always runs in order | The model is **asked** to follow the order |
| A missing step is a bug you can see in the code | A missing step only shows in the output (or a missing file) |

> **Data engineer view:** it is like an Airflow DAG where the task order is a *suggestion written in English*. That is flexible, and less reliable than real code. If a step must always happen (saving the report, say), check it in your own code after the run, for example "does the file exist?".

---

## 4. The files

### 4.1 `model.py` — which model

| Line | Code | Meaning |
| --- | --- | --- |
| 18 to 22 | imports | `os`, `load_dotenv`, `OpenAIChatModel`, `OpenAIProvider` |
| ~26 | `load_dotenv()` | Reads `NVIDIA_API` from `.env` into the environment |
| 29 | `def nvidia_model(model_name: str) -> OpenAIChatModel:` | Lecture 01's Provider + Model wrapped in a function |
| inside | `base_url="https://integrate.api.nvidia.com/v1"` | Nvidia's address. Nvidia copies OpenAI's protocol, so the OpenAI classes work. |
| inside | `api_key=os.environ["NVIDIA_API"]` | A `KeyError` here means your `.env` is missing or the name is wrong |

Same helper as in lectures 03 and 06. Each folder keeps its own copy because Python imports files from the folder you run from.

### 4.2 `dependencies.py` — who we are coaching

| Field | Type | Default | Used by an agent? |
| --- | --- | --- | --- |
| `name` | `str` | required | **Yes**: dynamic instructions and the export file name |
| `goal` | `str` | required | No |
| `experience_lvl` | `Literal["beginner","intermediate","advanced"]` | `"beginner"` | No |
| `weekly_hours` | `int` | `8` | No |
| `current_role` | `str \| None` | `None` | No |

- `@dataclass` writes `__init__` for you, so `ClientDeps(name="Bobby", goal="...")` works.
- Fields **without** a default come first (`name`, `goal`). Python requires that.
- `Literal[...]` limits the value to those three strings. A type checker (and your editor) warns about anything else. It is not enforced when the program runs.
- The filename: your original lecture import said `depdencies` (typo). The file is `dependencies.py`, so `agents.py` now imports `from dependencies import ClientDeps`.

### 4.3 `agents.py` — three agents and the handoff

| Lines | Code | Meaning |
| --- | --- | --- |
| 28 to 34 | imports | `datetime`, `Path`, `Agent`, `RunContext`, `ClientDeps`, `nvidia_model` |
| 37 | `model = nvidia_model("nvidia/nemotron-3.5-super-vl-120b-a12b")` | **One** model object shared by all three agents |
| 47 | `study_agent = Agent(...)` | `model` + `deps_type=ClientDeps` + `instructions` |
| 55 | `career_agent = Agent(...)` | Same shape, different instructions |
| 67 | `coach_agent = Agent(...)` | Same shape, instructions are the 5-step recipe |
| 89, 94, 99 | `@..._agent.instructions` functions | Dynamic instruction: inject `ctx.deps.name` |
| 114 | `ask_study_agent` | Tool: delegate to the study agent |
| 126 | `ask_career_agent` | Tool: delegate to the career agent |
| 134 | `export_report` | Tool: write the final text to a file |

The file builds objects and **runs nothing**. Reading order that makes it easy: agents (47 to 80), then dynamic instructions (89 to 102), then tools (114 to end).

**`export_report` step by step:**

| Code | What it does |
| --- | --- |
| `datetime.now().strftime("%Y%m%d_%H%M%S")` | A timestamp such as `20261109_083600`, so each run gets a new file |
| `Path("exports")` and `mkdir(exist_ok=True)` | Create the folder if missing, no error if it exists. It is **relative to where you run Python**. |
| `ctx.deps.name.casefold()` | Lowercase name for the file name (`bobby_...`) |
| `path.write_text(text)` | Save the text. There is no `return`, so the model receives `None`. |

It is a plain `def` (not `async`) because it only does a quick local file write. Both styles can be mixed in one agent.

### 4.4 `main.py` — the script you run

| Line | Code | Meaning |
| --- | --- | --- |
| 14 | `import asyncio` | To start async code from a normal script |
| 17 | `from agents import ClientDeps, coach_agent` | `ClientDeps` is available here because `agents.py` imported it |
| 20 | `async def main(prompt, **kwargs)` | Runs the coach and prints `result.output`. `**kwargs` forwards `deps=...`. |
| 31 | `if __name__ == "__main__":` | Runs only when you start this file directly |
| 33 to 39 | `client = ClientDeps(name="Bobby", ...)` | The profile every agent can read |
| 41 | `asyncio.run(main("I'm learning Python...", deps=client))` | Start the event loop and run the question |

`main.py` never mentions the study or career agents. It talks to the coach only, and the coach decides everything else.

---

## 5. The notebook: `multiagent_handoff.ipynb`

The same system in one cell, plus a tiny experiment. Cell numbers are the order of **code** cells.

| Cell | What it shows |
| --- | --- |
| markdown | The idea: a question is answered directly or handed to a more specialized agent. 3 agents, "agents as tool". |
| **[1]** | `Path("./exports").mkdir(exist_ok=True)` and `datetime.now().strftime(...)`: a test of the two building blocks that `export_report` uses. Output looks like `'20261030_110202'`. |
| **[2]** | Everything from `agents.py` and `dependencies.py` in one cell, then `await coach_agent.run(..., deps=ClientDeps(name="Martin", ...))`. The result shows a combined roadmap that opens with "Martin, ...". |

Differences from the `.py` version:

| Notebook | `.py` files |
| --- | --- |
| `ClientDeps` is defined in the same cell | Its own file, `dependencies.py` |
| `career_agent` instructions: a plain string | A string with a trailing comma, so a 1-item tuple (see 6.5) |
| Client is "Martin" | Client is "Bobby" |
| `await coach_agent.run(...)` directly (notebooks have a running event loop) | `asyncio.run(main(...))` |
| `export_report` uses `Path` imported in cell `[1]` | `Path` imported at the top of `agents.py` |

---

## 6. Gotchas and things to improve

1. **Only `name` is ever used.** `goal`, `experience_lvl`, `weekly_hours` and `current_role` are collected but no agent reads them. Bobby's 16 hours a week never reaches a study plan. Fix: add them to the dynamic instructions, for example `f"... {ctx.deps.weekly_hours} hours per week, level {ctx.deps.experience_lvl}"`.
2. **`export_report` returns `None`.** The coach cannot tell you where the file went. Return `str(path)` instead.
3. **Run it from inside this folder.** `Path("exports")` is relative to the current directory, and `main.py` does `from agents import ...`, which needs the folder to be the current one.
4. **A name like `Anna Berg` or `a/b` goes into the file name.** Spaces are fine, but `/` or `:` would break the path. Sanitise it if names come from users.
5. **The `career_agent` trailing comma** (`"...career paths.",`) makes `instructions` a tuple. PydanticAI accepts a sequence, and I confirmed the agent still runs, so it is harmless, but it is a typo-style slip. The notebook version has no comma.
6. **The order is requested, not enforced.** The model might skip a step, call a tool twice or export before combining. For anything that must happen, check in code.
7. **Cost grows with each delegation.** Each tool call is a model call, and the coach re-sends its growing message list every time (lecture 02). Three agents meant 5 model calls per question in a real run (plus hidden thinking tokens).
8. **The order of the experts is up to the model.** The recipe lists study first, then career, but in a real run the model asked for **both in the same response**, and PydanticAI ran those two tools together. Do not rely on a fixed order.
9. **Windows crash: `UnicodeEncodeError: 'charmap' codec can't encode character '→'`.** `Path.write_text(text)` uses Windows' default encoding (cp1252), which cannot write characters such as `→` that the model often puts in its answer. `export_report` crashed after creating an **empty** file, so the run printed only the startup banner and no answer. Fixed with `path.write_text(text, encoding="utf-8")`. It is the same bug as lecture 01's cell `[7]`.

---

## 7. Running it

In a terminal **inside `07_multiagent_handoff/`**:

```bash
cd 07_multiagent_handoff
uv run main.py
```

| Need | Why |
| --- | --- |
| `NVIDIA_API=...` in `.env` | `model.py` reads it |
| An internet connection | The model is hosted by Nvidia |

What you see: the coach's short combined answer, and a new file `exports/bobby_<timestamp>.md` with the same text.

---

## 8. Glossary

| Term | Meaning |
| --- | --- |
| **Handoff / delegation** | One agent passes a question to a more specialized agent and uses the answer. |
| **Agent as a tool** | A tool function whose body calls another agent's `.run()`. |
| **Orchestrator** | The agent that decides which specialist to call and in what order. Here, the coach. |
| **Specialist** | An agent with a narrow job and a short focused prompt. |
| **Deps** (dependencies) | Data your code hands to the run (`ClientDeps`). Tools and dynamic instructions read it via `ctx.deps`. |
| **`RunContext`** | The hidden first parameter that gives a function access to `ctx.deps` and `ctx.usage`. |
| **`usage`** | The token/request counter. Passing `usage=ctx.usage` makes sub-agents add to the parent's total. |
| **Static instructions** | A fixed string given to `Agent(instructions=...)`. |
| **Dynamic instructions** | A function decorated with `@agent.instructions` that builds text from `ctx.deps` at run time. |
| **`@dataclass`** | A decorator that turns a class with typed fields into a simple container. |
| **`Literal`** | A type that allows only the listed exact values. |
| **`.output`** | The final value of an agent run, here a string. |
| **`asyncio.run`** | Starts an async function from normal code. |
| **`casefold()`** | A strong lowercase, used here for the file name. |
