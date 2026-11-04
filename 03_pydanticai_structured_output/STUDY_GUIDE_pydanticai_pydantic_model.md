# Study guide: `pydanticai_pydantic_model.ipynb`

A beginner walkthrough of **one notebook**, cell by cell, written for a data engineer. Keep it open next to the notebook in VS Code.

- Wider background for this folder (the other two notebooks, the exercise bug) is in [STUDY_GUIDE_strctured_output_exercise.md](STUDY_GUIDE_strctured_output_exercise.md). The sibling notebook `lecture_pydanticai_pydantic_models.ipynb` has its own guide: [STUDY_GUIDE_lecture_pydanticai_pydantic_models.md](STUDY_GUIDE_lecture_pydanticai_pydantic_models.md).
- **Cell numbers.** VS Code shows a badge like `[3]` to the left of each **code** cell after it runs. In this guide `[3]` means the **3rd code cell from the top**, which is the badge you get after **Restart, then Run All**. Markdown cells have no badge, so I call them by their heading. This notebook has 29 cells: 23 code and 6 markdown. Line numbers are lines **inside** the cell.
- **Warning: the badges saved in this file are out of order** (see the map below). Do not match by the saved badge. Match by how the cell starts.
- Everything here that says "I tested" was run offline with a fake model, because I cannot call your Nvidia key. Nothing in your notebook or project was changed.

---

## Cell map

| Guide label | Type | How the cell starts | Badge saved in the file today |
| --- | --- | --- | --- |
| title | markdown | `# Pydantic AI together with Pydantic Models` | none |
| **[1]** | code | `# Agent: the object that sends...` imports and `model` | [6] |
| **[2]** | code | `# from Model import nvidia_model` (will fail, see below) | [7] |
| **[3]** | code | `# this is quite fast model...` then `agent = Agent(model=model)` | [8] |
| **[4]** | code | `print(result.output)` | [9] |
| "Why `BaseModel`? / Why `Field`?" | markdown | `## Why BaseModel?` | none |
| **[5]** | code | `class EmployeeModel(BaseModel):` | [10] |
| **[6]** | code | `result.output` | [11] |
| **[7]** | code | `type(result.output)` | **[16]** (run late) |
| **[8]** | code | `result.output.name, result.output.age, ...` | [12] |
| **[9]** | code | `result.output.model_dump()` | [13] |
| **[10]** | code | `output_type=list[EmployeeModel]` (ten employees) | [14] |
| **[11]** | code | `result.output` | [15] |
| "Task: Calculate mean salary" | markdown | `## Task: Calculate mean salary` | none |
| **[12]** | code | `from statistics import mean` | **[17]** |
| "Task: Convert to Pandas DataFrame" | markdown | `## Task: Convert to Pandas DataFrame` | none |
| **[13]** | code | `import pandas as pd` | **[18]** |
| "CV model" | markdown | `# CV model - a more complex and nested model` | none |
| **[14]** | code | `class ExperienceModel(BaseModel):` ... `CvModel` | [15] |
| **[15]** | code | `result.output[-1]` | [16] |
| **[16]** | code | `result.output[-1].name` | [17] |
| **[17]** | code | `result.output[-1].experiences[0].title, ...` | [18] |
| "(optional) Postprocessing" | markdown | `# (optional) Postprocessing - load into duckdb` | none |
| **[18]** | code | `import dlt` | not run |
| **[19]** | code | `import duckdb` / `desc` | not run |
| **[20]** | code | `cv_entries` | not run |
| **[21]** | code | `educations` | not run |
| **[22]** | code | `experiences` | not run |
| **[23]** | code | `duckdb.sql("""SELECT cv.name, ...` | not run |

The saved badges go 6, 7, 8, 9, 10, 11, **16**, 12, 13, 14, 15, **17, 18**, 15, 16, 17, 18. Cells were run out of order, and the numbers 15 to 18 each appear twice. That is why cell [7] shows `list` in your file (explained in its section).

---

## 1. Five ideas before the cells

If you only have five minutes, read this section. Everything else is detail.

### Idea 1: an LLM only returns text

You ask, it answers with a string. A string is hard to use in code. If you want the salary as a number you have to find it in the text and convert it yourself, and the next answer may be worded differently.

### Idea 2: `BaseModel` is the blueprint of a record

```python
class EmployeeModel(BaseModel):
    name: str
    age: int
    salary: int
    position: str
```

> **Data engineer view:** this is a `CREATE TABLE employee (name TEXT, age INT, salary INT, position TEXT)`. Each field is a column. The class name is the table name.

An object made from this class is **checked when it is created**. `age="hello"` is rejected. `age="34"` is quietly converted to `34`. Without `BaseModel` the class would be a plain Python class that accepts anything.

### Idea 3: `Field` adds rules and hints

```python
salary: int = Field(description="salary should be between 30k and 50k", gt=30_000, lt=50_000)
```

| Part | Meaning | SQL cousin |
| --- | --- | --- |
| `description="..."` | A hint. It is sent to the LLM so it knows what to put here. | `COMMENT ON COLUMN` |
| `gt=30_000` | Greater than 30000 (30000 itself is **rejected**) | `CHECK (salary > 30000)` |
| `lt=50_000` | Less than 50000 (50000 itself is **rejected**) | `CHECK (salary < 50000)` |

I tested the edges: 30000 and 50000 are rejected, 30001 and 49999 are accepted. (`ge` and `le` would include the edges.) `30_000` is just `30000` with an underscore for readability.

### Idea 4: `output_type` makes the agent answer in that shape

```python
result = await agent.run("Give me an IT employee", output_type=EmployeeModel)
```

Instead of text you get an `EmployeeModel` object. Inside, three things happen:

```
1. Pydantic turns EmployeeModel into a JSON schema (field names, types, limits, descriptions)
2. Pydantic AI sends that schema to the LLM as a "tool" named final_result
3. The LLM answers by "calling" that tool with JSON
4. Pydantic validates the JSON
      ok      -> you get an EmployeeModel object
      not ok  -> the error is sent back to the LLM and it retries once
```

I tested step 4: a fake LLM first answered `salary=99999`, Pydantic rejected it, the agent asked again, and the second answer passed. That is two model calls for one `agent.run`.

This is why the comment in cell [3] says the model "also has tool use". Structured output rides on tool calling, so the model must support tools. There are other output modes in Pydantic AI, but this notebook uses the default.

### Idea 5: classes can contain classes (nested models)

A `CvModel` has a list of `ExperienceModel`. That is a one-to-many relationship, like a `person` table and a `job` table. The LLM fills the whole tree in one answer and Pydantic checks every level. Cells [14] to [23] are about this, and about flattening that tree back into tables.

---

## 2. The story of the notebook

```
Stage 1  cells [1]-[4]    Plain question, plain text answer       -> a string you cannot trust
Stage 2  cell  [5]        Describe the answer as a class          -> output_type=EmployeeModel
Stage 3  cells [6]-[9]    Use the object                          -> .name, .salary, model_dump()
Stage 4  cells [10]-[13]  Ask for many, compute, DataFrame        -> list of objects -> table
Stage 5  cells [14]-[17]  A tree: CV with jobs and degrees        -> nested models
Stage 6  cells [18]-[23]  Flatten the tree into tables (optional) -> dlt -> DuckDB -> SQL join
```

Each stage fixes a weakness in the one before. Read the notebook as that chain.

### The data flow

```
prompt + EmployeeModel ──► LLM ──► JSON ──► Pydantic validates ──► EmployeeModel object
                                                                         │
                                                       list[EmployeeModel] (cell [10])
                                                                         │
                                         employee.model_dump() for each  │ (cell [13])
                                                                         ▼
                                                   list of dicts ──► pd.DataFrame
```

---

## 3. Variable tracker (read this when something breaks)

Notebooks keep every name alive until you overwrite it. This notebook reuses `result` four times.

| Name | Created in | Overwritten in | What it holds at the end |
| --- | --- | --- | --- |
| `model` | [1] | never | The Nvidia model object (lecture 01) |
| `employee_simulator` | [2] | never | Only exists if [2] succeeded. **Nothing uses it afterwards.** |
| `agent` | [3] | never | Agent with no instructions. Used by every later call. |
| `result` | [3] | **[5], [10], [14]** | Result of the most recent `agent.run(...)` |
| `EmployeeModel` | [5] | never | Your blueprint class |
| `mean_salary` | [12] | never | `44500` |
| `pd` | [13] | never | The pandas module |
| `ExperienceModel`, `EducationModel`, `CvModel` | [14] | never | The CV blueprints |
| `pipeline`, `info` | [18] | never | dlt objects |
| `conn`, `desc`, `cv_entries`, `educations`, `experiences` | [19] | never | DuckDB connection and three DataFrames |

### The order matters

Which `result` a cell sees depends on the **last** cell that set it:

| Cells | They expect `result` to be | Set by |
| --- | --- | --- |
| [4] | text | [3] |
| [6], [7], [8], [9] | one `EmployeeModel` | [5] |
| [11], [12], [13] | a list of `EmployeeModel` | [10] |
| [15], [16], [17], [18] | a list of `CvModel` | [14] |

Example: run [14] and then [12] again. `result.output` is now a list of CVs, and `employee.salary` raises `AttributeError` because a `CvModel` has no `salary`. Run the notebook top to bottom and this does not happen.

---

## 4. Cell by cell

### Cell [1]: set up the model (this is lecture 01 again)

| Lines | What | Where you learned it |
| --- | --- | --- |
| 2 to 12 | Imports | Lecture 01 |
| 16 | `load_dotenv()` reads `.env` | Lecture 01 |
| 20 to 26 | `OpenAIChatModel(name, provider=OpenAIProvider(base_url=..., api_key=...))` | Lecture 01 |

Nothing new. No agent is created here. Model name: `nvidia/nemotron-3.5-lightning-30b-a3b`.

> **Data engineer view:** `provider` is the connection string, `model` is the table you query.

---

### Cell [2]: a leftover cell that will fail

```python
# from Model import nvidia_model         # line 1, commented out
employee_simulator = Agent(
    model = nvidia_model("nvidia/nemotron-3.5-super-vl-120b-a12b"),   # line 5
    instructions = "You are an expert at simulating employment in Sweden. Simulate it in this format."
    """ name: "Bertil", age: 40, ... """   # lines 7 to 13
)
```

| Lines | What it does |
| --- | --- |
| 1 | The import is **commented out**. |
| 5 | Calls `nvidia_model(...)`, a helper from `model.py` in this folder. Since the import is off, Python has never heard of it. |
| 6 to 13 | `instructions`: two strings written next to each other. Python glues adjacent strings together, so this is one text that includes a format example. |

**What happens:** on a fresh kernel this raises `NameError: name 'nvidia_model' is not defined`. In VS Code a **Run All stops at the first cell that errors**, so cells [3] onwards would not run. To follow the notebook you can run cells one at a time and skip [2], or run `from model import nvidia_model` first (lowercase `model`, the file is `model.py`).

**Why it is harmless:** nothing later uses `employee_simulator`. Cell [3] builds a new agent called `agent`. This cell is a leftover from an earlier version where the format was explained in words. That is the "before" idea that `output_type` replaces.

**What `model.py` does:** it is the lecture 01 setup wrapped in a function so you can write `nvidia_model("any-model-name")`.

---

### Cell [3]: the first call, plain text

```python
agent = Agent(model=model)                                                         # line 2
result = await agent.run("Give me an IT employee working in Sweden, shortly.", timeout = 60)   # line 4
result                                                                              # line 5
```

| Line | Meaning |
| --- | --- |
| 1 | Comment: this model has tool use, which structured output needs (Idea 4). |
| 2 | An agent with a model and nothing else. No instructions, no tools, no `output_type`. |
| 4 | `await` waits for the answer. It works at the top level because Jupyter allows it. `timeout = 60` means: give up if the whole run takes more than **60 seconds**. I checked the docstring: it is in seconds and covers the whole run. |

**The big box of ASCII art in the output** is a startup banner from Pydantic AI (version 2.62.0 in your file). It says `tools: 0`, `observability: off`. It is harmless. It points to **Logfire**, the tracing tool you meet in a later lecture. You can hide it with the environment variable `PYDANTIC_AI_NO_BANNER=1`.

**The answer:** `AgentRunResult(output="Johan, 31, is a DevOps engineer in Stockholm, ...")`. `output` is a **string**. A sentence. Running it again gives another person and another sentence.

---

### Cell [4]: print the text

```python
print(result.output)
```

`result.output` is the answer. `result` itself is a wrapper (`AgentRunResult`) that also holds messages and token counts. You print the sentence. Can you get Johan's age out of it as a number? Only by parsing the text yourself. That is the problem the next cell solves.

---

### The "Why `BaseModel`? / Why `Field`?" cell (markdown)

Your own best explanation, so reread it. Two points to keep in mind:

- It says the LLM returns text, and `BaseModel` turns that text into a checked Python object.
- It uses exactly the table analogy: `BaseModel` is the schema, `Field` is the constraints and column comments.

---

### Cell [5]: the core of the lecture

```python
class EmployeeModel(BaseModel):                                   # line 5
    name: str                                                     # line 12
    age: int                                                      # line 13
    salary: int = Field(description="...", gt=30_000, lt=50_000)  # line 14
    position: str                                                 # line 15

result = await agent.run("Give me an IT employee working in sweden", output_type=EmployeeModel)   # lines 25 to 27
```

| Lines | Code | Meaning |
| --- | --- | --- |
| 3 | `from pydantic import BaseModel, Field` | The two tools you need |
| 5 | `class EmployeeModel(BaseModel):` | A new record shape. The name is yours. `(BaseModel)` gives it checking powers. |
| 6 to 11 | the triple-quoted text | A **docstring**: documentation for you, and it is also sent to the LLM (see below). |
| 12, 13, 15 | `name: str`, `age: int`, `position: str` | Plain fields. Type only, no extra rules. |
| 14 | `salary: int = Field(...)` | A field with a hint and limits (Idea 3) |
| 17 | comment | The `description` is sent to the LLM as a hint |
| 25 to 27 | `agent.run(..., output_type=EmployeeModel)` | The only difference from cell [3]. Answer in this shape. |

**What the output showed:**

```
AgentRunResult(output=EmployeeModel(name='Anna Lindberg', age=30, salary=45000, position='Software Engineer'))
```

Compare with cell [3]. There `output=` held a string. Here it holds an `EmployeeModel(...)`.

**What the LLM actually received** (I tested this with a fake model):

```json
{"properties": {"name": {"type": "string"},
                "age": {"type": "integer"},
                "salary": {"description": "salary should be between 30k and 50k, ...",
                           "exclusiveMinimum": 30000, "exclusiveMaximum": 50000, "type": "integer"},
                "position": {"type": "string"}},
 "required": ["name", "age", "salary", "position"], "title": "EmployeeModel", "type": "object"}
```

Three things to see:

1. `name`, `age` and `position` have **no description**. The model has only the field name and type to go on. Good names matter.
2. The limits arrive as `exclusiveMinimum` and `exclusiveMaximum`, so the LLM is told the numbers directly.
3. The class docstring (lines 6 to 11) is not inside this JSON, but it is **also sent**. I tested it: for `output_type=EmployeeModel` the docstring becomes the **description of the `final_result` tool**, and for `list[EmployeeModel]` it sits inside the schema next to the class. So the docstring is not only for you. The model reads it too. Write it as an instruction, not as a note to yourself.

**Two small things in the code:**

- The comment on line 17 sits inside the class but after the fields. It is only a comment.
- The `description` on the salary field says "the more senior the position, the higher salary". That is an instruction to the model. Pydantic does not enforce it, only the `gt` and `lt` numbers are enforced.

---

### Cells [6] to [9]: it is a real object

| Cell | Code | Output | What it shows |
| --- | --- | --- | --- |
| [6] | `result.output` | `EmployeeModel(name='Anna Lindberg', age=30, salary=45000, position='Software Engineer')` | The object lives in `.output` |
| [7] | `type(result.output)` | see below | The type of the object |
| [8] | `result.output.name, result.output.age, result.output.salary` | `('Anna Lindberg', 30, 45000)` | Dot access to each field |
| [9] | `result.output.model_dump()` | `{'name': 'Anna Lindberg', 'age': 30, ...}` | Convert to a plain dict |

**Cell [7] shows `list` in your saved file. That is a trap.** The saved badge on [7] is [16], while [10] is [14] and [11] is [15]. So [7] was run after [10], when `result` already held a list of ten employees, and printed `list`. On a clean **Restart + Run All** it prints `__main__.EmployeeModel`, which means "an instance of the class you defined in this notebook". Same cause as the `result` table in section 3.

**Cell [8]:** `.salary` is the number `45000`, not the text `"45000"`. This is the payoff. Compare it to cell [3], where the age was inside a sentence.

**Cell [9], `model_dump()`:** turns the object into a plain dict (`str`, `int`, ...). Pandas, JSON and databases all understand dicts, but not Pydantic objects. You will use it in cell [13].

**Try in a scratch cell:** `result.output["name"]` raises `TypeError: 'EmployeeModel' object is not subscriptable`. It is an object, not a dict. Use `.name`.

---

### Cell [10]: ten employees at once

```python
result = await agent.run(
    "Give me ten employees in AI and data engineering fields, so the roles can vary, salary must be between 30000 and 50000",
    output_type=list[EmployeeModel],
)
```

`list[EmployeeModel]` means "a list where every item fits `EmployeeModel`".

**What happens inside:** Pydantic AI wraps the list in an object with one key called `response`, because a tool's input must be an object. The model fills `response` with an array. Every item is validated by `EmployeeModel`. I tested this: with a fake model the result was a normal `list`.

**What the output showed:** ten people: Alice Johnson (Machine Learning Engineer, 45000), Bob Smith (Data Scientist, 48000), Cara Lee, Dan King, Eve Martinez, Frank Adams, Grace White, Hank Black, Ivy Green, Jack Brown. Salaries range from 40000 to 49000, inside `gt=30_000, lt=50_000`.

**Why the prompt repeats the salary range.** The limit is already in the class. Saying it in the prompt as well makes it likelier the first answer passes. Otherwise Pydantic rejects it and you pay for a retry (an extra model call).

**Watch out:** "ten" is only a request. `list[EmployeeModel]` does not mean "exactly 10". The model could return 8 or 12 and Pydantic would accept it. Check `len(result.output)` if the count matters.

> **Data engineer view:** `list[EmployeeModel]` is a table. `EmployeeModel` is one row.

---

### Cell [11]: look at the list

`result.output` shows ten `EmployeeModel(...)` lines. Each item is a real object, not a dict.

---

### The "Task: Calculate mean salary" cell (markdown), then cell [12]

```python
from statistics import mean
mean_salary = mean(employee.salary for employee in result.output)
print(mean_salary)
```

| Line | Meaning |
| --- | --- |
| 1 | `statistics.mean` is from Python's standard library. No install needed. |
| 3 | `employee.salary for employee in result.output` loops over the list and takes each salary. `mean(...)` averages them. |
| 5 | Prints `44500`. |

I checked the arithmetic: 45000 + 48000 + 42000 + 46000 + 44000 + 47000 + 43000 + 41000 + 40000 + 49000 = 445000, and 445000 / 10 = 44500.

**Why this works:** `employee.salary` is guaranteed to be an `int` because validation checked it. With the free text from cell [3] you would first have to find and convert the number. It also uses the last `result` from cell [10] (see section 3).

---

### The "Task: Convert to Pandas DataFrame" cell (markdown), then cell [13]

```python
import pandas as pd
pd.DataFrame([employee.model_dump() for employee in result.output])
```

Read the second line from the inside out:

```
result.output                                    list of 10 EmployeeModel
[employee.model_dump() for employee in ...]      list of 10 dicts          (one dict = one row)
pd.DataFrame( ... )                              table: name, age, salary, position
```

A **list of dicts** is the standard "records" shape that `pd.DataFrame` understands. The output is a 10-row table with columns `name`, `age`, `salary`, `position`.

> **Data engineer view:** the field names of `EmployeeModel` became the column names, and the types became the column types. The class was the schema of the table.

This cell does not save the table in a variable (no `df = ...`). It only displays it. Add `df =` in front if you want to reuse it.

---

### The "CV model" cell (markdown), then cell [14]

```python
class ExperienceModel(BaseModel):    # a job:    title, company, description, start_year, end_year
class EducationModel(BaseModel):     # a degree: title, education_area, school, description, start_year, end_year
class CvModel(BaseModel):
    name: str
    age: int
    experiences: list[ExperienceModel]     # line 21
    educations: list[EducationModel]       # line 22

result = await agent.run(
    "Create 5 fake persons that is applying for a data engineering job. They should have 2-5 previous job experiences",
    output_type=list[CvModel],
)
```

The tree:

```
list[CvModel]               (5 people)
  └── CvModel
        ├── name, age
        ├── experiences: list[ExperienceModel]    (several jobs)
        └── educations:  list[EducationModel]     (several degrees)
```

> **Data engineer view:** this is a parent table (`cv`) with two child tables (`experience`, `education`), each linked to the parent. In JSON it is one nested document. In a database you normally normalize it into three tables.

| Lines | Meaning |
| --- | --- |
| 1 to 6 | One job. Five fields, no `Field(...)`, so no rules and no hints. |
| 9 to 15 | One degree. |
| 18 to 22 | One person with lists of jobs and degrees. |
| 25 to 28 | One call, `output_type=list[CvModel]`. The LLM fills the whole tree. |

**I tested what the model is sent:** the schema contains `CvModel`, `ExperienceModel` and `EducationModel` as definitions, and every level is validated.

**What is not checked** (I tested these too, all accepted):

- `end_year` earlier than `start_year`. Pydantic only checks that both are integers.
- The "2-5 job experiences" from the prompt. A person with 3 jobs passes, and so would one with 0 or 9.
- Whether the school or the company exists.

If you want rules like these you add `Field(ge=..., le=...)` on the field, or a validator. That is not in this notebook. This cell has no output, because it ends with an assignment.

---

### Cells [15] to [17]: walking into the tree

| Cell | Code | Output | What it shows |
| --- | --- | --- | --- |
| [15] | `result.output[-1]` | `CvModel(name='Hank Rogers', age=33, experiences=[...], educations=[...])` | The **last** of the five people (`-1` = last item) |
| [16] | `result.output[-1].name` | `'Hank Rogers'` | A top-level field |
| [17] | `result.output[-1].experiences[0].title, result.output[-1].experiences[1].title` | `('Database Administrator', 'Data Engineer')` | Into the list, then into the item |

Read the chain in cell [17] left to right:

```
result.output     -> list of CvModel
[-1]              -> the last CvModel
.experiences      -> list of ExperienceModel
[0]               -> the first job
.title            -> 'Database Administrator'
```

Hank Rogers has four jobs and one degree in your saved output. That shows the one-to-many shape: four rows for jobs, one for degrees.

---

### The "(optional) Postprocessing" cell (markdown)

The author says it is optional: a way to unnest the data and store it, with `dlt` into DuckDB, or you could use a NoSQL store like MongoDB instead.

**None of cells [18] to [23] have been run in your file** (no badge, no outputs), and there is no `cv.duckdb` in the folder.

**Before you try [18]:** `dlt` is **not installed** (I checked your venv) and is not in `pyproject.toml`. Cell [18] will fail with `ModuleNotFoundError: No module named 'dlt'` until you add it. The dlt docs call the extra for DuckDB `dlt[duckdb]`, so the command is probably `uv add "dlt[duckdb]"`. I did not install it, because it changes your project.

---

### Cell [18]: load the nested data with `dlt`

```python
import dlt
pipeline = dlt.pipeline(pipeline_name="cv_duckdb", destination=dlt.destinations.duckdb("cv.duckdb"), dataset_name="staging")
info = pipeline.run(data=[result.output], loader_file_format="jsonl", table_name="cv_entries")
print(info)
```

`dlt` ("data load tool") is a library that loads Python data into a database.

| Lines | Meaning |
| --- | --- |
| 3 to 7 | Configure the pipeline: a name, a destination (a **DuckDB file** called `cv.duckdb`), and a schema name `staging` |
| 9 to 11 | Run it: load the data into a table called `cv_entries`. `jsonl` is the intermediate file format. |
| 13 | Print a summary of the load |

**What dlt does with nested data:** it keeps the top-level fields in `cv_entries` and moves each nested list into its own **child table**. The notebook's own later cells use these names: `cv_entries__educations` and `cv_entries__experiences`, linked back with `_dlt_id` (the parent row id) and `_dlt_parent_id` (on the child, pointing at the parent).

> **Data engineer view:** this is automatic normalization. You hand over one nested document, you get three linked tables, with no hand-written `INSERT` or schema.

**Two things I could not check, because `dlt` is not installed:**

1. Line 10 passes `[result.output]`. But `result.output` is already a list of 5 people, so this is a list inside a list. If `dlt` complains, or the tables look odd, try `data=result.output` first.
2. `cv.duckdb` is created in the notebook's folder, and your `.gitignore` does not ignore `*.duckdb`. Git would show it as a new file.

---

### Cells [19] to [22]: read the tables back

```python
import duckdb
with duckdb.connect("cv.duckdb") as conn:
    desc = conn.sql("desc;").df()
    cv_entries  = conn.sql("FROM staging.cv_entries").df()
    educations  = conn.sql("FROM staging.cv_entries__educations").df()
    experiences = conn.sql("FROM staging.cv_entries__experiences").df()
desc
```

| Lines | Meaning |
| --- | --- |
| 3 | Open the DuckDB file. `with` closes it afterwards. |
| 4 | `desc;` lists the tables in the database. |
| 5 to 7 | `FROM staging.<table>` is DuckDB shorthand for `SELECT * FROM`. `.df()` turns the result into a pandas DataFrame. |
| 9 | Show the table list |

Cells [20], [21], [22] only display `cv_entries`, `educations` and `experiences` so you can see them. The DataFrames stay available after the `with` block closes the connection.

---

### Cell [23]: join the pieces back (read this slowly)

```sql
SELECT cv.name, cv.age, ex.company, ex.description AS experience_description,
       ex.start_year AS experience_start_year, ex.end_year AS experience_end_year,
       e.title, e.education_area, e.school, e.start_year AS education_start_year, e.end_year AS education_end_year
FROM cv_entries cv
LEFT JOIN educations e   ON cv._dlt_id = e._dlt_parent_id
LEFT JOIN experiences ex ON cv._dlt_id = ex._dlt_parent_id
```

**How does DuckDB find `cv_entries`?** There is no such table in the DuckDB file under that name. It is the **Python variable** from cell [19]. DuckDB can query a pandas DataFrame by its variable name (a "replacement scan"). I tested it: it works with DataFrames in your notebook. That is why this cell uses `duckdb.sql(...)` and not `conn.sql(...)`.

**Two things worth knowing about this query** (I tested both with tables shaped like dlt's):

1. **Row multiplication.** The parent is joined to two child tables at once. Each job is paired with each degree. A person with 3 jobs and 2 degrees gives **6 rows**, not 5. In my test, 5 jobs and 3 degrees in total became 8 rows. This is the classic "fan-out" in a join. If you then compute `COUNT(*)` or sum something, you double-count.
2. **Which `title`?** The query selects `e.title`, the **degree** title. The job title `ex.title` is not selected, and the job description is named `experience_description`. So the output has a column called `title` that is a degree. Aliasing it as `education_title` and adding `ex.title AS experience_title` would make it unambiguous.

The `LEFT JOIN` keeps a person even if they have no jobs or no degrees.

I am only describing this, not changing your notebook.

---

## 5. How this connects to the other lectures

| Idea in this notebook | Where it comes back |
| --- | --- |
| Provider and Model (cell [1]) | Lecture 01, then every later lecture |
| `agent.run(...)` and `result.output` | Lecture 01 |
| `output_type` passed to `run` | Lecture 04 puts `output_type` on the `Agent` itself |
| `BaseModel` and `Field` | Lecture 04: `Movie` and `Prompt`. Lecture 05: `ChatRequest` and `ChatResponse` |
| `final_result` tool (Idea 4) | Lecture 06: your own tools use the same mechanism |
| `model_dump()` | Lecture 04: turning a `Movie` into a row for DuckDB |
| `employees.csv` | Not used by this notebook. It belongs to the sibling notebook, which has a commented-out `to_csv` line. |
| `model.py` in this folder | Cell [2] was meant to use it. |
| `timeout` | A safety net when a model is slow. |
| Banner / "observability: off" | The Logfire lecture later |

---

## 6. Problems you will hit

| Symptom | Cause | What to do |
| --- | --- | --- |
| **Run All stops at cell [2]** with `NameError: nvidia_model` | The import on line 1 is commented out | Run cells one by one and skip [2], or run `from model import nvidia_model` |
| **Cell [7] says `list`** | It was run after [10]. `result` was overwritten. | Restart, then Run All, then it says `EmployeeModel` |
| **`AttributeError ... has no attribute 'salary'`** in [12] or [13] | You re-ran [14] before them, so `result` is a list of CVs | Re-run [10] first |
| **`KeyError: 'NVIDIA_API'`** in [1] | No `.env` file or no key | Create `.env` with `NVIDIA_API=...` (lecture 01) |
| **Cell [3] or [10] very slow, then a timeout** | Slow model or network. Cell [3] has `timeout = 60`. | Run again or use another model |
| **A validation error that does not go away** | The model keeps returning a salary outside the range, so even the retry fails | Loosen the range or improve the description |
| **`ModuleNotFoundError: No module named 'dlt'`** at [18] | Not installed | Probably `uv add "dlt[duckdb]"` |
| **A lot more rows than expected** from [23] | The double join (section 4) | Join one child at a time |

---

## 7. Explain it in your own words

If you can say each of these in plain words, you understand the notebook.

| Idea | One sentence |
| --- | --- |
| Free text ([3]) | "If I only ask in words I get a sentence, and I have to dig the numbers out myself." |
| `BaseModel` ([5]) | "I describe one record as a class, like a table schema, and anything built from it is checked." |
| `Field` ([5]) | "The description is a hint for the AI. `gt` and `lt` are limits that Pydantic enforces." |
| `output_type` ([5]) | "I tell the agent to answer in that shape. It is sent as a tool, validated, and retried if wrong." |
| `result.output` ([8]) | "It is now a real object: `.name` is text, `.salary` is a number." |
| `list[...]` ([10]) | "I can ask for many records at once. The number I ask for is not enforced." |
| `model_dump()` ([9], [13]) | "I turn an object into a dict, so pandas can make a table." |
| Nested models ([14]) | "A person with a list of jobs is a parent with child rows, filled in one answer." |
| `dlt` ([18]) | "It splits the nested data into linked tables in DuckDB and gives them ids." |
| The join ([23]) | "I put the tables back together, but joining two child tables at once multiplies the rows." |

---

## 8. Questions you may have

<details><summary>1. What is the difference between <code>BaseModel</code> and a normal Python class?</summary>

A normal class accepts anything you put in. A `BaseModel` checks types when the object is created, converts safe values (`"34"` becomes `34`), and raises a validation error for the rest. It can also turn itself into a dict (`model_dump()`) or a JSON schema.
</details>

<details><summary>2. Why does the notebook have both <code>agent</code> and <code>employee_simulator</code>?</summary>

`employee_simulator` (cell [2]) is a leftover from an earlier version and is never used. All the later cells use `agent` from cell [3].
</details>

<details><summary>3. Do I need <code>Field</code> for every field?</summary>

No. Only for fields where you want a hint or extra limits. Plain fields like `name: str` can stay as they are, but a good field name helps the model because there is no description to read.
</details>

<details><summary>4. The class docstring in cell [5] is long. Does the LLM see it?</summary>

Yes. I tested it: the field descriptions are in the schema, and the class docstring is sent as well (as the description of the `final_result` tool, or inside the schema for a list). So the docstring in cell [5] is partly an instruction to the model.
</details>

<details><summary>5. What if the LLM returns a salary of 60000?</summary>

Pydantic rejects it (`lt=50_000`). The error goes back to the LLM and it retries once. If the second answer is also wrong, you get an error instead of a bad value.
</details>

<details><summary>6. Does validation prove the person is realistic?</summary>

No. It proves the shape and the limits. "Anna Lindberg, 30, 45000" is valid, but it is made up. Checking truth needs evaluation (a later lecture).
</details>

<details><summary>7. Why use <code>model_dump()</code> and not just pass the object to pandas?</summary>

`pd.DataFrame` understands dicts, not Pydantic objects. `model_dump()` gives dicts, and also converts nested models.
</details>

<details><summary>8. Why is the CV example "nested" and why does that make it hard?</summary>

One person has many jobs. In JSON that is natural: a list inside the person. In a flat table it is not, so you either store the document as it is or split it into parent and child tables, which is what `dlt` does in cells [18] to [22].
</details>

<details><summary>9. Why does <code>result.output[-1]</code> give the last person?</summary>

In Python, index `-1` is the last item of a list, `-2` the second last, and so on.
</details>

---

## 9. My questions

Add questions here as you read, then ask Claude to answer them in this file.

- [ ]
