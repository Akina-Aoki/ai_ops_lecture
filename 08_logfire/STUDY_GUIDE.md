# Study guide: 08 Logfire (monitoring and prompt management)

| When you are reading... | Read this section |
| --- | --- |
| The big idea | [1. The 30-second version](#1-the-30-second-version) and [2. The pictures](#2-the-pictures-to-understand) |
| Words like span, trace, metric | [3.1 Observability](#31-observability-a-flight-recorder-for-your-program) |
| `main.py` | [4.5 main.py](#45-mainpy--the-script-you-run) |
| `prompts.py` | [4.3 prompts.py](#43-promptspy--prompts-from-logfire) |
| `agents.py` | [4.4 agents.py](#44-agentspy--the-same-three-agents-new-prompt-source) |
| `model.py`, `dependencies.py` | [4.1](#41-modelpy--which-model) and [4.2](#42-dependenciespy--who-we-are-coaching) |
| Setting up Logfire and the keys | [5. Setup and running](#5-setup-and-running) |
| Things that can bite you | [6. Gotchas](#6-gotchas-and-things-to-improve) |

---

## 1. The 30-second version

Lecture 07 built a coach agent that delegates to a study agent and a career agent. Lecture 08 keeps **all of that unchanged** and adds two things from a tool called **Logfire**:

| New in 08 | In one sentence | Where in the code |
| --- | --- | --- |
| **Monitoring** (observability) | Every agent run, model call and tool call is recorded and sent to the Logfire website, so you can look at what happened afterwards. | 3 lines in `main.py` |
| **Prompt management** | The agents' instructions are no longer typed in the code. They are stored on the Logfire website and downloaded when the program starts. | the new file `prompts.py` |

> **Why do this?** An AI app is hard to debug. The answer is different each time, and one question can trigger several model calls and tool calls. Without a record you only have what you `print`. And if a prompt needs a fix, you would have to edit code and run again.

> **Data engineer view:**
> - **Monitoring** is what the Airflow UI and your pipeline logs give you: which task ran, in what order, how long it took, where it failed. Logfire gives the same for an AI app.
> - **Prompt management** is like moving settings out of the code into a config table. You change a row, not the program.

---

## 2. The pictures to understand

### Picture A: how the files connect, and the start-up order

```
 model.py          nvidia_model("...")     the AI connection (same as 07)
 dependencies.py   ClientDeps              the client profile (same as 07)
 prompts.py        get_prompt("...")       NEW: downloads a prompt from Logfire
        │                 │
        ▼                 ▼
 agents.py   study_agent ─┐
             career_agent ─┼─ same model + deps_type, but instructions=get_prompt(...)
             coach_agent ──┘   + 3 tools: ask_study_agent, ask_career_agent, export_report
        │
        ▼
 main.py     turns on Logfire, creates ClientDeps, runs coach_agent    ◄── you run this one
        │
        ├──► Nvidia model (the API)           exports/<name>_<time>.md
        └──► Logfire (the website)            receives the trace of the run
```

**Order in time.** `main.py` begins with `from agents import ...`. That line runs `agents.py`, which runs `prompts.py`. So this happens **before the first line of `main.py`'s own code**:

```
python main.py
   └─ import agents ──► import prompts ──► logfire.configure(api_key=...)      (connect, read-only key)
                    └─► get_prompt("study_agent_instructions")   ─► network call to Logfire
                    └─► get_prompt("career_agent_instructions")  ─► network call to Logfire
                    └─► get_prompt("coach_agent_instructions")   ─► network call to Logfire
                    └─► three Agent(...) objects are built with those texts
   then main.py's own code:
   load_dotenv() ─► logfire.configure() ─► instrument_system_metrics() ─► instrument_pydantic_ai()
   then the run: asyncio.run(main(...))
```

This matches the numbered arrows in `architecture_08.png`: arrows 1 to 4 are the downloads (once, at start-up), arrows 5 to 8 are the run.

### Picture B: what one run looks like in Logfire

I ran your real `agents.py` with Logfire's instrumentation on and a **fake model** (no Nvidia call, no Logfire account needed). I swapped only `prompts.py` and `model.py` for stand-ins, and collected the spans in memory. Here is the tree that came out:

```
invoke_agent coach_agent                       ← the whole run (the top of the tree)
 ├─ chat <model name>                          ← coach model call 1: "I'll ask the study agent"
 ├─ execute_tool ask_study_agent
 │    └─ invoke_agent study_agent              ← the specialist's own run, INSIDE the tool
 │         └─ chat <model name>
 ├─ chat <model name>                          ← coach model call 2: "now the career agent"
 ├─ execute_tool ask_career_agent
 │    └─ invoke_agent career_agent
 │         └─ chat <model name>
 ├─ chat <model name>                          ← coach model call 3: "save the report"
 ├─ execute_tool export_report
 └─ chat <model name>                          ← coach model call 4: writes the final answer
```

Result of that run: **12 spans, all in 1 trace**, and `RunUsage(input_tokens=316, output_tokens=52, requests=6, tool_calls=3)` (the token numbers are from the fake model, so ignore them; the counts of 6 requests and 3 tool calls match lecture 07).

Three things to notice:

1. **One run = one trace.** Even though three agents took part, everything is in a single tree, because the specialists run inside the coach's tool calls.
2. **The span names are `invoke_agent ...`, `chat ...` and `execute_tool ...`.** In the Logfire website you will see these, with your real model name after `chat`.
3. **You did not write any code for this.** `logfire.instrument_pydantic_ai()` is what makes it happen.

> The README's tree uses simpler labels (`span: model request`). The *shape* is the same; the names above are what I actually got.

### Picture C: from a prompt in Logfire to the text the model sees

```
Logfire website                                           your code
┌─────────────────────────────────────┐
│ variable: prompt__study_agent_...   │   get_prompt("study_agent_instructions")
│   version 1  "You are a study..."   │ ────────────────────────────────────────►  Agent(instructions=<that text>)
│   version 2  "You are a study..."   │                                                    │
│   version 3  "You are an expert..." │ ◄── label "production" points here                 ▼
└─────────────────────────────────────┘                                      what the model really gets:
                                                                             part 1: the Logfire text
                                                                             part 2: "Student's name is Bobby. Address them by name"
                                                                                      (from @study_agent.instructions, uses ctx.deps)
```

The Logfire text is **fixed for the run**. The `@agent.instructions` function from lecture 07 still adds one more sentence at run time, because only the code can read `ctx.deps`.

---

## 3. Ideas worth understanding

Keep the code open next to this section.

**The analogy used below:**

| In real life | In the code |
| --- | --- |
| A flight recorder ("black box") on a plane | **Logfire monitoring** |
| Cameras on each step of the factory line | `logfire.instrument_pydantic_ai()` |
| A recipe book kept in the cloud, not in the kitchen | Logfire **prompt management** |
| The recipe's edition number (1st, 2nd, 3rd) | the **version** |
| A sticky note saying "use this edition for service" | the **label** (`production`) |
| The cook fetching today's recipes before opening | `get_prompt(...)` at start-up |

### 3.1 Observability: a flight recorder for your program

"Observability" means: after something ran, can you tell **what it did and why**? Logfire uses four words for this. Learn them once, they are used in every monitoring tool.

| Word | Meaning | Example in this lecture |
| --- | --- | --- |
| **Log** | A timestamped note about one event, with no duration | "export_report was called" |
| **Span** | One piece of work with a **name, a start time and a duration** | one model call; one tool call; one whole agent run |
| **Trace** | A **tree of spans** for one request, parent and children | everything the coach did for one question |
| **Metric** | A number measured **over time** | CPU use, memory use, latency |

How they relate:

```
metric  =  a line on a chart that goes on all the time (CPU, memory)   ← not tied to one request
trace   =  one request from start to finish
span    =  one box inside the trace
log     =  a dot on the timeline (instant, no length)
```

> **Data engineer view:**
> - A **trace** is like one pipeline run in Airflow. A **span** is one task instance in that run, with start time and duration. A **metric** is the dashboard of worker CPU. A **log** is a line in the task log.
> - "Which task was slow, and what were its inputs?" is the question a trace answers.

**What you can answer afterwards with Logfire:**
- Which model call took the longest?
- What exact text did the coach send to the study agent?
- Which tool did the model choose, and with what arguments?
- How many tokens did one question cost?
- Did a tool crash, and on which call?

### 3.2 Instrumentation: "cameras on the factory line"

**Instrumentation** means adding recording to code, usually without changing the code. In `main.py`:

```python
logfire.configure()                # connect this program to my Logfire project
logfire.instrument_system_metrics()  # also record CPU and memory over time
logfire.instrument_pydantic_ai()   # record every agent run, model call and tool call
```

| Line | What it does | Which Logfire word |
| --- | --- | --- |
| `configure()` | Says "send everything to my project". Nothing is recorded yet. | setup |
| `instrument_pydantic_ai()` | PydanticAI now reports each agent run, each model request, each tool call, with inputs, outputs, token counts and timings. | **spans / traces** |
| `instrument_system_metrics()` | A background recorder of computer measures (CPU, memory...). | **metrics** |

**Order matters a little:** `configure()` first, then the `instrument_*` lines.

**You did not touch `agents.py`.** That is the point of instrumentation: the agents do not know they are being watched. The comment in `agents.py` says the same: every tool call and nested agent run "shows up as spans".

> **Privacy warning.** The recording includes the text of prompts and answers (instrument_pydantic_ai even has an `include_content` option to control this). Do not put passwords, API keys or customer data into prompts and then ship them to a monitoring website without thinking about it.

### 3.3 Prompt management: "the recipe book in the cloud"

**The problem in 07.** Prompts were strings inside `agents.py`. To change one word, you edit the code, commit, run again. A non-programmer cannot help.

**The 08 solution.** Each prompt is stored in Logfire as a **managed variable** (a named value kept on the website). The code just asks for it by name:

```python
instructions=get_prompt("study_agent_instructions")
```

Inside `get_prompt` (read it in 4.3) there are three names you should know:

| Word | Meaning | In this lecture |
| --- | --- | --- |
| **name** | The variable's name. The code adds the prefix `prompt__`. | `prompt__study_agent_instructions` |
| **version** | Every saved change becomes a new version. Old ones are kept. | 1, 2, 3, ... |
| **label** | A bookmark on one version. | `production` |
| **default** | Fallback text if nothing is found. | `"be a jokey assistant"` |

**Why labels exist.** Imagine version 3 is live (`production`) and you write version 4. If you put the `production` label on version 4, everyone gets it at once. Instead you can give version 4 another label (say `staging`), try it with `get_prompt(..., label="staging")`, and move `production` over only when you are happy.

> **Data engineer view:** it is like a table with a column `is_current`, or `latest` vs `v2` tags on a Docker image. The code asks for "the production one" and does not care which version number that is today.

**A trade-off to understand.** Prompts used to be in git, so you saw changes in the code review. Now the prompt lives outside your repository. You can change the agent's behaviour **without any commit**. That is the feature and also the risk: the code in git no longer tells you the whole behaviour. Logfire keeps the version history instead.

### 3.4 Why the prompts download "before main starts"

`prompts.py` has two kinds of code:

| Kind | Example | When it runs |
| --- | --- | --- |
| Inside a function | the body of `get_prompt` | only when called |
| At the top level, outside any function | `logfire.configure(api_key=...)` | **the moment the file is imported** |

`agents.py` does `from prompts import get_prompt`, so `configure(...)` runs immediately. Then `agents.py` itself calls `get_prompt(...)` three times at top level (inside `Agent(...)`), so the downloads also happen at import.

Consequences:

| Fact | What it means for you |
| --- | --- |
| The downloads happen at import | Start-up needs internet and takes a few seconds |
| It happens once per program start | Editing a prompt on the website changes the **next start**, not a program that is already running |
| A missing key stops everything early | If `LOGFIRE_PROMPTS` is absent, `os.environ["LOGFIRE_PROMPTS"]` raises `KeyError` before `main()` exists |

This is the same lesson as `model.py` with `os.environ["NVIDIA_API"]`: top-level code runs on import.

### 3.5 Two kinds of Logfire access

The lecture uses Logfire in two different ways, with two different "keys". This confuses most beginners.

| | Sending traces | Downloading prompts |
| --- | --- | --- |
| Done by | `main.py` → `logfire.configure()` | `prompts.py` → `logfire.configure(api_key=...)` |
| Credential | Your login from `uv run logfire auth` (stored on your computer) | `LOGFIRE_PROMPTS` in `.env`, an API key with the scope `project:read_variables` |
| Direction | Your app **sends** data to Logfire | Your app **reads** data from Logfire |
| Why separate | A read-only key is safer to put in `.env` than a full login | |

That is why `configure()` appears **twice** in the program (once in `prompts.py`, once in `main.py`). It works, but it is worth knowing about (gotcha 6.4).

---

## 4. The files

### 4.1 `model.py` — which model

Identical to lecture 07. `nvidia_model(model_name)` returns an `OpenAIChatModel` pointed at `https://integrate.api.nvidia.com/v1`, with `api_key=os.environ["NVIDIA_API"]`. A `KeyError` here means `.env` is missing or the name is wrong.

### 4.2 `dependencies.py` — who we are coaching

Identical to lecture 07. A `@dataclass` called `ClientDeps` with five fields: `name`, `goal` (both required), `experience_lvl`, `weekly_hours`, `current_role` (all with defaults). Only `name` is ever read by an agent (gotcha 6.5).

### 4.3 `prompts.py` — prompts from Logfire

This is the **new file**. 94 lines, but most are comments. The real code:

| Lines | Code | Meaning |
| --- | --- | --- |
| 34 to 38 | `import logfire`, `VariablesOptions`, `os`, `load_dotenv` | What the file uses |
| 36 | `from pydantic import BaseModel` | **Not used** anywhere in the file |
| 42 | `from pydantic_ai_harness.logfire import ManagedPrompt` | **Not used**, and needs an extra package (gotcha 6.1) |
| 45 | `load_dotenv()` | Reads `.env` so the next lines can find `LOGFIRE_PROMPTS` |
| 50 to 53 | `logfire.configure(api_key=os.environ["LOGFIRE_PROMPTS"], variables=VariablesOptions())` | **Runs at import.** Connects with the read-only key and switches the "variables" feature on |
| 56 | `def get_prompt(name, default="be a jokey assistant", label="production")` | The only function. Three inputs, two with defaults |
| 76 to 80 | `prompt = logfire.var(name=f"prompt__{name}", type=str, default=default)` | **Declares** the variable: its Logfire name, that it is text, and the fallback |
| 83 | `prompt.refresh_sync(force=True)` | **Downloads** the latest values now. `force=True` skips the local cache. `_sync` means "wait until finished". |
| 85 | `resolved = prompt.get(label=label)` | Picks the version that has the requested label |
| 87 | `print(resolved.version, resolved.label)` | Debug line: **this is the line you see in the terminal at start-up** |
| 88 | `return resolved.value` | The prompt text |
| 92 to 93 | `if __name__ == "__main__": print(get_prompt("coach_agent_instructions"))` | Test this file alone: `uv run prompts.py` |

**`get_prompt` as plain English:**

> "Logfire, I want the variable `prompt__<name>`. Refresh it from the website, give me the version labelled `production`, show me which version that was, and hand me its text. If none exists, give me the joke default."

**Declare, then refresh, then get.** Three steps, three lines. Beginners expect one. They are separate because:
1. `logfire.var(...)` only creates a local handle (the name, the type and the fallback).
2. `refresh_sync` goes to the network.
3. `.get(label=...)` reads from what was downloaded.

**`VariablesOptions()` with no arguments.** It has defaults, for example a 60-second polling interval and a 10-second network timeout. For this script they do not matter, because the prompts are read once at start-up.

### 4.4 `agents.py` — the same three agents, new prompt source

Compare with 07. The structure is the same; **the only change** is the `instructions=` line of each agent:

```python
# 07: text written in the code
study_agent = Agent(model=model, deps_type=ClientDeps,
                    instructions="You are a study expert. Give concrete study plans...")

# 08: text downloaded from Logfire
study_agent = Agent(model=model, deps_type=ClientDeps,
                    instructions=get_prompt("study_agent_instructions"))
```

| Lines | Code | Meaning |
| --- | --- | --- |
| 40 to 54 | imports | Includes `from prompts import get_prompt` (line 54), the new one |
| 58 | `model = nvidia_model("nvidia/nemotron-3.5-super-vl-120b-a12b")` | One model shared by all agents |
| 71, 77, 86 | `study_agent`, `career_agent`, `coach_agent` | Each calls `get_prompt(...)` while being built. **Three network calls at import.** |
| 103, 108, 113 | `@..._agent.instructions` functions | Add `"... name is {ctx.deps.name}. Address them by name"` at run time (unchanged from 07) |
| 131 | `ask_study_agent` | Tool: calls `study_agent.run(question, deps=ctx.deps, usage=ctx.usage)` |
| 143 | `ask_career_agent` | Tool: same for the career agent |
| 150 | `export_report` | Tool: writes the text to `exports/<name>_<time>.md` |

For how the handoff tools work (`deps=ctx.deps`, `usage=ctx.usage`, `await`) read **Section 3.1 of the lecture 07 guide**. Nothing there changed.

**One new dependency you cannot see in the file.** The coach's tools are called by name, and the numbered steps that tell the coach to use them are now **inside the Logfire prompt**, not in this repo. So the prompt in Logfire must mention `ask_study_agent`, `ask_career_agent` and `export_report` with exactly those spellings. If you rename a function here and forget the prompt (or the other way round), nothing crashes: the coach just stops using the tool.

### 4.5 `main.py` — the script you run

| Line | Code | Meaning |
| --- | --- | --- |
| 35 | `from agents import coach_agent, ClientDeps` | **Triggers all the prompt downloads** (Picture A) |
| 36 to 38 | `asyncio`, `logfire`, `load_dotenv` | Imports |
| 43 | `load_dotenv()` | Load `.env` again (harmless, the other files already did) |
| 48 | `logfire.configure()` | Connect to your Logfire project (uses your `logfire auth` login) |
| 51 | `logfire.instrument_system_metrics()` | Record CPU and memory. Needs the `logfire[system-metrics]` extra. |
| 55 | `logfire.instrument_pydantic_ai()` | Record every agent run, model call and tool call |
| 60 to 67 | `async def main(prompt, **kwargs)` | Runs the coach and prints `result.output` |
| 71 | `if __name__ == "__main__":` | Runs only when you start this file directly |
| 73 to 79 | `client = ClientDeps(name="Bobby", ...)` | The profile every agent can read |
| 81 to 86 | `asyncio.run(main("I'm learning Python...", deps=client))` | Start the event loop and run the question |

Same as 07, `main.py` never mentions the specialists. The only new lines are the three `logfire` ones (48, 51, 55).

---

## 5. Setup and running

### One-time setup

1. **Create a Logfire account** (link in the README) and sign in.
2. **Install the packages** (the README gives these):

   ```bash
   uv add logfire
   uv run logfire auth
   uv add "logfire[variables]"
   uv add "logfire[system-metrics]"
   ```

   | Command | What it gives you |
   | --- | --- |
   | `uv add logfire` | The Logfire library |
   | `uv run logfire auth` | Logs your computer into your Logfire account (a browser opens) |
   | `uv add "logfire[variables]"` | The extra needed for `logfire.var(...)` (prompt management). Without it `logfire.var` raises `ImportError: Using managed variables requires the pydantic_handlebars and pydantic packages` (I saw this exact error). |
   | `uv add "logfire[system-metrics]"` | The extra needed for `instrument_system_metrics()` |

3. **Create three prompts** in the Logfire web app (as managed variables) and give each version the label `production`:

   ```
   prompt__coach_agent_instructions
   prompt__study_agent_instructions
   prompt__career_agent_instructions
   ```

   You can copy the text from the instructions in `07_multiagent_handoff/agents.py`.

4. **Create an API key** in Logfire with the scope `project:read_variables`.
5. **Put the keys in `.env`** (this folder or the repo root):

   ```
   NVIDIA_API=your_nvidia_key_here
   LOGFIRE_PROMPTS=your_logfire_key_here
   ```

   Never commit `.env`. It is already ignored by git for this repo, but check before you push.

### Every time you run it

In a terminal **inside `08_logfire/`**:

```bash
cd 08_logfire
uv run main.py
```

| What you should see | Meaning |
| --- | --- |
| Three lines like `3 production` | `version label` of each downloaded prompt (the `print` on line 87 of `prompts.py`). Check these first. |
| The coach's short combined answer | The run worked |
| A new file `exports/bobby_<timestamp>.md` | `export_report` ran |

Then open your Logfire project in the browser and look at the newest trace (a `invoke_agent coach_agent` at the top, as in Picture B).

**If no trace appears:** run `uv run logfire whoami` (are you logged in?) and `uv run logfire projects use <your-project>` (is this folder tied to a project?). `uv run logfire projects status` shows what telemetry has reached the project.

---

## 6. Gotchas and things to improve

1. **The unused `ManagedPrompt` import can stop the program.** `prompts.py` line 42 imports `pydantic_ai_harness`, which is a separate package. In this repository's `.venv` it is **not installed**: `import pydantic_ai_harness` gives `ModuleNotFoundError`. The README's setup does not install it either. If you see that error, either install the package or (better) delete that import and the unused `from pydantic import BaseModel`. They do nothing.
2. **Your `pyproject.toml` does not list `logfire` yet.** It has `pydantic-ai`, which brings Logfire's core in indirectly, but not the `variables` and `system-metrics` extras. The README's `uv add` commands add them and update `pyproject.toml` and `uv.lock`; commit those files too, or a fresh clone will break.
3. **A wrong name or label does not crash, it changes behaviour.** The fallback is `"be a jokey assistant"`. If your coach suddenly jokes around, the prompt was not found. Check the printed `version label` line and the spelling of `prompt__...` in Logfire. (I could not test the exact printout without a Logfire project; the code comment describes this fallback.)
4. **`logfire.configure()` is called twice** (`prompts.py` with the read-only key, `main.py` without). It works in this lecture, but two configure calls with different settings can surprise you in a larger project. A cleaner design is one `configure()` call in one place.
5. **Only `name` is ever used from `ClientDeps`.** `goal`, `experience_lvl`, `weekly_hours` and `current_role` are collected and then ignored. Add them to the dynamic instructions, e.g. `f"... {ctx.deps.weekly_hours} hours per week"`.
6. **Prompts are read once, at start-up.** Editing a prompt on the website does not change a program that is already running (for example a web server). It takes effect at the next start. Also, a prompt edit is not in git, so write down what you changed and why.
7. **`export_report` crashes on Windows for some characters.** `path.write_text(text)` on line 161 has no `encoding="utf-8"`. I reproduced it by saving the text `FINAL → ok`:

   ```
   UnicodeEncodeError: 'charmap' codec can't encode character '→'
   ```

   The crash happens inside the tool, so the whole run fails after the model already did all its work. Lecture 07 fixed it with `path.write_text(text, encoding="utf-8")`. Do the same here.
8. **`export_report` returns nothing**, so the coach cannot tell you where the file went. Return `str(path)`.
9. **Typo in `coach_name`:** `"advicing"` should be `"advising"`. Harmless, but the model reads it.
10. **Run from inside this folder.** `Path("exports")` is relative to where you run Python, and `from agents import ...` needs `agents.py` next to you.
11. **Monitoring costs a bit and can leak content.** Every span is sent over the internet and includes prompt and answer text. Fine for a lecture; think before doing it with real customer data.
12. **Traces are not a replacement for tests.** Logfire shows you *what happened*; it does not tell you whether the answer was *good*. That is the next topic (the README has a commented placeholder for "Part 2 - LLM judge").

---

## 7. Glossary

| Term | Meaning |
| --- | --- |
| **Logfire** | A monitoring website and library from the makers of Pydantic. Receives traces and metrics and stores prompts. |
| **Observability** | Being able to tell what a program did, and why, after it ran. |
| **Instrumentation** | Adding recording to code. `logfire.instrument_pydantic_ai()` does it for PydanticAI. |
| **Span** | One piece of work with a name, start time and duration. |
| **Trace** | A tree of spans for one request. One coach run is one trace. |
| **Metric** | A value measured over time, such as CPU load. |
| **Log** | A timestamped record of one event with no duration. |
| **Managed variable** | A named value stored in Logfire and fetched by code with `logfire.var(...)`. Here, a prompt. |
| **Prompt management** | Keeping prompts outside the code, with versions and labels. |
| **Version** | A saved edition of a prompt. Each change makes a new one. |
| **Label** | A bookmark on a version, such as `production`. The code asks for a label, not a number. |
| **Default (fallback)** | Text used if Logfire has no value. Here `"be a jokey assistant"`. |
| **`LOGFIRE_PROMPTS`** | The `.env` key that lets the code read prompts (scope `project:read_variables`). |
| **`uv run logfire auth`** | Command that logs your computer into Logfire so traces can be sent. |
| **Import-time code** | Code at the top of a file, outside functions. It runs when the file is imported. |
| **`refresh_sync`** | Download the variable's latest value and wait until done. |
| **Handoff / agent as a tool** | A coach tool whose body calls another agent's `.run()`. Explained in the lecture 07 guide. |
