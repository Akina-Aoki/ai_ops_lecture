# Exercise 1, Part 1 - Restaurant Finder (FastAPI + PydanticAI + DuckDB + Streamlit)

This folder implements the exercise 1, part 1 requirement: a FastAPI service
that turns a free-text prompt ("a location and a type of food") into a
structured `Restaurant` via a PydanticAI agent, stores it in DuckDB, and
a Streamlit page that consumes that API.

## Files

| File | What it does |
| --- | --- |
| [data_models.py](data_models.py) | `Restaurant` (AI output + DB row shape) and `Prompt` (request body) |
| [db_utils.py](db_utils.py) | `query_duckdb()`: one helper for running SQL against the DuckDB file |
| [setup_db.py](setup_db.py) | One-time script that creates the `restaurants` table |
| [restaurant_api.py](restaurant_api.py) | The FastAPI app: `GET /restaurants`, `POST /restaurant` |
| [frontend.py](frontend.py) | Streamlit page that calls the API |
| `data/restaurants.duckdb` | The database file (created on first run) |

Data flow for `POST /restaurant`:

```
caller --{"prompt": "..."}--> restaurant_api.py
                                 | 1. validate body with Prompt
                                 | 2. ask the LLM for a Restaurant (PydanticAI)
                                 | 3. save it with query_duckdb()
                                 v
                            data/restaurants.duckdb
```

## 1. Prerequisites

- `NVIDIA_API` set in the repo's `.env` (same key used in exercise 0).
- Dependencies are already in the project's `pyproject.toml`: `fastapi`,
  `uvicorn`, `duckdb`, `streamlit`, `pydantic-ai`. `httpx` comes along as a
  dependency of those, so nothing extra to install.

## 2. Create the database table (once)

From this folder (`exercises/exercise_1/app`):

```bash
python setup_db.py
```

You should see:

```
restaurants table ready.
```

Safe to re-run any time - it won't drop existing data.

## 3. Start the API

```bash
uvicorn restaurant_api:app --reload
```

Leave this running in its own terminal. Check it's alive:

```bash
curl http://127.0.0.1:8000/restaurants
```

This returns `[]` the first time (empty table).

### Try the endpoints

**Browser / Swagger UI** - open [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs),
expand `POST /restaurant`, click **Try it out**, and send:

```json
{"prompt": "A cheap vegan place near Södermalm, Stockholm"}
```

**Or with curl**, in a second terminal:

```bash
curl -X POST http://127.0.0.1:8000/restaurant \
  -H "Content-Type: application/json" \
  -d "{\"prompt\": \"A cheap vegan place near Sodermalm, Stockholm\"}"
```

Expected: a JSON object with `name`, `cuisine`, `price_level`, `rating`,
`description`, `opening_hours`, `location`.

Confirm it was saved:

```bash
curl http://127.0.0.1:8000/restaurants
```

The restaurant you just created should now be in the list.

## 4. Start the Streamlit frontend

In a **third** terminal (API must still be running):

```bash
streamlit run frontend.py
```

This opens `http://127.0.0.1:8501` in your browser.

1. Type a request in the text box, e.g. "A cozy Italian restaurant in Gamla
   Stan, Stockholm", and click **Find a restaurant**.
2. The generated restaurant appears above the table.
3. The **All saved restaurants** table at the bottom lists every restaurant
   saved so far (it re-fetches `GET /restaurants` on every page re-run).

## 5. What "done" looks like

- `python setup_db.py` prints `restaurants table ready.`
- `GET /restaurants` returns `[]` on an empty table, and a growing list as
  you add restaurants.
- `POST /restaurant` with a prompt returns one validated `Restaurant` and
  it shows up in the next `GET /restaurants` call.
- The Streamlit page's form creates a restaurant and the table below it
  updates to include it.

## This was verified by running it

Confirmed working end-to-end in this session:

- `python setup_db.py` -> `restaurants table ready.`
- `uvicorn restaurant_api:app` started; `GET /restaurants` returned `[]`
- `POST /restaurant` with `"A cheap vegan place near Sodermalm, Stockholm"`
  -> returned and saved **Grönska Bistro**
- Streamlit page loaded at `http://127.0.0.1:8501`; submitting "A cozy
  Italian restaurant in Gamla Stan, Stockholm" through the form generated
  and displayed **Trattoria della Nonna**, and the saved-restaurants table
  showed both rows.
