# Study guide: `lecture_pydanticai_pydantic_models.ipynb`

A walkthrough of **one notebook**, cell by cell. Keep it open next to the notebook in VS Code.

- The wider background for this folder (how structured output works inside, the other two notebooks, the exercise bug) is in [STUDY_GUIDE_strctured_output_exercise.md](STUDY_GUIDE_strctured_output_exercise.md). This file does not repeat it. It follows the notebook in order.
- Cell numbers: VS Code shows a badge like `[3]` to the left of each **code** cell after it runs. In this guide `[3]` means the **3rd code cell from the top**, which is the cell that shows `[3]` after **Restart, then Run All**. Markdown cells have no badge, so I call them by their heading. This notebook has 24 cells, 19 of them code cells. Line numbers are lines **inside** the cell.
- The notebook is in Swedish. I give translations where a Swedish text matters.

| Guide label | Type | How the cell starts | Badge saved in the file today |
| --- | --- | --- | --- |
| title | markdown | `# PydanticAI together with Pydantic Models` | none |
| **[1]** | code | `# Agent: ...` imports and the `model` | [1] |
| **[2]** | code | `employee_simulator = Agent(` (free-text format, run twice) | [2] |
| "Force a structured output..." | markdown | `## Force a structured output using pydantic` | none |
| **[3]** | code | `from pydantic import BaseModel, Field` | [3] |
| **[4]** | code | `employee_simulator = Agent(` (no `output_type`) | [4] |
| **[5]** | code | `result = await employee_simulator.run(` ... `output_type=EmployeeModel` | [5] |
| **[6]** | code | `employee2 = result.output` | [6] |
| **[7]** | code | `type(employee2)` | [7] |
| **[8]** | code | `employee2.name + " är cool"` | [8] |
| **[9]** | code | `employee2.salary` | [9] |
| **[10]** | code | `employee2.__dict__.keys()` | [10] |
| **[11]** | code | `employee2.__dict__.values()` | [11] |
| **[12]** | code | `for key, value in employee2.__dict__.items():` | [12] |
| "Simulate many employees" | markdown | `## Simulate many employees` | none |
| **[13]** | code | `result = await employee_simulator.run("Ge mig totalt 10 ...` | [13] |
| "Task - calculate mean salary" | markdown | `## Task - calculate mean salary` | none |
| **[14]** | code | `employees = result.output` | [14] |
| **[15]** | code | `salary = 0` (the loop) | [15] |
| "Convert to dataframe" | markdown | `## Convert to dataframe` | none |
| **[16]** | code | `employees[0].model_dump()` | [16] |
| **[17]** | code | `import pandas as pd` | [17] |
| **[18]** | code | `# df.to_csv("employees.csv", index=None)` | [18] |
| **[19]** | code | `df.plot(kind = "barh", x = "name", y = "salary")` | [19] |

The saved badges already run [1] to [19] in order, so they match the guide labels. If a number ever disagrees with what you see, match the cell by how it starts.

---

## 1. The story of the notebook

The notebook answers one question: **how do I get usable data out of an LLM?**

```
Stage 1  cells [1]-[2]   Ask for a format in words              → free text, unreliable
Stage 2  cells [3]       Describe the format as a class         → Pydantic alone, no AI
Stage 3  cells [4]-[5]   Ask the AI to fill that class          → a real object
Stage 4  cells [6]-[12]  Use the object                         → .name, .salary, model fields
Stage 5  cells [13]-[15] Ask for many, then compute             → list of objects, a mean
Stage 6  cells [16]-[19] Turn objects into rows                 → DataFrame, chart
```

Each stage fixes a weakness of the one before it. Read the notebook as that chain, not as 24 separate cells.

### The data flow of the whole notebook

```
Your prompt ──► LLM ──► JSON that fits the schema ──► Pydantic checks it ──► EmployeeModel object
                                                                                  │
                                                list[EmployeeModel] (cell [13]) ◄─┘
                                                           │
                              employee.model_dump() for each (cell [17])
                                                           │
                                                  list of dicts ──► pd.DataFrame ──► table, chart
```

---

## 2. Variable tracker

Notebooks keep every name alive until you overwrite it. Most confusion in this notebook comes from names being reused. Use this table when a cell does not do what you expect.

| Name | Created in cell | Overwritten in cell | What it holds at the end |
| --- | --- | --- | --- |
| `model` | [1] | never | The Nvidia model object (lecture 01) |
| `employee_simulator` | [2] | **[2]** (again, same text), **[4]** (new, shorter instructions) | An Agent with only `"Du är expert på att simulera anställda i Sverige"` |
| `result` | [2] | [2], **[4], [5], [13]** | Result of the last run. After cell [13] it holds a **list** of employees. |
| `EmployeeModel` | [3] | never | Your Pydantic class (the blueprint) |
| `employee1` | [3] | never | One employee built **by hand** |
| `employee2` | [6] | never | One employee **from the AI** (from cell [5]'s result) |
| `employees` | [14] | never | The list of 10 `EmployeeModel` from cell [13] |
| `salary` | [15] | never | A running total, ends as the sum of all salaries |
| `df` | [17] | never | The DataFrame of the 10 employees |

Two consequences:

1. **Cells [5] and [13] use the simple agent from cell [4]**, not the one with the format example from cell [2]. The structure no longer comes from the prompt text. It comes from `output_type`.
2. **Cell [6] depends on cell [5]'s `result`**, and **cell [14] depends on cell [13]'s `result`**. If you run cell [5] again, `result` changes but `employee2` does not, until you re-run cell [6].

---

## 3. Cell by cell

### Cell [1] — set up the model (this is lecture 01, again)

```python
model = OpenAIChatModel("nvidia/nemotron-3.5-lightning-30b-a3b", provider=OpenAIProvider(base_url=..., api_key=os.environ["NVIDIA_API"]))
```

| Lines | What | Where you learned it |
| --- | --- | --- |
| 2 to 12 | Imports | Lecture 01, the big cell (cell [2] in the 01 guide) |
| 16 | `load_dotenv()` | Lecture 01 |
| 20 to 26 | Provider inside Model | Lecture 01 |

There is no `Agent(...)` here. The agent is built in cell [2]. Nothing new to learn, only to run.

---

### Cell [2] — Stage 1: ask for a format in words

**Translation of the Swedish:**

```
instructions = "You are an expert at simulating employees in Sweden.
                Follow this format:
                name: "Bertil"   age: 40   salary: 35000   role: "IT-supporter"   ort: "Göteborg" "
prompt       = "Give me a data engineer who works in Stockholm"
```

| Lines | What it does |
| --- | --- |
| 1 to 11 | Builds an agent. `instructions` describes the job **and shows an example of the format** |
| 13 to 16 | Runs it and prints the answer |
| 18 to 28 | Builds the **same** agent again |
| 30 to 31 | Runs it again (with a lowercase `stockholm` and a trailing space) and prints |

**What the output showed:** two different people, `Johan` and `Miriam`, both in a `name: "..."` layout.

**Why the cell is there:** to show the weakness. Two runs of the same prompt give two different answers (that is normal for LLMs, see lecture 02). The answer is a **string**. To use `salary` you would parse text yourself. Nothing guarantees `salary: 35000` is a number.

**Watch out:** `ort` is in the example format, but your `EmployeeModel` in cell [3] has no `ort` (it has `description` instead). The two designs are not the same, and that is fine. From cell [3] on, the class is the truth, not this text.

---

### The "Force a structured output using pydantic" cell (markdown)

The turning point. "Force" is the right word: instead of **asking** for a format, you **require** it.

---

### Cell [3] — Stage 2: Pydantic alone (the most important cell)

```python
from pydantic import BaseModel, Field
```

- `BaseModel` is a class you inherit from to describe the shape of a record: which `fields` it has, what `type` each one is, and what `limits` apply. 
- **Anything built from that class gets checked automatically.**

| Lines | Code | Meaning |
| --- | --- | --- |
| 1 | `from pydantic import BaseModel, Field` | `BaseModel` gives the class checking powers, `Field` adds rules |
| 4 | `class EmployeeModel(BaseModel):` | A new data shape. The name is yours. |
| 5 to 7 | `name: str = Field(description=...)` | A text field. The description is a hint for humans **and the LLM**. |
| 8 | `age: int = Field(..., ge=18, le=67)` | A whole number, from 18 up to and including 67 |
| 9 to 13 | `salary: int = Field(..., ge=30_000, lt=60_000)` | From 30000 up to but **not including** 60000 |
| 14 | `role: str` | Text |
| 15 | `description: str` | Text |
| 18 to 24 | `employee1 = EmployeeModel(name="Bertil", ...)` | **Build one by hand.** No AI involved. |
| 26 | `employee1` | Shows the object |

**Why the cell builds one by hand:** to show that Pydantic works without the AI. Pydantic accepts `salary=30000` because `ge=30_000` allows the boundary. Later the AI fills the same class, and the same rules apply.

**Reading `ge`, `le`, `lt`:** `ge` = greater or equal, `le` = less or equal, `lt` = less than. So ages 18 to 67 are allowed, salaries 30000 to 59999 are allowed.

---

### Cell [4] — the same agent, no structure

```python
employee_simulator = Agent(model=model, instructions="Du är expert på att simulera anställda i Sverige")
result = await employee_simulator.run("Ge mig en data engineer i stockholm")
result.output
```

Shorter instructions this time (no format example). The prompt is "Give me a data engineer in Stockholm".

**What the output showed:** a long Swedish essay that starts with *"I can't give you a specific person's contact details or private data, but I can help you with a realistic profile..."*, then lists typical tech stacks, salaries and where to find people.

**Why the cell is there:** it is the "before" picture for cell [5]. Same agent, same prompt, no `output_type`: you get an essay, not a record. It also shows that an LLM may refuse or wander off.

**Also:** this cell redefines `employee_simulator` (see the variable tracker).

---

### Cell [5] — Stage 3: the core line of the lecture

```python
result = await employee_simulator.run(
    "Ge mig en data engineer i stockholm", output_type=EmployeeModel
)
result
```

The only difference from cell [4] is **`output_type=EmployeeModel`**.

**What it did:** the output was

```
AgentRunResult(output=EmployeeModel(name='Johan Karlsson', age=32, salary=45000,
               role='Data Engineer', description='Designs and maintains data pipelines...'))
```

Look at it carefully: `output=` is no longer text. It holds an `EmployeeModel(...)`.

**What happened inside** (I verified this on your installed version with a fake model):

```
output_type=EmployeeModel
   │ Pydantic turns the class into a JSON schema (names, types, descriptions, ge/le/lt)
   ▼
Pydantic AI sends the schema to the LLM as a tool called "final_result"
   │ the LLM answers by "calling" that tool with JSON
   ▼
Pydantic validates the JSON against EmployeeModel
   ├── ok      → you get an EmployeeModel
   └── not ok  → the error goes back to the LLM, it retries (1 retry by default)
```

Without `output_type`, the same test showed the agent allowed plain text and had no `final_result` tool. So `output_type` changes what the model is *allowed* to say.

**Notes:**

- `output_type` is given to `run`, so it applies to **this call only**. Run the same agent again without it and you get text again. (Lecture 04 puts it on the Agent itself.)
- The `description` came back in **English**, although the Field description was Swedish. Descriptions guide the model, they do not force a language.

---

### Cells [6] to [9] — Stage 4: it is a real object

| Cell | Code | Output | What it shows |
| --- | --- | --- | --- |
| [6] | `employee2 = result.output` | the employee | The object lives in `result.output` (as in lecture 01) |
| [7] | `type(employee2)` | `__main__.EmployeeModel` | It is an instance of **your** class. `__main__` means "defined in this notebook". |
| [8] | `employee2.name + " är cool"` | `'Johan Karlsson är cool'` | `.name` is a normal string ("is cool"). You can use it in code. |
| [9] | `employee2.salary` | `45000` | `.salary` is a number, not text |

**Compare cell [9] with cell [2].** In cell [2] you had `salary: 45000` as part of a text. Here `employee2.salary` is the integer `45000`. That is the whole benefit.

**Try (in a scratch cell at the bottom):** `employee2["name"]`. It raises `TypeError: 'EmployeeModel' object is not subscriptable`. The object is not a dict. You use `.name`, not `["name"]`.

---

### Cells [10] to [12] — looking inside the object

| Cell | Code | What it returns |
| --- | --- | --- |
| [10] | `employee2.__dict__.keys()` | `dict_keys(['name', 'age', 'salary', 'role', 'description'])` |
| [11] | `employee2.__dict__.values()` | the five values |
| [12] | `for key, value in employee2.__dict__.items(): print(f"{key}: {value}")` | one line per field |

`__dict__` is Python's internal store of an object's attributes. It works, and I checked that for a flat model `employee2.__dict__ == employee2.model_dump()`. But cell [16] uses `model_dump()`, which is the proper Pydantic method and also handles nested models. Prefer `model_dump()` in your own code.

Cell [12] is a plain Python loop. Each line is `key: value`, like the old free-text format in cell [2], except this time the *code* produced it from validated data.

---

### The "Simulate many employees" cell (markdown)

Next stage: from one record to a table.

---

### Cell [13] — Stage 5: a list of objects

```python
result = await employee_simulator.run(
    "Ge mig totalt 10 anställda inom IT/HR/marketing",   # "Give me a total of 10 employees in IT/HR/marketing"
    output_type=list[EmployeeModel],
)
```

`list[EmployeeModel]` means "a list where every item fits `EmployeeModel`". The output is `AgentRunResult(output=[EmployeeModel(...), EmployeeModel(...), ...])`.

**What to notice in the output:**

- 10 items. Ages from 27 to 50 (inside 18 to 67). Salaries from 38000 to 57000 (inside 30000 to 59999). The limits held for every item.
- Roles: Software Developer, DevOps Engineer, HR Specialist, HR Manager, Marketing Coordinator, Content Strategist, and more. The prompt asked for IT, HR and marketing, and the model varied them.

**Watch out:** the number **10 is only a request in the prompt**. `list[EmployeeModel]` does not say "exactly 10". The model could return 8 or 12, and Pydantic would accept it. Count with `len(employees)` if it matters.

---

### Cells [14] and [15] — compute the mean salary (under "Task - calculate mean salary")

| Cell | Code | Meaning |
| --- | --- | --- |
| [14] | `employees = result.output` | Save the list under a clearer name |
| [15] | loop adding `employee.salary` into `salary`, then `salary/len(employees)` | Result: `47600.0` |

**Line by line of cell [15]:**

```python
salary = 0                         # line 1: running total
for employee in employees:         # line 3: go through each EmployeeModel
    salary += employee.salary      # line 4: add this person's salary
salary/len(employees)              # line 6: total divided by the number of people
```

I checked the arithmetic: 45000 + 52000 + 38000 + 55000 + 40000 + 48000 + 42000 + 57000 + 46000 + 53000 = 476000, and 476000 / 10 = 47600.0.

**Why this works:** `employee.salary` is guaranteed to be an `int` by validation. With free text you would first have to extract and convert it.

**Alternatives (same result):** `sum(e.salary for e in employees) / len(employees)`, or `statistics.mean(...)`, or after cell [17], `df["salary"].mean()`.

---

### Cell [16] — one object to a dict
The step that connects the AI to your normal data tools.

```python
employees[0].model_dump()
```

Returns a plain Python dict for the first employee: `{'name': 'Alice Ericsson', 'age': 30, 'salary': 45000, ...}`.

`model_dump()` turns a Pydantic object into plain data (dict of str, int, ...). Pandas, JSON and databases all understand dicts, but not Pydantic objects.

---

### Cell [17] — list of dicts to a DataFrame

```python
import pandas as pd
df = pd.DataFrame([employee.model_dump() for employee in employees])
df.head()
```

Read the second line from the inside out:

```
employees                                       list of 10 EmployeeModel
[employee.model_dump() for employee in ...]     list of 10 dicts          (one dict = one row)
pd.DataFrame( ... )                             table with columns name, age, salary, role, description
```

A **list of dicts** is the standard "records" shape that `pd.DataFrame` turns into rows. `df.head()` shows the first five.

> **Data engineer view:** the field names of `EmployeeModel` became the column names, and the field types became the column types. The class acted as the schema for the table.

---

### Cell [18] — a commented-out line

```python
# df.to_csv("employees.csv", index=None)
```

Commented out, so it does nothing. It most likely wrote `employees.csv` in this folder during an earlier run (the file has 10 rows plus a header, but different names from the current output, so it came from another run). Nothing else in the repo reads that file. `index=None` leaves out the row numbers.

---

### Cell [19] — chart

```python
df.plot(kind="barh", x="name", y="salary")
```

A horizontal bar chart: one bar per person, bar length = salary. `barh` = bar, horizontal. The output `<Axes: ylabel='name'>` is the chart object, and the picture appears below it. The first row of the DataFrame is drawn at the **bottom**. This uses `matplotlib`, which is installed through your `uv add` line in the lecture 01 README.

---

## 4. Explain it in your own words

Use these as a self-test. If you can say each in plain words, you understand the notebook.

| Stage | One sentence |
| --- | --- |
| Free text ([2], [4]) | "If I only ask in words, I get text that changes every time and that I have to parse." |
| `BaseModel` ([3]) | "I describe the exact shape of a record as a class, like a table schema with rules." |
| `Field` ([3]) | "A description tells the AI what to put in. `ge`, `le` and `lt` set limits." |
| `output_type` ([5]) | "I tell the agent to answer in that shape, and Pydantic checks it, with a retry if it is wrong." |
| `result.output` ([6] to [9]) | "It is now a real object: `.name` is text, `.salary` is a number." |
| `list[...]` ([13]) | "I can ask for many records at once." |
| `model_dump()` ([16], [17]) | "I turn objects into dicts so pandas can make a table." |

---