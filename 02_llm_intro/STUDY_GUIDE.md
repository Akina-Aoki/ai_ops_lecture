# Study guide: 02 LLM intro

Keep this open next to `llm_intro.ipynb`. Read a cell in the notebook, then read the matching section here.
This guide explains the **why**. The notebook already explains the **what**.

**How cells are numbered here.** VS Code shows a badge like `[3]` to the left of each **code** cell after it runs. In this guide `[3]` means the **3rd code cell from the top**, which is the cell that shows `[3]` after **Restart, then Run All**. Markdown cells have no badge, so I call them by their heading. Line numbers are lines **inside** the cell.

| Guide label | Type | How the cell starts | Badge saved in the file today |
| --- | --- | --- | --- |
| title | markdown | `# Introduction to LLMs using Nvidia Build` | none |
| **[1]** | code | `# Agent: ...` then `from pydantic_ai import Agent` (2 lines) | [1] |
| **[2]** | code (42 lines) | `# Agent: ...` then all imports, model, agent with `system_prompt`, the run | [2] |
| "What does this code do?" | markdown | `## What does this code do?` | none |
| **[3]** | code | `print(result.output)` | [3] |
| "Check the messages" | markdown | `## Check the messages` | none |
| **[4]** | code | `result.all_messages()` | [4] |
| **[5]** | code | `len(result.all_messages())` | [5] |
| **[6]** | code | `result.all_messages()[0]` | [6] |
| **[7]** | code | `result.all_messages()[0].parts[1].content` | [7] |
| **[8]** | code | `agent._system_prompts` | [8] |
| "Analyze tokens" | markdown | `# Analyze tokens` | none |
| **[9]** | code | `print(result.usage)` | [9] |
| **[10]** | code | `prompt = result.all_messages()[0].parts[1].content` | [10] |
| **[11]** | code | `print(f"system_prompt_words = ...` (3 lines) | [11] |
| "Basic prompt engineering" | markdown | `## Basic prompt engineering` | none |
| **[12]** | code (18 lines) | `chef_bot = Agent(` | none (not run when saved) |
| **[13]** | code | `print(result.output)` (the one after `chef_bot`) | [19] |
| "Temperature" | markdown | `# Temperature` | none |
| **[14]** | code (15 lines) | `from pydantic_ai import ModelSettings` | [14] |
| **[15]** | code | `result = await agent.run(prompt, timeout=120)` | [15] |
| **[16]** | code | `agent.model_settings = ModelSettings(temperature=1.5)` | [16] |
| **[17]** | code | `result = await agent.run(prompt, timeout=120)` | [17] |
| "Multimodal inputs" | markdown | `# Multimodal inputs (Will give an error)` | none |
| "Do not run" | markdown | `# Do not run` (code written as text) | none |
| **[18]** | code | `print(result.response.parts[0].content)` | [18] |
| (last cell) | empty code cell | nothing | none |

The saved badges for **[12]** and **[13]** are off because those cells were run out of order. After **Restart, then Run All** every badge matches the guide label. If a number ever disagrees with what you see, match the cell by how it starts (third column).

| When you are reading... | Read this section |
| --- | --- |
| Cell [2] (the big cell) | [3. Cell [2]](#cell-2--lecture-01-plus-one-new-idea-system_prompt) |
| Cells [3] to [8] (messages) | [4. Messages](#4-cells-3-to-8--what-is-really-sent-the-messages-list) |
| "Analyze tokens", cells [9] to [11] (tokens) | [5. Tokens](#5-cells-9-to-11--tokens-under-analyze-tokens) |
| "Basic prompt engineering", cells [12] and [13] (chef bot) | [6. Prompt engineering](#6-cells-12-and-13--prompt-engineering-under-basic-prompt-engineering) |
| "Temperature", cells [14] to [17] | [7. Temperature](#7-cells-14-to-17--temperature-under-temperature) |
| "Multimodal inputs", "Do not run" and cell [18] (images, thinking) | [8. Images and thinking](#8-multimodal-cells-and-cell-18--images-and-the-thinking-part) |
| Any later lecture | [10. Where this reappears](#10-where-this-reappears-in-later-lectures) |

---

## 1. The 30-second version

Lecture 01 gave you a phone line to the AI. Lecture 02 teaches you to **control** the call and **look inside** it.

There are five ideas, one per section of the notebook:

| Idea | One sentence | Cells |
| --- | --- | --- |
| **System prompt** | A standing instruction that shapes every answer | [2] |
| **Messages** | A conversation is a list of messages, and you can inspect it | [3] to [8] |
| **Tokens** | The unit the model reads and writes, and the unit you pay and wait for | "Analyze tokens", [9] to [11] |
| **Temperature** | A dial from "predictable" to "creative" | "Temperature", [14] to [17] |
| **Multimodal** | Input is not only text (images), if the model supports it | "Multimodal inputs", "Do not run" |

---

## 2. The two pictures to understand

### Picture A: the model has no memory

```
You ask:   "Why is it foggy in Göteborg?"
                    │
   Your code builds a list of messages and sends the WHOLE list
                    │
                    ▼
  [ system: "You are a joking programming bot..."   ]
  [ user:   "Why is it foggy in Göteborg right now?" ]  ──►  Nvidia runs the model
                                                              │
                                                              ▼
                                         [ model: "Are you experiencing a dew point overflow..." ]
```

The model itself **remembers nothing** between calls. If you want a conversation, your code must send the earlier messages again each time. That is the whole reason `message_history` exists (cell [4] shows what it looks like, lecture 05 uses it for the chatbot).

> **Data engineer view:** an API call is stateless, like a plain HTTP request. The "state" (the conversation) lives in **your** code, like a session you store in a table and pass back in.

### Picture B: what one run produces

```
result  (an AgentRunResult)
 ├── output ───────────────► "Are you experiencing a dew point overflow..."   (the answer text)
 ├── usage ────────────────► RunUsage(input_tokens=45, output_tokens=1066, requests=1)
 └── all_messages() ───────► a list of 2 messages
        ├── [0] ModelRequest   (what we SENT)
        │       ├── parts[0] SystemPromptPart   "You are a joking programming bot..."
        │       └── parts[1] UserPromptPart     "Why is it foggy in Göteborg right now?"
        └── [1] ModelResponse  (what came BACK)
                ├── parts[0] ThinkingPart  (the model's hidden reasoning)
                └── parts[1] TextPart      "Are you experiencing a dew point overflow..."
```

Keep this tree in mind for cells [3] to [11] and [18]. Every one of those cells is just reading a different branch of it.

---

## 3. The notebook, cell by cell

### The title cell and cell [1] (import)

Cell [1] is the one-line import from lecture 01. It is redundant, because cell [2] imports `Agent` again. Harmless.

### Cell [2] — lecture 01 plus one new idea: `system_prompt`

Compare with the big code cell in lecture 01 (cell [2] in the lecture 01 guide). Almost everything is the same:

| Lines | What | New? |
| --- | --- | --- |
| 1 to 12 | Imports | same |
| 16 | `load_dotenv()` | same |
| 20 to 26 | Provider inside Model | same |
| 29 to 32 | `Agent(model, system_prompt=...)` | **new: `system_prompt`** |
| 34 | `prompt = "..."` | **new: the question lives in a variable** |
| 39 | `await agent.run(prompt)` | same |
| 42 | `print(result.output)` | same |

#### What `system_prompt` is

Line 31: `system_prompt="You are a joking programming bot that will always ask questions back in a nerdy joke style"`.

- It is a **standing instruction**. It goes at the start of the conversation, before the user's question.
- The user never sees it. It is written by **you, the developer**.
- It changes the model's behaviour **without changing the question**. Same question, different system prompt, different answer.
- Compare:

| | Written by | Changes | Example |
| --- | --- | --- | --- |
| **system prompt** | the developer | rarely (it defines the bot) | "You are a joking programming bot..." |
| **user prompt** | the user | every call | "Why is it foggy in Göteborg right now?" |

> **Data engineer view:** the system prompt is configuration. The user prompt is the input row.

#### Why the answer is not really an answer

The user asked **why** it is foggy **right now**. The model has no access to today's weather. So it jokes and asks a question back, which is exactly what the system prompt told it to do. In a real weather bot you would fix the missing data with a **tool** that fetches the weather. That is `06_tool_use`, and it is built for this kind of question.

#### The banner in the output

The `pydantic-ai v2.62.0` box is just a startup message. It says "observability: off" because **tracing** (Logfire) comes in a later lecture. To hide it, set the environment variable `PYDANTIC_AI_NO_BANNER=1`.

---

## 4. Cells [3] to [8] — what is really sent: the messages list

| Cell | Code | What you see | What it teaches |
| --- | --- | --- | --- |
| [3] | `print(result.output)` | The answer text again | `output` is only the **text part** |
| [4] | `result.all_messages()` | A list with a `ModelRequest` and a `ModelResponse` | The conversation is a list of message objects |
| [5] | `len(...)` | `2` | One request + one response |
| [6] | `...[0]` | The `ModelRequest` | It has **parts** |
| [7] | `...[0].parts[1].content` | The user's question | `parts[0]` is the system prompt, `parts[1]` is the user prompt |
| [8] | `agent._system_prompts` | A tuple with the system prompt | The agent stores it |

Read cell [4]'s output with picture B next to it. The `ModelResponse` has **two** parts: a `ThinkingPart` (the model's reasoning, very long) and a `TextPart` (the answer). `result.output` is only the `TextPart`.

Two cautions:

1. **`agent._system_prompts` starts with an underscore.** In Python that means "internal, not meant for users". It is fine for looking around in a lesson. Do not build code on it, because it can change between versions.
2. **`parts[1]` assumes the order.** It works here because there is a system prompt at position 0. With no system prompt, the user prompt would be at `parts[0]`.

### `system_prompt` vs `instructions` (you will see both in the course)

You will see `system_prompt=` here and in lecture 05, and `instructions=` in lectures 03 and 06. They look alike. I tested the difference in your installed version (pydantic-ai 2.62.0):

| | `system_prompt` | `instructions` |
| --- | --- | --- |
| Where it ends up | Written **into the message history** as a `SystemPromptPart` (cell [7] shows this) | Attached to each request from the **current** agent, not stored as a message part |
| When you pass an old `message_history` | The old system prompt comes along with the old messages. The new agent's `system_prompt` is **not** added. | The current agent's `instructions` are used for the new request |
| Good for | A chat that you continue later (lecture 05) | An agent whose job description may change (lecture 06) |

For lecture 02 you can treat them as "the standing instruction".

---

## 5. Cells [9] to [11] — tokens (under "Analyze tokens")

### What is a token?

The model does not read letters or words. It reads **tokens**: small chunks of text. A short common word is often one token. A long or rare word is several. Punctuation and spaces count too.

### Why you care about tokens

| Because... | Explanation |
| --- | --- |
| **You pay per token** | Providers charge for input tokens and output tokens. |
| **You wait per token** | The model writes its answer one token at a time. More tokens means slower. |
| **There are limits** | Providers limit requests and tokens per minute. A model can only read a limited number of tokens at once (its "context window"). |

### What your numbers say (cells [9] and [11])

```
RunUsage(input_tokens=45, output_tokens=1066, output_reasoning_tokens=1000, requests=1)   (shortened from cell [9])
system_prompt_words = 17     user_prompt_words = 8     output_words = 45
```

| Number | What it is | What to notice |
| --- | --- | --- |
| `input_tokens = 45` | System prompt + user prompt, sent to the model | 17 + 8 = 25 **words**, but 45 **tokens**. Tokens are not words. The message formatting adds some too. |
| `output_tokens = 1066` | Everything the model wrote | **Much** more than the visible answer |
| `reasoning_tokens = 1000` | Part of the output that was the model "thinking" | This is the `ThinkingPart` from picture B |
| visible answer | 1066 − 1000 ≈ 66 tokens | The answer has 45 words, so roughly 1.5 tokens per word here |

**The lesson:** a tiny question (8 words) produced about 1,000 tokens of hidden thinking and about 66 tokens of answer. You paid and waited for all of it, even though you only see the answer. Reasoning models do this. `06_tool_use/tools_basics.ipynb` sets `ModelSettings(thinking="minimal")` to reduce it.

### Why cell [10] looks odd

```python
prompt = result.all_messages()[0].parts[1].content
```

It pulls the user prompt back out of the messages (picture B) so cell [11] can count its words. The result is the same string you started with. It is a demonstration that the messages contain what you sent.

---

## 6. Cells [12] and [13] — prompt engineering (under "Basic prompt engineering")

**Prompt engineering** means writing the prompt so the model behaves the way you need. This lecture only introduces it. More comes later.

### Cell [12] — the chef bot

```python
chef_bot = Agent(model, system_prompt=( "あなたは...プロのシェフ...", """次の形式にしてください...""" ))
```

Three things to notice:

1. **`system_prompt` can be a tuple (or list) of strings.** Each string is a separate instruction. Cell [14] does the same with a list.
2. **The prompt asks for a format**: first a 1 to 2 sentence description, then an ingredient list, then numbered steps. The model followed it.
3. **Written in Japanese, answered in Japanese.** The model follows the language of the prompt.

### Cell [13] — read the output critically

You asked for **three Japanese soups** ("和食料理の汁を3つ"). The model gave tom yum (Thai), pho (Vietnamese) and miso soup (Japanese). It followed the **format** perfectly and the **content** only partly.

This is the key point of the whole course:

> A prompt controls **shape** well and **truth** poorly. You cannot trust a good-looking answer. That is why the course has evaluation, LLM judges and hallucination detection later.

Lecture 03 deals with the shape problem more strongly: instead of asking for a format in words, you give a Pydantic model and the output is **validated**.

---

## 7. Cells [14] to [17] — temperature (under "Temperature")

### What temperature is

At each step the model has a list of possible next tokens, each with a probability.

| Temperature | What the model does | Feels like |
| --- | --- | --- |
| **0** | Strongly prefers the most likely token | Predictable, consistent |
| **around 1** | Normal variety | Balanced |
| **high (1.5)** | Gives unlikely tokens more chance | Creative, sometimes odd |

Rule of thumb: **low** temperature for work that needs consistency (extraction, SQL, classification). **Higher** for creative writing.

### What your notebook shows

| Cell | Setting | Result |
| --- | --- | --- |
| [14] | `temperature=0` | "…rabbit named Nibbles jumped high into the air…" |
| [15] | same, run again | A **different** story about a moonlit meadow |
| [16] | `agent.model_settings = ModelSettings(temperature=1.5)` | A third, more elaborate story |
| [17] | same again | A fourth, again different |

**Important:** cells [14] and [15] use temperature 0 and still give different stories. The markdown above them already says it: *even at 0 it is not fully deterministic.* Never write code that assumes the same input gives the same output.

### How the setting is attached

```python
agent = Agent(model, system_prompt=[...], model_settings=ModelSettings(temperature=0))   # cell [14], lines 3-10
agent.model_settings = ModelSettings(temperature=1.5)                                    # cell [16], changes it later
```

`ModelSettings` is a bag of options for the model call. In your version the available keys include `temperature`, `max_tokens`, `top_p`, `seed`, `timeout`, `thinking` and more. You can set them on the agent (as here) so they apply to every run.

---

## 8. Multimodal cells and cell [18] — images and the "thinking" part

### The "Multimodal inputs" and "Do not run" cells — multimodal input

**Multimodal** means the input is more than text, for example an image. The notebook says the model is **text-only**, so an image request is rejected. That is why the "Do not run" cell is written as **markdown**: it is code you can read but not execute with this model.

What the code shows:

```python
user_prompt=[ prompt, BinaryContent(data=image_data, media_type="image/avif") ]
```

`user_prompt` can be a **list** that mixes text and files. `BinaryContent` wraps the raw bytes plus the file type. To use it you must choose a model that accepts images.

### Cell [18] — `result.response.parts[0].content`

```python
print(result.response.parts[0].content)
```

`result.response` is the **last** `ModelResponse` (the `[1]` in picture B). Its `parts[0]` is the `ThinkingPart`. So you are printing the model's private reasoning for the rabbit story, including the drafts it wrote and rejected before the final text. This is the 1,000 hidden tokens from section 5, made visible.

---

## 9. Gotchas

| Gotcha | Why | Fix |
| --- | --- | --- |
| **Names are reused.** Cell [14] creates a **new** `agent`, `prompt` and `result`, replacing the joke bot from cell [2]. | Notebook variables live until you overwrite them | After cell [14], the joke agent is gone. Run top to bottom, or give the new agent another name (like `chef_bot` in cell [12]). |
| **Run order matters.** Cells [3] to [11] need `result` and `agent` from cell [2]. Cell [18] needs a `result` from a run. | A cell only knows what earlier cells ran | Use **Restart, then Run All**. |
| **Outputs are saved in the file.** What you see may come from an older run. | `.ipynb` files store outputs | Re-run before explaining it to someone. |
| **Answers change every run.** | Sampling is random (section 7) | Do not expect identical text. |
| **Image cell fails.** | The model is text-only | Leave the "Do not run" cell as markdown. |
| **Slow or time out.** | Reasoning models think first | Use `timeout=120`, as the notebook does. |

---

## 10. Where this reappears in later lectures

| Idea from 02 | Where it appears next | What changes |
| --- | --- | --- |
| `system_prompt` on the Agent | `05_pydanticai_fastapi_chatbot/chat_agent.py` lines 53 to 56 | The joke-bot idea becomes the chatbot's personality |
| `instructions` (the sibling of `system_prompt`) | `03_.../lecture_pydanticai_pydantic_models.ipynb`, `06_tool_use/agents.py` line 41 | A "job description" for the agent. In 06 it also says "use the tools" and "decline non-weather questions". |
| `result.all_messages()` | `05_.../chat_agent.py` line 88 | Returned to the web page so it can be sent back next time |
| `message_history` | `05_.../chat_agent.py` line 78 to 80, `data_models.py` lines 67 and 86, `frontend.py` lines 41 to 42, 67, 72 | The "stateless model" from picture A, solved: Streamlit stores the history and sends it with every question |
| Tokens and cost | The banner in cell [2]: "see every model and tool call live, with cost" | **Logfire tracing** and monitoring (week 3 of the root `README.md`) |
| Reasoning tokens | `06_tool_use/tools_basics.ipynb` (`ModelSettings(thinking="minimal")`) | Turning thinking down to save tokens and time |
| `ModelSettings` | `04_pydantic_fastapi/src/movies_api.py` lines 29 to 31 | Imported for tuning the model, not used yet |
| "Prompt controls shape, not truth" (cell [13]) | `03_pydanticai_structured_output` | `output_type=` enforces the shape with Pydantic |
| "Model can't know today's weather" (cell [2]) | `06_tool_use` | A weather tool gives the model real data |
| Multimodal input | Not used again yet | |

---

## 11. Glossary (new words in 02)

| Term | Meaning |
| --- | --- |
| **System prompt** | A standing instruction from the developer, placed before the conversation. |
| **User prompt** | The question or input from the user. |
| **Message** | One item in the conversation. A request (sent) or a response (received). |
| **Part** | A piece of a message: system prompt, user prompt, thinking, or text. |
| **Token** | A chunk of text the model reads or writes. Usually less than a word to about a word. |
| **Input / output tokens** | Tokens you send, and tokens the model produces. Billed and limited separately. |
| **Reasoning (thinking) tokens** | Output tokens the model spends thinking before answering. |
| **Context window** | The maximum number of tokens a model can read at once. |
| **Temperature** | A setting for randomness: low is predictable, high is creative. |
| **Deterministic** | Same input always gives the same output. LLMs are not, even at temperature 0. |
| **Prompt engineering** | Writing prompts to get the behaviour you want. |
| **Multimodal** | Accepting more than text, such as images. |
| **Stateless** | Remembers nothing between calls. |

---