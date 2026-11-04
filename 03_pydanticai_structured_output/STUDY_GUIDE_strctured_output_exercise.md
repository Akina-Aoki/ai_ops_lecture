# Study guide: 03 Structured output

## 1. The 30-second version

In lectures 01 and 02 the answer came back as **text**. Text is hard to use in a program. You would have to parse it, and it changes every run.

Lecture 03 fixes this with one idea:

> Describe the shape of the answer you want as a Python class. Pydantic AI makes the model fill in that shape, and Pydantic **checks** it.

- `BaseModel` comes from Pydantic, the data library, not from PydanticAI. PydanticAI just uses it.

- `BaseModel` is a class you inherit from to describe the shape of a record: which `fields` it has, what type each one is, and what `limits` apply. Anything built from that class gets checked automatically.

```python
class EmployeeModel(BaseModel):          # 1. describe the shape
    name: str
    age: int
    ...

result = await agent.run("Give me an IT employee",
                         output_type=EmployeeModel)   # 2. ask for that shape

result.output.salary                      # 3. a real Python object, not text
```

> **Data engineer view:** `EmployeeModel` is a table schema. `output_type=` says "return rows that fit this schema". Pydantic is the schema validation step. It is the same job a data contract does between two systems, here between the LLM and your code.

The "Pydantic" in **Pydantic AI** is this: the part that defines and validates the shape.

---

## 2. The pictures to understand

### Picture A: free text versus structured output

```
Lecture 02 (free text)                         Lecture 03 (structured)

agent.run("Give me an employee")               agent.run("Give me an employee",
        │                                                 output_type=EmployeeModel)
        ▼                                               │
"Johan, 31, is a DevOps engineer in                     ▼
 Stockholm, specializing in CI/CD..."          EmployeeModel(name='Johan', age=31,
        │                                                    salary=45000, role='DevOps')
  a string: to use it you                              │
  must parse it yourself                         result.output.salary  →  45000
```

### Picture B: what happens inside when you pass `output_type`

I checked this in your installed version (pydantic-ai 2.62.0) with a fake model that records what it receives.

```
1. Pydantic builds a JSON schema from your class
      EmployeeModel.model_json_schema()
      → field names, types, descriptions and limits (ge/le/gt/lt)

2. Pydantic AI sends that schema to the LLM as a TOOL named "final_result"
      The LLM is told: "To answer, call final_result with these arguments."
      Plain text answers are not allowed.

3. The LLM replies with a tool call containing JSON
      {"name": "Johan", "age": 32, "salary": 45000, "role": "Data Engineer", ...}

4. Pydantic VALIDATES that JSON against your class
        ├── valid ──────────► you get an EmployeeModel object. Done.
        └── invalid (age=70, limit is 67)
                │
                ▼
5. The validation error is sent back to the LLM, and it tries again
      (Pydantic AI allows 1 retry by default.)
      The test run made 2 model calls: the first failed validation, the second passed.
```

Three things follow from this picture:

| Fact | Consequence |
| --- | --- |
| The schema is the instruction | Field names, `description=` and limits are **part of the prompt**. Good names and descriptions give better answers. |
| It uses the model's tool calling | The model should support **tool use**.  |
| Failures cost extra calls | A retry means more tokens, more time and more money. |

---

## 3. Why this matters for a data engineer

| Without structure | With `output_type` |
| --- | --- |
| Regex over free text | `result.output.salary` |
| Silent bad values (age = "about 30") | Validation error, or an automatic retry |
| Different layout every run | Same fields every run |
| Hard to put in a table | `pd.DataFrame([e.model_dump() for e in employees])` (notebook A cell [17]) |

This is the bridge from "chatting with an AI" to "AI as a step in a data pipeline".

---

## 4. The problem: free text

**Notebook A, cell [2].** Two identical agents, each told in `instructions` to follow a format:

```
name: "Bertil"
age: 40
salary: 35000
role: "IT-supporter"
ort: "Göteborg"
```

The model mostly followed it, and printed `name: "Johan" ...` and `name: "Miriam" ...`. Problems:

- You asked for one data engineer and the second run is a different person. Output changes every run.
- It is still a **string**. To get the salary you would have to split lines and cast to int.
- Nothing stops `salary: "a lot"`.
- The agent is defined twice (lines 1 to 11 and 18 to 28), only to show that the same prompt gives different results. Notice the second prompt has a lowercase `stockholm` and a trailing space. It does not matter to the model.

**Cell [4]** makes the point harder. With only `instructions="Du är expert på att simulera anställda i Sverige"` and no `output_type`, the model replied with a long essay that began by saying it could not give a specific person's contact details. Free text is unpredictable.

---

## 5. Pydantic on its own (no AI yet)

**Notebook A, cell [3]** is the most important cell to understand, because it uses **only Pydantic**, with no model.

```python
class EmployeeModel(BaseModel):
    name: str = Field(description="...")
    age: int = Field(description="ålder från 18 till 67 år", ge=18, le=67)
    salary: int = Field(description="...", ge=30_000, lt=60_000)
    role: str = Field(description="yrke/roll")
    description: str = Field(description="...")

employee1 = EmployeeModel(name="Bertil", age=40, salary=30000, role="IT supporter", description="...")
```

### The parts

| Part | Meaning |
| --- | --- |
| `class EmployeeModel(BaseModel)` | Inheriting `BaseModel` is what gives the class its checking powers. Without it, it is a plain class that checks nothing. |
| `name: str` | A type hint. Pydantic **enforces** it. |
| `Field(...)` | Extra rules and hints for one field |
| `description="..."` | A note for humans **and for the LLM**. It goes into the schema (picture B, step 1). |
| `ge`, `gt`, `le`, `lt` | The limits, see below |

| Argument | Means | Example |
| --- | --- | --- |
| `gt` | greater than | `gt=30_000`: 30000 is **not** allowed |
| `ge` | greater than or equal | `ge=30_000`: 30000 **is** allowed |
| `lt` | less than | `lt=60_000`: 60000 is **not** allowed |
| `le` | less than or equal | `le=67`: 67 **is** allowed |

Cell [3] uses `ge=30_000`, so `salary=30000` passes. Notebook B cell [5] uses `gt=30_000`, so 30000 would fail there.

### What Pydantic does when data is wrong

I ran these:

```python
EmployeeModel(name="B", age="34", ...)      # OK. "34" is converted to the number 34 (safe conversion)
EmployeeModel(name="B", age="hello", ...)   # ValidationError: Input should be a valid integer
EmployeeModel(name="B", age=70, ...)        # ValidationError: Input should be less than or equal to 67
```

Pydantic **converts** when it is safe (`"34"` to `34`) and **rejects** otherwise, with a message that names the field and the rule. That message is exactly what is sent back to the LLM on a retry (picture B, step 5).

> **Data engineer view:** `BaseModel` is the table definition. `Field(ge=..., lt=...)` is a `CHECK` constraint. `description=` is a column comment. The difference: here the comment is also read by the LLM.

---

## 6. Notebook A, cell by cell

| Cell | Code | What it teaches |
| --- | --- | --- |
| (title) | title | |
| [1] | Provider, Model (lecture 01's big cell without the Agent) | Same setup, now with comments removed from most lines |
| [2] | Free-text agent, run twice | The problem (section 4) |
| (markdown) | markdown heading | "Force a structured output using pydantic" |
| [3] | `EmployeeModel`, one object built by hand | Pydantic needs no AI (section 5) |
| [4] | Agent with no `output_type` | Free text is unpredictable |
| [5] | `agent.run(..., output_type=EmployeeModel)` | **The core line.** Result is an `EmployeeModel`. |
| [6] | `employee2 = result.output` | The object is in `result.output`, as in lecture 01 |
| [7] | `type(employee2)` | `__main__.EmployeeModel`. A real instance of **your** class. |
| [8] | `employee2.name + " är cool"` | It is a normal string. You can use it. |
| [9] | `employee2.salary` | `45000`. A number, not text. |
| [10] to [12] | `__dict__` keys, values, loop | Inspecting fields. See the warning below. |
| [13] (under "Simulate many employees") | `output_type=list[EmployeeModel]` | **A list of objects.** Ten at once. |
| [14] and [15] (under "Task - calculate mean salary") | Mean salary with a loop | `47600.0`. Maths works because `salary` is an `int`. |
| [16] and [17] (under "Convert to dataframe") | `model_dump()` then `pd.DataFrame(...)` | Objects become rows |
| [18] | `# df.to_csv("employees.csv", ...)` | Commented out. `employees.csv` is what this once saved. |
| [19] | `df.plot(kind="barh", ...)` | A chart from AI-generated data |

### Notes on the important cells

**Cell [5]** (the whole lecture in one call):

```python
result = await employee_simulator.run("Ge mig en data engineer i stockholm", output_type=EmployeeModel)
```

`output_type` here is passed to `run`, so it applies to this call only. The same agent in cell [4] had no `output_type` and gave an essay. In lecture 04 the type is put on the Agent itself (see section 10).

**Cells [10] to [12]** use `__dict__`. It works, but `__dict__` is an internal Python detail. The proper Pydantic way is `model_dump()` (cell [16]). `model_dump()` also converts nested models into nested dicts, which `__dict__` does not.

**Cell [13]** asks for `list[EmployeeModel]`. In the test, Pydantic AI wrapped the list inside an object `{"response": [...]}` when sending the schema, because the tool arguments must be an object. You never see that. `result.output` is a plain Python list.

**Cells [14] and [15]**: the loop adds up `employee.salary` for each item. That works only because validation guaranteed `salary` is an `int`. In notebook B cell [12] the same task is `mean(employee.salary for employee in result.output)`.

**Language note.** The `Field` descriptions are in Swedish, but the `description` values in the output (cell [5]) came back in English. Descriptions guide the model, they do not force a language.

---

## 7. Notebook B extras: nested models and DuckDB

Notebook B is an earlier version, with the same core and extra material.

| Cell | What it adds |
| --- | --- |
| "Why `BaseModel`?" (markdown) | The best written explanation of why `BaseModel` and `Field` exist (read it) |
| [5] | `EmployeeModel` with `gt=30_000, lt=50_000`, and the first `output_type=` call |
| [10] | `output_type=list[EmployeeModel]` with the limits written into the prompt text too |
| [12] | Mean with `statistics.mean` |
| [14] | **Nested models**: `CvModel` contains lists of `ExperienceModel` and `EducationModel` |
| [15] to [17] | Walking into nested data: `result.output[-1].experiences[0].title` |
| [18] to [23] | Load the nested data into DuckDB with the `dlt` library, then join it back with SQL |

### Nested models (notebook B cell [14])

```
CvModel
 ├── name, age
 ├── experiences: list[ExperienceModel]   (title, company, description, start_year, end_year)
 └── educations:  list[EducationModel]    (title, education_area, school, ...)
```

The LLM now fills a whole **tree** in one answer, and Pydantic validates every level of it. This is how you get one-to-many data (a person with many jobs).

### Why cells [18] to [23] are "optional"

A nested tree does not fit in one flat table. `dlt` splits it into three tables (`cv_entries`, `cv_entries__educations`, `cv_entries__experiences`) linked by `_dlt_id` and `_dlt_parent_id`, and the SQL in cell [23] joins them back. It is a data-engineering pattern: **unnest, load, join**.

These cells have not been run (no execution count), and **`dlt` is not in your `pyproject.toml`**. To try them you need `uv add dlt`.

---

## 8. The exercise, and a bug in it

`structured_output_exercise.ipynb` reads a text file and summarizes it into a structure:

```python
class Person(BaseModel):
    name: str
    organisation: str = Field("company or organisation")
    subject: str = Field("the subject the person has")

class Resilience(BaseModel):
    title: str = Field("pick suitable headline from the input, don't hallucinate")
    description: str = Field("3-5 sentences summary of the content")
    contributors: list[Person]
    contact: str = Field("contact person for this event")
```

### The bug: `Field("text")` is not a description

The first argument of `Field` is the **default value**, not the description. I ran it:

```python
class Bad(BaseModel):
    organisation: str = Field("company or organisation")

Bad()   # organisation='company or organisation'
```

What this does in your exercise (lines 7, 8, 11, 12 and 14 of its cell [1]):

| Effect | Why it matters |
| --- | --- |
| The LLM gets **no hint** about the field | The hint text is not in the schema as a description |
| The field is **optional** | It has a default, so the model may skip it |
| If skipped, the field is silently filled with the hint text | You get `organisation='company or organisation'` and think it is real data |

**Fix:** use the keyword. `Field(description="company or organisation")`.

### Other things to know about the exercise

- It reads `raw_text.txt`, which is **not in the folder**, so cell [1] will raise `FileNotFoundError`. You need to supply the text.
- `from model import nvidia_model` works because `model.py` is in the same folder.
- It uses the bigger model `nvidia/nemotron-3.5-super-vl-120b-a12b` through the helper.
- `instructions` tells the model to write in Swedish and "summarize according to the output type". The output type is the format. `instructions` is the job.

### `model.py`

```python
def nvidia_model(model_name: str) -> OpenAIChatModel:
    return OpenAIChatModel(model_name=model_name, provider=OpenAIProvider(base_url=..., api_key=os.environ["NVIDIA_API"]))
```

It is lecture 01's big code cell (cell [2] in the 01 guide) turned into a function, so you can write `Agent(model=nvidia_model("..."))` and choose the model name per agent. Notebook B cell [2] uses it but its import is commented out (`# from Model import nvidia_model`), and the capital M would not match the file name `model.py` anyway.

---

## 9. Gotchas

| Gotcha | Why | Fix |
| --- | --- | --- |
| **Valid is not true.** | Validation checks shape and ranges, not facts. A 32-year-old "Johan Karlsson" is valid whether or not he exists. | Never assume a validated answer is correct. This is why evaluation comes later. |
| **`Field("text")`** (exercise) | First argument is the default | `Field(description="text")` |
| **`raw_text.txt` missing** (exercise) | The file is not in the repo | Add the text file |
| **Notebook B cell [2] `NameError`** | Uses `nvidia_model`, import is commented out | `from model import nvidia_model` |
| **Notebook B cell [7] says `list`** | Its saved badge ([16]) is later than cells [10] and [14] (saved as [14] and [15]), which both produce lists. It was run out of order. | Restart, Run All. Cell [7] would then say `EmployeeModel`. |
| **`dlt` not installed** (notebook B) | Not in `pyproject.toml` | `uv add dlt` |
| **Model without tool support** | Structured output uses a tool call (picture B) | Use a model that supports tool use |
| **`gt` vs `ge`** | `gt` excludes the boundary | Choose deliberately |
| **Retries cost money and time** | Failed validation means another model call | Write clear descriptions to reduce failures |
| **Stale README** | `README.md` says the code uses OpenRouter; your notebooks use Nvidia | Ignore the OpenRouter note |

---

## 10. Where this reappears in later lectures

| Idea from 03 | Where it appears next | What changes |
| --- | --- | --- |
| `BaseModel` + `Field(ge, lt, ...)` | `04_pydantic_fastapi/src/data_models.py` lines 25 to 43: `Movie` with `rating: int = Field(gt=0, lt=6)` | Same idea, now a movie record |
| `output_type=` | `04_.../movies_api.py` lines 52 and 81 | Set on the Agent at line 52 (applies to every run) and again at line 81 |
| `result.output` is a real object | `movies_api.py` lines 83 to 92 | `movie.title`, `movie.year`... go into a DuckDB `INSERT`. This is "LLM to typed row to database" in four lines. |
| Pydantic validating **incoming** data | `04_.../data_models.py`: `Prompt` | FastAPI uses a Pydantic model to validate the request, with an automatic error (422) |
| One model, two jobs | `Movie` is both the AI's `output_type` and the API's response | The shape is defined **once** and reused |
| `BaseModel` for messages | `05_.../data_models.py` lines 47 and 75: `ChatRequest`, `ChatResponse` | The data contract between the web page and the API |
| `list[...]` of models | `05_.../data_models.py` lines 67 and 86: `message_history: list[ModelMessage]` | The lecture 02 conversation list, now validated |
| `model_dump()` | Anywhere you turn objects into rows or JSON | |
| `nvidia_model()` helper | `06_tool_use/model.py` | Copied there, with a docstring that explains why each folder needs its own copy |
| "Schema from a class" | `06_tool_use` | Tools are the same idea. Python function signatures and docstrings become the schema the LLM sees. |
| Valid is not true | Evaluation, LLM judge, hallucination detection (root `README.md`, weeks 3 to 4) | Checking the **content**, not just the shape |

---

## 11. Glossary (new words in 03)

| Term | Meaning |
| --- | --- |
| **Pydantic** | A Python library that defines data shapes with classes and validates data against them. |
| **`BaseModel`** | The Pydantic class you inherit from to get validation. |
| **Field** | Extra rules and hints for one attribute: `Field(description=..., ge=..., lt=...)`. |
| **Validation** | Checking that data fits the rules. Fails with `ValidationError`. |
| **Coercion** | Safe automatic conversion, such as `"34"` to `34`. |
| **Schema / JSON schema** | A machine-readable description of a shape. This is what the LLM receives. |
| **Structured output** | An LLM answer that fits a schema instead of being free text. |
| **`output_type`** | The argument that sets the schema for the answer. |
| **Nested model** | A model that has other models (or lists of them) as fields. |
| **`model_dump()`** | Turns a model object into a plain dict. |
| **Retry** | The automatic second attempt when the answer fails validation. |
| **Tool call** | The LLM requesting that a function be run with arguments. Here the "function" is the answer itself (`final_result`). |

---

## 12. Check yourself

Try to answer before opening each one.

<details><summary>1. What problem does <code>output_type</code> solve?</summary>

Free-text answers are unpredictable and hard to use in code. `output_type` makes the model reply in a fixed shape that Pydantic validates, so you get a real Python object.
</details>

<details><summary>2. How does the LLM know which fields to produce?</summary>

Pydantic turns your class into a JSON schema (field names, types, descriptions, limits). Pydantic AI sends it as a tool called `final_result`, and the model answers by calling that tool.
</details>

<details><summary>3. The model returns <code>age = 70</code> but the limit is <code>le=67</code>. What happens?</summary>

Pydantic raises a validation error. Pydantic AI sends the error back to the model and lets it retry (one retry by default). If it still fails, you get an error instead of a bad value.
</details>

<details><summary>4. What is the difference between <code>gt=30_000</code> and <code>ge=30_000</code>?</summary>

`gt` is "greater than" so 30000 is rejected. `ge` is "greater than or equal" so 30000 is accepted.
</details>

<details><summary>5. Why is <code>Field("company or organisation")</code> wrong?</summary>

The first argument of `Field` is the default value. It does not describe the field to the LLM, and it makes the field optional, so a missing value is silently replaced by that text. Use `Field(description="...")`.
</details>

<details><summary>6. Does validation prove the answer is correct?</summary>

No. It proves the answer has the right shape and the values are inside the rules. A made-up person with a valid age still passes. Checking truth needs evaluation, which comes later.
</details>

<details><summary>7. Why use <code>model_dump()</code> and not <code>__dict__</code>?</summary>

`model_dump()` is the supported API and also converts nested models. `__dict__` is an internal detail.
</details>

<details><summary>8. How do you get ten employees instead of one?</summary>

Use `output_type=list[EmployeeModel]` and ask for ten in the prompt. `result.output` is then a normal Python list of `EmployeeModel` objects.
</details>

<details><summary>9. Why does notebook B need <code>dlt</code> for the last cells?</summary>

A nested tree (CV with many jobs) does not fit in one flat table. `dlt` unnests it into linked tables in DuckDB, and SQL joins them back. It is optional, and `dlt` is not installed yet.
</details>

---

## 13. My questions

Add questions here as you read, then ask Claude to answer them in this file.

- [ ]
