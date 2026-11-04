# Study guide: 04 Pydantic + FastAPI

Keep this open next to the code in VS Code. Open the file named in the table, then read the matching section here.
This guide explains the **why**. The docstrings and comments in the files already explain the **what**.

This lecture has no notebook. It is four small Python files in `src/`, so references look like `movies_api.py` line 81.

| When you are reading... | Read this section |
| --- | --- |
| Anything about "API", "endpoint", "GET", "POST" | [3. Web API in plain words](#3-web-api-in-plain-words) |
| `data_models.py` | [4.1 data_models.py](#41-data_modelspy--the-shapes) |
| `setup_db.py` | [4.2 setup_db.py](#42-setup_dbpy--create-the-table-once) |
| `utils.py` | [4.3 utils.py](#43-utilspy--one-function-to-run-sql) |
| `movies_api.py` | [4.4 movies_api.py](#44-movies_apipy--the-api) |
| How to run it | [5. Running it](#5-running-it) |
| Any later lecture | [8. Where this connects](#8-where-this-connects) |

---

## 1. The 30-second version

Until now the AI lived inside a notebook. Only you could use it. Lecture 04 puts it **behind a web address**, so any program (a web page, another service, a script) can use it by sending a request.

The example app is a movie list:

- `GET /movies` returns the movies stored in a database.
- `POST /movie` takes a sentence like "a famous 80s horror movie", asks the AI for a **structured** `Movie`, saves it in the database, and returns it.

Three earlier ideas meet here:

| From | Used here for |
| --- | --- |
| Lecture 01 | An `Agent` that talks to a model (this time Google Gemini, not Nvidia) |
| Lecture 03 | `output_type=Movie`, so the AI answers in a validated shape |
| New | FastAPI (the web layer) and DuckDB (the storage) |

> **Data engineer view:** this is a tiny pipeline. Request in, LLM as a transform step, validated row, `INSERT` into a table, row out. FastAPI is the ingestion endpoint and Pydantic is the data contract on both sides.

---

## 2. The pictures to understand

### Picture A: how the files connect

```
 data_models.py     Movie, Prompt        (shapes, no logic)
       ▲   ▲
       │   └──────────────────────────────┐
 setup_db.py ──► utils.py ◄──────────── movies_api.py  ◄── you run this one
 (run once)      query_duckdb()          (FastAPI app: the "main" file)
       │               │                        │
       └───────────────┴────────► data/movies.duckdb   (a single database file)
                                                │
                                      Gemini model (over the internet)
```

Only `movies_api.py` is a running program. The others are imported by it or run once.

### Picture B: what happens on `POST /movie`

```
You send:   POST /movie     {"prompt": "a famous 80s horror movie"}
                │
                ▼
1. FastAPI checks the body against `Prompt`        ── wrong shape → automatic 422 error, your code never runs
                │
                ▼
2. agent.run(prompt, output_type=Movie)            ── the LLM must answer with title, year, genre, rating
                │                                      rating outside 1-5 → error goes back to the LLM, it retries
                ▼
3. query_duckdb("INSERT INTO movies VALUES (?,?,?,?)", [title, year, genre, rating])
                │
                ▼
4. FastAPI turns the Movie into JSON and returns it   {"title": "Alien", "year": 1979, "genre": "Horror", "rating": 5}
```

Pydantic does two jobs in this one request. It checks what **comes in** (step 1, `Prompt`) and what the **AI produces** (step 2, `Movie`).

---

## 3. Web API in plain words

You will meet these words in every web tutorial.

| Word | Meaning here |
| --- | --- |
| **Server** | A program that waits for requests and answers them. Yours runs on your own machine. |
| **API** | The list of things a server lets other programs do. |
| **Endpoint** | One address + one action, like `GET /movies`. |
| **URL** | `http://127.0.0.1:8000/movies`. `127.0.0.1` means "this computer", `8000` is the port, `/movies` is the path. |
| **GET** | "Give me data." It should not change anything. |
| **POST** | "Here is data, do something with it." It sends a body. Here it creates a movie. |
| **JSON** | The text format used to send data, like `{"title": "Alien", "year": 1979}`. |
| **Status code** | `200` = OK. `422` = your request had the wrong shape. `404` = no such address. `500` = the server crashed. |
| **FastAPI** | The Python library where you declare endpoints with functions. |
| **uvicorn** | The program that actually listens on the port and hands requests to FastAPI. FastAPI is the app, uvicorn is the engine that runs it. |
| **`/docs`** | A page FastAPI generates for you. You can try every endpoint from the browser. |

### Why put the AI behind an API at all?

| Without an API | With an API |
| --- | --- |
| Only your notebook can use the agent | Any program can, in any language |
| The key stays on your machine | The key stays on the server, callers never see it |
| Each caller re-implements validation | The server validates once |
| Hard to add a web page | The web page just calls the URL (lecture 05) |

---

## 4. The files

### 4.1 `data_models.py` — the shapes

Two Pydantic models, lines 25 to 53.

| Model | Lines | Role |
| --- | --- | --- |
| `Movie` | 25 to 43 | One movie: `title: str`, `year: int`, `genre: str`, `rating: int = Field(gt=0, lt=6)` |
| `Prompt` | 46 to 53 | The request body: just `prompt: str` |

**`Field(gt=0, lt=6)`** (line 43) means greater than 0 and less than 6, so the only valid ratings are 1, 2, 3, 4 and 5. This is the same idea as `ge`/`lt` in lecture 03.

**One model, two jobs.** `Movie` is used as:

1. the `output_type` for the AI (so the LLM must reply with these fields), and
2. the return value of the endpoint (so the API's response has the same fields).

The shape is written once and reused. If you add a field here, the AI, the endpoint and the response all change together. The database table does **not** change on its own (see gotchas).

### 4.2 `setup_db.py` — create the table once

Lines 25 to 32:

```sql
CREATE TABLE IF NOT EXISTS movies (title TEXT, year INTEGER, genre TEXT, rating TINYINT);
```

- `IF NOT EXISTS` makes it safe to run twice. It never deletes data.
- The columns are in the **same order** as the fields of `Movie`. That order matters because the insert in `movies_api.py` is positional (see 4.4).
- `TINYINT` is a very small whole number, enough for 1 to 5.
- Run it **once** before starting the API. Without the table, both endpoints fail.

Your database already has the table and two movies: *The Terminator* (1984) and *Shaolin Soccer* (2002), both rated 5.

### 4.3 `utils.py` — one function to run SQL

`query_duckdb(sql_code, parameters=None)`, lines 29 to 59.

| Line | What it does | Why |
| --- | --- | --- |
| 26 | `DATA_PATH = Path(__file__).parent.parent / "data"` | Builds the database folder from the **file's own location**, so it works from any launch directory |
| 47 | `with duckdb.connect(DATA_PATH / "movies.duckdb") as conn:` | Opens the database file, and closes it afterwards even if there is an error |
| 50 | `conn.execute(sql_code, parameters)` | Runs the SQL. `?` placeholders are filled from `parameters`. |
| 55 to 58 | If the SQL starts with `select`, `from`, `desc` or `pragma`, return a DataFrame | Reads give back rows as a pandas DataFrame |
| 59 | Otherwise return nothing | `CREATE` and `INSERT` have no rows to return |

**DuckDB** is a database that lives in one file. There is no server to install. Python opens the file. It is popular with data engineers for analytics.

**Why `?` placeholders** (SQL injection). Writing values into the SQL string yourself is dangerous. A title like `x'); DROP TABLE movies;--` could be run as SQL. With placeholders the value is passed separately and stored as plain text. I tested this on a copy of your database: a movie with exactly that title was saved as a normal row and the table survived.

**`FROM movies;`** is DuckDB shorthand for `SELECT * FROM movies;`. That is why `"from"` is in the list of read statements on line 56.

### 4.4 `movies_api.py` — the API

Read it top to bottom. It is short.

| Lines | Code | Meaning |
| --- | --- | --- |
| 28 to 34 | imports | `FastAPI`, `Agent`, `load_dotenv`, `query_duckdb`, `Movie`, `Prompt` |
| 38 | `load_dotenv()` | Loads the `.env` file so the API key exists. **Must run before line 52.** |
| 42 | `app = FastAPI()` | The web application. Everything below registers endpoints on it. |
| 52 | `agent = Agent(model="google:gemini-flash-lite-latest", output_type=Movie)` | One agent, created **once** when the file loads, and reused for every request |
| 55 to 66 | `@app.get("/movies")` | Read endpoint |
| 69 to 96 | `@app.post("/movie")` | Create endpoint |

#### The model string (line 52)

`"google:gemini-flash-lite-latest"` is a **shortcut** for the three objects from lecture 01. The part before the colon picks the provider (`google`), the part after picks the model. Pydantic AI builds the provider for you and reads the key from the environment (`GOOGLE_API_KEY` or `GEMINI_API_KEY`). I confirmed this: it creates a `GoogleModel` with a `GoogleProvider`.

`-latest` is an alias that always points to a current version, because Google retires specific versions often.

**If the key is missing, the server does not even start.** I tested this: creating the Agent without a key raises an error right away. That is why `load_dotenv()` on line 38 has to come first.

On Windows your `.env` line `Gemini_API_Key=...` works, because Windows treats environment variable names as case-insensitive. I tested that too. On Mac or Linux the name would have to be `GEMINI_API_KEY` exactly.

#### `GET /movies` (lines 55 to 66)

```python
@app.get("/movies")
async def read_movies():
    movies = query_duckdb("FROM movies;")
    return movies.to_dict(orient="records")
```

- The line starting with `@` is a **decorator**. It says: "when a GET request arrives at `/movies`, call the function below".
- `query_duckdb` returns a DataFrame. `to_dict(orient="records")` turns it into a list of dicts, one per row, which FastAPI converts to JSON.

#### `POST /movie` (lines 69 to 96)

```python
@app.post("/movie")
async def create_movie(query: Prompt):
    result = await agent.run(query.prompt, output_type=Movie)
    movie = result.output
    query_duckdb("INSERT INTO movies VALUES (?,?,?,?)",
                 parameters=[movie.title, movie.year, movie.genre, movie.rating])
    return movie
```

| Part | Meaning |
| --- | --- |
| `query: Prompt` (line 70) | FastAPI reads the JSON body and checks it against `Prompt`. A bad body gets a `422` before your function runs. |
| `await agent.run(...)` (line 81) | The same call as lecture 01. `output_type=Movie` makes the answer a validated `Movie`. |
| `movie = result.output` (line 83) | A real `Movie` object (lecture 03) |
| `INSERT ... VALUES (?,?,?,?)` (lines 90 to 93) | Saves a row. The order `title, year, genre, rating` must match the table. |
| `return movie` (line 96) | FastAPI turns it into JSON automatically |

**Why `async def` and `await`.** Waiting for the AI takes seconds. While one request waits, the server can answer other requests. The same idea as lecture 01.

**`output_type` appears twice** (lines 52 and 81). Line 52 sets it as the agent's default. Line 81 passes it again for this call. The second one is not needed, but it does no harm.

---

## 5. Running it

From the README. Run these in a terminal, in this order:

```bash
cd 04_pydantic_fastapi/src
uv run python setup_db.py                      # once: creates the table (already done for you)
uv run uvicorn movies_api:app --reload         # starts the server
```

| Open in the browser | What you see |
| --- | --- |
| `http://127.0.0.1:8000/movies` | The movies as JSON |
| `http://127.0.0.1:8000/docs` | FastAPI's interactive page. Open `POST /movie`, click **Try it out**, send `{"prompt": "a famous 80s horror movie"}`. |

What the command means:

| Part | Meaning |
| --- | --- |
| `uvicorn` | The server program |
| `movies_api:app` | In the file `movies_api.py`, find the variable named `app` |
| `--reload` | Restart when you save the file. Good for development only. |

**Why you must be inside `src/`.** `movies_api.py` does `from utils import query_duckdb` and `from data_models import Movie, Prompt`. Python finds those files in the current folder, so you run the server from `src/`. The README says "cd into 04 file and src".

Needs an API key: put `Gemini_API_Key=...` in the repo's `.env` (get one at Google AI Studio, linked in the README).

---

## 6. What I tested

I ran your real code on a **copy** of the project, with a fake AI model, so your database and your quota were untouched.

| Test | Result |
| --- | --- |
| `GET /movies` | `200`, returns the two stored movies |
| `POST /movie` with a normal prompt | `200`, returns the new movie, and `GET /movies` then shows it |
| The fake AI first answered `rating = 6` | Pydantic rejected it, the error went back, the AI retried with `5`. Two model calls, one saved row. |
| `POST /movie` with `{"wrong": "x"}` | `422`, message "Field required" for `body.prompt`. The AI was never called. |
| A title containing `'); DROP TABLE movies;--` | Saved as plain text. The table survived. |
| The app's address list | `/movies` and `/movie` (plus FastAPI's built-in docs pages) |

---

## 7. Gotchas

| Gotcha | Why | What to do |
| --- | --- | --- |
| **`ModuleNotFoundError: utils`** | You started the server from the wrong folder | `cd` into `src/` first |
| **Server will not start, key error** | No API key found when the Agent is created on line 52 | Check `.env` has the Gemini key, and that `load_dotenv()` runs first |
| **404 / 429 / 503 from the model** | Google retires models (404), limits the free tier (429), or is overloaded (503) | Try another model name on line 52 |
| **The database does not enforce 1 to 5** | `rating TINYINT` has no `CHECK` rule. Only Pydantic stops a 6. | Any other code that writes to the table can store a 6. Add a `CHECK` if it matters. |
| **Changing `Movie` does not change the table** | The table was created once by `setup_db.py` | Change the table yourself too, and keep the column order |
| **Positional insert** | `VALUES (?,?,?,?)` has no column names | If the order of fields and columns drifts apart, data lands in the wrong column |
| **Every POST adds a row** | There is no duplicate check | Sending the same prompt twice creates two rows |
| **Every POST costs an AI call** | Plus a retry if validation fails | Watch your free quota |
| **Valid is not true** | The AI can invent a movie or a wrong year, and it still passes validation | Never trust the content just because the shape is right |
| **One writer at a time** | DuckDB lets one process write to the file at a time | Do not open the same `.duckdb` file in a notebook while the API is writing |
| **README is stale** | It says the code uses OpenRouter, but it uses Gemini. It also has the typo `python -dotenv`. | Use `python-dotenv` and the Gemini key |
| **The database is in git** | `data/movies.duckdb` is a tracked binary file | Every insert changes it, so `git status` shows it modified |
| **Blocking calls in `async def`** | `query_duckdb` is not async, so it pauses the server for the moment it runs | Fine for a small file database. A big query would block other requests. |

---

## 8. Where this connects

| In 04 | Comes from | Goes to |
| --- | --- | --- |
| `Agent` + `await agent.run` | Lecture 01 | Lecture 05 `chat_agent.py` (same pattern inside an endpoint) |
| `output_type=Movie` | Lecture 03 (`output_type=EmployeeModel`) | Lecture 06 uses plain text output, with tools |
| `Prompt` validating the request | New: Pydantic for **incoming** data | Lecture 05 `ChatRequest` does the same job for chat messages |
| `Movie` as response | New: one model, used twice | Lecture 05 `ChatResponse` |
| `"google:gemini-flash-lite-latest"` | New: the model-string shortcut | Lecture 05 `constants.py` keeps these strings in one place |
| `load_dotenv()` before the Agent | Lecture 01 | Every later file |
| `app = FastAPI()` and decorators | New | Lecture 05 `api.py` |
| `ModelSettings` imported, unused (line 31) | Lecture 02 (temperature) | Not used here. It is where you would tune the model. |

```
01-03  an Agent in a notebook
  │
04     the same Agent behind a web address (FastAPI) + saved to a database (DuckDB)
  │
05     a web page (Streamlit) that calls the web address, and a chat history
  │
06     the Agent can call your Python functions
```

---

## 9. Glossary (new words in 04)

| Term | Meaning |
| --- | --- |
| **FastAPI** | Python library for building web APIs from functions |
| **uvicorn** | The server that runs a FastAPI app |
| **Endpoint** | One address + one action, like `POST /movie` |
| **Decorator** | The `@app.get(...)` line that attaches a function to an endpoint |
| **Request body** | The JSON data sent with a POST |
| **Status code** | A number that says how the request went (`200` OK, `422` bad shape) |
| **422** | "Unprocessable": your JSON did not match the expected shape |
| **DuckDB** | A database stored in a single file, with no server |
| **Placeholder (`?`)** | A spot in SQL where a value is inserted safely |
| **SQL injection** | An attack where text is run as SQL. Placeholders prevent it. |
| **Positional insert** | `INSERT` without column names, so the value order must match |
| **`--reload`** | uvicorn option that restarts when you save |

---

## 10. Check yourself

Try to answer before opening each one.

<details><summary>1. What is the difference between FastAPI and uvicorn?</summary>

FastAPI is the library where you define the endpoints (the app). uvicorn is the server program that listens on a port and passes requests to that app. `uvicorn movies_api:app` means "run the `app` variable from `movies_api.py`".
</details>

<details><summary>2. Where does Pydantic check data in <code>POST /movie</code>?</summary>

Twice. FastAPI checks the incoming body against `Prompt`. Pydantic AI checks the AI's answer against `Movie`.
</details>

<details><summary>3. What happens if the AI answers with <code>rating = 6</code>?</summary>

Validation fails (`gt=0, lt=6`), the error is sent back to the model, and it tries again. I saw two model calls and one saved row.
</details>

<details><summary>4. Why does the <code>INSERT</code> use <code>?</code> instead of putting the values into the SQL text?</summary>

To stop SQL injection. The values are passed separately and stored as plain text, never run as SQL.
</details>

<details><summary>5. Why must <code>load_dotenv()</code> come before <code>Agent(...)</code> on lines 38 and 52?</summary>

The Agent looks for the API key when it is created. Without the key in the environment, creating it fails and the server does not start.
</details>

<details><summary>6. Why do you start the server from inside <code>src/</code>?</summary>

The file imports <code>utils</code> and <code>data_models</code> by name, and Python finds them in the current folder.
</details>

<details><summary>7. The database column <code>rating</code> is a TINYINT. What stops someone storing a 6 there?</summary>

Nothing in the database. Only the Pydantic `Movie` model does, and only for data that goes through the API.
</details>

<details><summary>8. What does <code>query_duckdb("FROM movies;")</code> return, and why?</summary>

A pandas DataFrame, because the SQL starts with `from`, which `utils.py` treats as a read statement.
</details>

---

## 11. My questions

Add questions here as you read, then ask Claude to answer them in this file.

- [ ]
