# Study guide: 09 LanceDB (vector database, embeddings, hybrid search)

| When you are reading... | Read this section |
| --- | --- |
| The big idea | [1. The 30-second version](#1-the-30-second-version) and [2. The pictures](#2-the-pictures-to-understand) |
| Words like vector, embedding, distance | [3.1](#31-embeddings-gps-coordinates-for-meaning) and [3.2](#32-vector-search-and-distance) |
| Tables, schemas, `SourceField` | [3.3 Tables](#33-tables-schemas-and-versions) and [3.4 Embedding registry](#34-the-embedding-registry-and-sourcefield--vectorfield) |
| Keyword vs vector vs hybrid | [3.5](#35-three-kinds-of-search) |
| `lancedb_basics.ipynb` | [4.1](#41-lancedb_basicsipynb--part-1) |
| `lancedb_embeddings.ipynb` | [4.2](#42-lancedb_embeddingsipynb--part-2) |
| `custom_embeddings/nvidia_nemotron.py` | [4.3](#43-custom_embeddingsnvidia_nemotronpy--your-own-embedder) |
| The two JSON files | [4.4](#44-the-two-json-files) |
| Installing and running | [5. Setup and running](#5-setup-and-running) |
| Things that can bite you | [6. Gotchas](#6-gotchas-and-things-to-improve) |

---

## 1. The 30-second version

Until now an agent only knew what its model had learned. For a real app (a company chatbot, a help desk) the model must also use **your own documents**. The trick is called **RAG**, and it starts with this lecture:

1. Turn every document into a list of numbers that captures its **meaning** (an **embedding** or **vector**).
2. Store text and vector together in a **vector database** (here: **LanceDB**).
3. When a question comes, turn the question into numbers too, and ask the database: "which stored vectors are **closest**?"

| New in 09 | In one sentence | Where in the code |
| --- | --- | --- |
| **LanceDB** | A database that lives in a folder on your disk and can search by closeness of vectors | `lancedb.connect(...)` in both notebooks |
| **Embedding model** | An AI model that turns text into a vector. Three are used: Cohere, a local one, NVIDIA's | `get_registry().get(...)` |
| **Search by meaning** | `table.search("text")` returns the nearest rows | the search cells |
| **Hybrid search** | Meaning search + keyword search merged together | the last cells of the basics notebook |
| **Custom embedder** | Your own class that plugs a new embedding service into LanceDB | [custom_embeddings/nvidia_nemotron.py](custom_embeddings/nvidia_nemotron.py) |

> **Data engineer view:**
> - LanceDB is to vectors what **DuckDB** is to analytics: **embedded** (a library, not a server), data stored in files in a folder, columnar (Arrow/Lance format).
> - An embedding column is just a column of type `FLOAT[N]`. Vector search is `ORDER BY distance(vector, :query) LIMIT k`.
> - The embedding registry is like an **adapter/connector** layer (think dbt adapters or Spark data sources): same code, different back end.

There are **no agents** in this lecture. No PydanticAI, no FastAPI. It is only notebooks, two JSON files and one small Python file. The agents come back when RAG is added.

---

## 2. The pictures to understand

### Picture A: how the files connect

```
animals_text_embeddings.json ─┐
jokes.json ───────────────────┼──► lancedb_basics.ipynb ──► vector_database/     (folder, made on first run)
                              │           │
                              │           └──► Cohere API   (turns jokes into 1024 numbers)
                              │
jokes.json ───────────────────┴──► lancedb_embeddings.ipynb ──► knowledge_base/  (folder, made on first run)
                                          │
                                          ├──► local model (sentence-transformers, free)
                                          └──► custom_embeddings/nvidia_nemotron.py ──► NVIDIA API
                                                          ▲
                                                          └── reads NVIDIA_API from .env
```

The two notebooks do **not** depend on each other. They use different folders. Only the second one imports a file of ours.

### Picture B: what a LanceDB "database" looks like on disk

```
09_lancedb/
├── vector_database/                 ← db = lancedb.connect("vector_database")
│   ├── animals_text.lance/          ← one table = one folder ending in .lance
│   │   ├── _versions/               ← a manifest for every change (version 1, 2, ...)
│   │   ├── _transactions/           ← the log of what changed
│   │   └── data/                    ← the actual rows (Lance files, columnar)
│   └── jokes.lance/
└── knowledge_base/
    ├── jokes_sentence_transformer.lance/
    └── jokes_nvidia.lance/
```

No server, no port, no password. Copy the folder and you copied the database.

> **Data engineer view:** `_versions` + `_transactions` + `data` is the same idea as **Delta Lake / Iceberg**: data files plus a log. That is why `table.add(...)` gives `version=2`, and why old versions can be read ("time travel").

### Picture C: what happens when you add and search (the heart of the lecture)

```
ADD (writing)
  df of jokes ─► table.add(df) ─► [LanceDB sees joke is a SourceField]
                                         │  calls the embedding model: "Parallel lines have..." ─► [0.013, 0.016, -0.028, ...]
                                         ▼
                              row stored:  joke = "Parallel lines..."   vector = [1024 numbers]

SEARCH (reading)
  "give me jokes on C#" ─► table.search("give me jokes on C#")
                                  │  SAME embedding model turns the question into [0.02, -0.01, ...]
                                  ▼
                       compare with the vector of every row ─► sort by distance ─► .limit(8) ─► to_pandas()
```

Two rules fall out of this picture:

| Rule | Why |
| --- | --- |
| **Use the same model for storing and searching** | Vectors from different models live in different "number worlds". Comparing them is meaningless |
| **Vector length must match** | A table built for 1024 numbers cannot take a 384-number vector |

### Picture D: vector search with 3 numbers (you can do this on paper)

The animals file uses only **3 numbers** per row, so you can see the maths. Think of each animal as a **point in 3D space**. A search is "which points are nearest to my point?"

```
query = [0.5, 0.2, 0.9]

row                                          squared distance to the query        rank
panda    [0.51, 0.37, 0.82]                  0.0001 + 0.0289 + 0.0064 = 0.0354      1  ◄ closest
cheetah  [0.95, 0.12, 0.72]                  0.2025 + 0.0064 + 0.0324 = 0.2413      2
elephant [0.88, 0.22, 0.55]                  0.1444 + 0.0004 + 0.1225 = 0.2673      3
parrot   [0.25, 0.66, 0.81]                  0.2822                                 4
lion     [0.93, 0.18, 0.41]                  0.4254                                 5
frog     [0.14, 0.44, 0.27]                  0.5841                                 6
dog      [0.12, 0.85, 0.33]                  0.8918                                 7
cat      [0.4, 0.91, 0.1]                    1.1541                                 8
```

`.limit(3)` keeps the first three. These are exactly the three rows the notebook shows (`_distance` 0.0354, 0.2413, 0.2673). Notice: `_distance` is the **squared** Euclidean distance (no square root). **Smaller means closer.**

---

## 3. Ideas worth understanding

Keep the notebooks open next to this section.

**The analogy used below:**

| In real life | In the code |
| --- | --- |
| Every place on Earth has GPS coordinates. Near places have near coordinates | A text has a **vector**. Texts with similar meaning have near vectors |
| The mapmaker who turns an address into coordinates | The **embedding model** |
| Asking "what is near this spot?" | `table.search(...)` |
| A book index at the back: look up the exact word | **Full-text search (FTS)** |
| Two mapmakers using different projections | Two embedding models: their numbers cannot be mixed |

### 3.1 Embeddings: GPS coordinates for meaning

An **embedding model** reads a text and outputs a fixed-length list of numbers. Similar meaning gives similar numbers.

| Text | What a good model does |
| --- | --- |
| "Chemists have all the solutions" | Close to "I told a chemistry joke" |
| "kemi" (chemistry in some Scandinavian languages) | Close to the English chemistry jokes, if the model is **multilingual** |
| "give me nature related jokes" | Close to jokes about bears, bugs, frogs, whatever is nearest |

| Model | Vector length | Runs where | Notes |
| --- | --- | --- | --- |
| Hand-made (animals JSON) | 3 | nowhere | Just to learn |
| Cohere `embed-multilingual-light-v3.0` | 1024 | Cohere's servers | Paid API, key `COHERE_API_KEY` |
| `intfloat/multilingual-e5-small` | 384 | your CPU | Free, downloads once |
| NVIDIA `nemotron-3.5-embed-8b` | 4096 (set in the class) | NVIDIA's servers | Key `NVIDIA_API`, our custom class |

You never read the numbers. What matters is the **distance** between two vectors.

### 3.2 Vector search and distance

`table.search(x)` does three things:

1. Turn `x` into a vector (skipped if you pass a vector, as in Picture D).
2. Compute the distance to the vectors in the table.
3. Return the nearest rows, with an extra column `_distance`.

| Fact | Meaning |
| --- | --- |
| `_distance` smaller = more similar | 0 would be identical |
| Default is Euclidean (L2) distance | Straight-line distance in N dimensions |
| `.limit(k)` is "top k" | Without it LanceDB returns a default number of rows |
| It **always** returns k rows | Even when nothing is really related. The "nature jokes" search shows this |

**ANN.** The basics notebook says LanceDB uses **approximate nearest neighbours**. For millions of rows, comparing with every row is too slow, so an **index** finds *nearly* the best rows much faster. With 30 jokes the distinction does not matter. We never create a vector index in this lecture, so LanceDB simply compares all rows, which is fine at this size.

### 3.3 Tables, schemas and versions

A table has **columns with types** (a *schema*). LanceDB can get the schema in two ways:

| Way | Code | When to use |
| --- | --- | --- |
| **From the data** | `db.create_table("animals_text", data=data)` | Quick start. LanceDB guesses: `text` is a string, `vector` is a list of 3 floats |
| **From a class** | `db.create_table("jokes", schema=JokeModel)` | You decide the columns, and can add embedding rules |

The class is a `LanceModel`, which is a **Pydantic** model (lecture 03), so the idea is familiar: a class with typed fields.

```python
class JokeSchema(LanceModel):
    joke: str
    rating: int
```

| Method | What it does |
| --- | --- |
| `db.create_table(name, data=...)` | Create and fill |
| `db.create_table(name, schema=...)` | Create **empty**, with those columns |
| `exist_ok=True` | If the table exists, open it instead of an error (safe to re-run) |
| `mode="overwrite"` | If the table exists, **replace** it (deletes the old data) |
| `table.add(rows)` | Append rows. Each add = a new **version** |
| `db.open_table(name)` | Open an existing table (what you do in a new session) |
| `db.drop_table(name)` | Delete a table. No undo |
| `table.head()`, `.to_pandas()` | Look at the data (pyarrow / pandas) |

> **Data engineer view:** `exist_ok=True` is `CREATE TABLE IF NOT EXISTS`. `mode="overwrite"` is `CREATE OR REPLACE TABLE`. `table.add` is an `INSERT` (append only; every write is a new version).

### 3.4 The embedding registry and SourceField / VectorField

Doing the embedding by hand would be: call the model, get a list, put it in the vector column. LanceDB can do this for you. You describe it **once**, in the schema:

```python
model = get_registry().get("cohere").create(name="embed-multilingual-light-v3.0")

class JokeModel(LanceModel):
    joke: str = model.SourceField()                        # text goes IN here
    vector: Vector(model.ndims()) = model.VectorField()    # numbers come OUT here
```

| Piece | Meaning |
| --- | --- |
| `get_registry()` | LanceDB's catalogue of embedding providers |
| `.get("cohere")` | Pick a provider by name. `"sentence-transformers"` and `"nvidia-nemotron"` are other names used here |
| `.create(name=...)` | Make an instance of it, configured with a model name |
| `model.ndims()` | How long its vectors are. The `Vector(...)` column must match |
| `SourceField()` | "This column is the **input**: embed it" |
| `VectorField()` | "This column is the **output**: store the embedding here" |

After that you only write `table.add(df)` with the text column. LanceDB fills the vector column. For `table.search("text")` it also embeds the question. **That is why the notebook never shows you a vector being created.**

> **Data engineer view:** this is a **computed column** done at write time. The same schema describes how data is enriched on the way in and on the way out.

### 3.5 Three kinds of search

| | **Vector search** | **Full-text search (FTS)** | **Hybrid** |
| --- | --- | --- | --- |
| Matches by | Meaning | Exact words | Both |
| Needs | An embedding model | `create_fts_index("joke")` | Both of the left two |
| Good for | "jokes about nature" | "C#", names, product codes | Mixed, unpredictable questions |
| Weak at | Exact names; always returns something | Different words with the same meaning ("car" vs "automobile") | A bit more work |
| Code | `table.search("text")` | `table.search("text", query_type="fts")` | `query_type="hybrid"` |

(The notebook only runs vector and hybrid search. FTS on its own is shown above for comparison.)

**Hybrid search step by step:**

```
question ──► vector search ──► list 1 (ranked by meaning)  ─┐
         └─► keyword search ─► list 2 (ranked by words)    ─┴─► RRF reranker ──► ONE final list ──► .limit(8)
```

**RRF (Reciprocal Rank Fusion)** merges two ranked lists without needing to compare their different scores. Each row gets `1 / (k + rank)` from each list it appears in, and the scores are added (LanceDB uses a default constant `k` of 60). A made-up example:

| Row | Rank in vector list | Rank in keyword list | Score |
| --- | --- | --- | --- |
| A | 1 | 3 | 1/61 + 1/63 = 0.0323 |
| B | 2 | not found | 1/62 = 0.0161 |
| C | 5 | 1 | 1/65 + 1/61 = 0.0318 |

A is first, C is a close second, B third. **A row that is good in both lists beats a row that is great in only one.**

> **Rule of thumb from the notebook:** exact matching → FTS. Meaning-based matching → vector. Unpredictable or mixed queries → hybrid.

### 3.6 "Passage" vs "query": why the custom class has two methods

Retrieval models like Nemotron are trained to match a **question** with a **document**. A question and its answer do not look alike ("What is the capital of France?" vs "Paris is a city on the Seine..."). So the model wants to know **which side** it is embedding. The API calls this `input_type`:

| When | LanceDB calls | `input_type` |
| --- | --- | --- |
| `table.add(...)` (storing documents) | `compute_source_embeddings` | `"passage"` |
| `table.search("...")` (the question) | `compute_query_embeddings` | `"query"` |

If you used `"passage"` for both, search would still work but less well.

### 3.7 Free vs hosted: which embedder should I pick?

| Question | Local model (`sentence-transformers`) | Hosted API (Cohere, NVIDIA) |
| --- | --- | --- |
| Cost | Free | Pay per use / quota |
| Key needed | No | Yes |
| Privacy | Text stays on your computer | Text is sent over the internet |
| Speed for 30 rows | A few seconds after the first download | One or several network calls |
| Quality | Good for small models | Usually higher with the big models |
| Offline | Yes, after the first download | No |

---

## 4. The files

### 4.1 `lancedb_basics.ipynb` — part 1

The notebook has comments in every code cell, plus a short map at the top. Here it is by theme.

| Part | Code | Meaning |
| --- | --- | --- |
| Connect | `db = lancedb.connect(uri="vector_database")` | Opens the folder, creates it if missing. `db.uri` shows the absolute path |
| Load data | `json.loads(file.read())` | A list of 6 dicts: `{"text": ..., "vector": [3 numbers]}` |
| Create | `db.create_table("animals_text", exist_ok=True, data=data)` | The table is created from the data. Prints `version=1` |
| Look | `table_animals.head()` / `.to_pandas()` | `head()` gives 5 rows as a pyarrow table; `to_pandas()` gives all rows |
| Add | `table_animals.add(more_data)` | Panda and lion are added. `AddResult(version=2)` |
| Empty table | `class JokeSchema(LanceModel)` + `db.create_table(name="jokes", schema=JokeSchema)` | A table with no rows, only columns. Then `drop_table("jokes")` removes it |
| List | `db.table_names()` | Shows tables. **Deprecated**: use `db.list_tables()` |
| Reopen | `db.open_table("animals_text")` | How you get back to the table in a new session |
| Vector search | `table_animals.search([0.5, 0.2, 0.9]).limit(3).to_pandas()` | Picture D |
| Embedding model | `get_registry().get("cohere").create(name="embed-multilingual-light-v3.0")` | **Cohere**, a hosted API (needs `COHERE_API_KEY`) |
| Schema | `JokeModel` with `SourceField` and `VectorField` | Section 3.4 |
| Create `jokes` | `db.create_table("jokes", schema=JokeModel, exist_ok=True)` | An empty table that knows how to embed |
| Load jokes | `pd.DataFrame(jokes_data).rename({"jokes": "joke"}, axis=1)` | One column `jokes` from the JSON, renamed to `joke` to match the schema |
| Fill | `table_jokes.add(df_jokes)` | LanceDB embeds 30 jokes and stores 1024 numbers per joke. `version=2` |
| Check | `table_jokes.head(2)` | Shows `vector: fixed_size_list<item: float>[1024]` |
| Text search | `search("data engineering jokes").limit(8)` | Four searches: data engineering, C#, chemistry, nature |
| FTS index | `table_jokes.create_fts_index("joke", replace=True)` | Builds a keyword index on the text column |
| Hybrid | `search(..., query_type="hybrid", vector_column_name="vector", fts_columns="joke").rerank(RRFReranker()).limit(8)` | Section 3.5 |

**What to look at in the four text searches:**

| Query | What you notice |
| --- | --- |
| "data engineering jokes" | The data lake and pipeline jokes come first: meaning matches |
| "give me jokes on C#" | C# jokes first, then Python jokes: also programming, just further away |
| "give me chemistry related jokes" | Chemistry jokes first, then weaker matches to fill 8 rows |
| "give me nature related jokes" | No joke is really about nature. The order looks loose. That is the weakness the hybrid cell tries to address |

### 4.2 `lancedb_embeddings.ipynb` — part 2

Same idea, different embedding models. Also commented cell by cell.

| Part | Code | Meaning |
| --- | --- | --- |
| Set-up | `pd.read_json("jokes.json")`, `lancedb.connect("knowledge_base")` | A DataFrame with one column `jokes`. A **new** database folder |
| Local model | `get_registry().get("sentence-transformers").create(name="intfloat/multilingual-e5-small", device="cpu")` | Free, 384 numbers, downloads from Hugging Face the first time |
| Schema | `class JokeModel(LanceModel): jokes: str = model.SourceField() ...` | Field is called `jokes` here (not `joke`), so no rename needed |
| Table | `db.create_table("jokes_sentence_transformer", schema=JokeModel)` then `table.add(df)` | Embeds 30 jokes on your CPU |
| Search | `table.search("why do mathematicians have problems?")`, `table.search("kemi ...")` | The second is in another language and still finds chemistry jokes |
| Custom embedder | `from custom_embeddings.nvidia_nemotron import NvidiaNemotronEmbedding` | The import **registers** the class under the name `"nvidia-nemotron"` |
| Create it | `embedding_model = get_registry().get("nvidia-nemotron").create()` | Builds an instance of our class |
| New schema | `class NvidiaJokeModel(LanceModel)` using `embedding_model.SourceField()` and `VectorField()` | A schema tied to the NVIDIA embedder. `JokeModel` cannot be reused: it belongs to the local model (gotcha 1) |
| Table | `db.create_table("jokes_nvidia", schema=NvidiaJokeModel, mode="overwrite")` then `table_jokes.add(df)` | 4096 numbers per joke. `mode="overwrite"` replaces the table if it exists |
| Search | `table_jokes.search("kemi")` | Searches the NVIDIA table |
| Last cell | `table_jokes.search("why do mathematicians ...")` | Same question as the e5 search, now on the NVIDIA table, so you can compare the models |

### 4.3 `custom_embeddings/nvidia_nemotron.py` — your own embedder

Read the docstrings in the file: it has a module docstring that draws the flow.

| Lines | Code | Meaning |
| --- | --- | --- |
| 42 to 46 | imports | `OpenAI` (the NVIDIA API speaks the OpenAI protocol), `TextEmbeddingFunction` and `get_registry` from LanceDB, `numpy` |
| 49 | `load_dotenv()` | Reads `.env` so `NVIDIA_API` exists |
| 53 to 58 | `client = OpenAI(base_url=..., api_key=os.getenv("NVIDIA_API"), max_retries=3, timeout=60.0)` | **Runs at import.** One shared connection to `integrate.api.nvidia.com/v1` |
| 63 | `@get_registry().register("nvidia-nemotron")` | **Runs at import.** Adds the class to the registry under that name |
| 64 | `class NvidiaNemotronEmbedding(TextEmbeddingFunction)` | Inherits LanceDB's base class for text embedders |
| 74 to 75 | `model = "nvidia/nemotron-3.5-embed-8b"`, `dimensions = 4096` | Settings. `dimensions` must match the real vector length |
| 77 | `ndims()` | Tells LanceDB the vector length, so the table column becomes `Vector(4096)` |
| 85 | `_embed_one(text, input_type)` | The only method that talks to the API. Sends one text, converts the answer to a `float32` numpy array |
| 101 | `generate_embeddings(texts)` | Required by the base class. Embeds a list of texts as `"passage"`, one API call each |
| 110 | `compute_source_embeddings(texts)` | What LanceDB calls on `table.add(...)` |
| 114 | `compute_query_embeddings(query)` | What LanceDB calls on `table.search(...)`. Uses `"query"` |

**Import-time code again.** Like `model.py` in earlier lectures, lines 49, 53 and 63 run the moment the file is imported. If `NVIDIA_API` is missing, the `OpenAI(...)` call fails right there, before any embedding.

**Why this file is a good template.** To add *any* embedding service to LanceDB you need only: a class that extends `TextEmbeddingFunction`, the `@register("name")` decorator, `ndims()`, and one method that returns a list of vectors. Everything else in LanceDB then works with it.

### 4.4 The two JSON files

| File | Shape | Used by |
| --- | --- | --- |
| [animals_text_embeddings.json](animals_text_embeddings.json) | A **list** of objects: `[{"text": "...", "vector": [a, b, c]}, ...]` (6 rows) | Basics notebook, vector search with fake 3-number vectors |
| [jokes.json](jokes.json) | An **object** with one key: `{"jokes": ["...", "..."]}` (30 strings) | Both notebooks. `pandas` turns it into one column called `jokes` |

Why the shapes differ: a list of dicts maps directly to table rows (`create_table(data=...)` accepts it). `jokes.json` has one key holding a list, so pandas makes a one-column DataFrame, and the column name comes from the key.

---

## 5. Setup and running

### One-time setup

1. **Install the packages** (the README gives this):

   ```bash
   uv add lancedb sentence-transformers cohere
   ```

   | Package | What it gives you |
   | --- | --- |
   | `lancedb` | The vector database |
   | `sentence-transformers` | The free local embedding model (the original README line missed the final `s`) |
   | `cohere` | The client used by LanceDB's Cohere embeddings |

2. **Create a Cohere key** ([dashboard](https://dashboard.cohere.com/api-keys)) and put it in `.env`. For part 2 also keep the NVIDIA key you already use:

   ```env
   COHERE_API_KEY=your_cohere_key_here
   NVIDIA_API=your_nvidia_key_here
   ```

   Never commit `.env`. It is already in the repo's `.gitignore`.

### Every time you run it

1. Open the notebook in VS Code, choose the project's `.venv` as kernel.
2. Run the cells from top to bottom.

| What you should see | Meaning |
| --- | --- |
| `LanceDBConnection(uri='.../09_lancedb/vector_database')` | The database folder exists now |
| `LanceTable(name='animals_text', version=1, ...)` | The table was created |
| `AddResult(version=2)` | Rows were added; the table is now at version 2 |
| A `_distance` column in search results | Smaller is closer |
| New folders `vector_database/` and `knowledge_base/` | Your data. Delete them to start from scratch |

The saved outputs in the notebooks come from the lecturer's machine (paths like `/Users/aigineer/...`). Yours will have your own paths.

---

## 6. Gotchas and things to improve

### Fixed in this version (good to know why they happened)

| # | What was wrong | Why it matters | Fix now in the notebooks |
| --- | --- | --- | --- |
| 1 | **`jokes_nvidia` did not use NVIDIA.** `embedding_model` was created, but the table used `schema=JokeModel`, which is tied to the **local** `model` | The schema decides which embedder runs. Creating an embedder object does nothing until a schema uses it. The table silently held 384-number e5 vectors | New class `NvidiaJokeModel` using `embedding_model.SourceField()` and `VectorField()` |
| 2 | The last cell searched `table`, not `table_jokes` | It repeated an old search, so the NVIDIA table was never tested | It now searches `table_jokes` |
| 3 | The markdown said "sentence-transformer", the cell used Cohere | Misleading: you need `COHERE_API_KEY` | Markdown corrected |
| 4 | `open("jokes.json", "r")` crashed on Windows: `UnicodeDecodeError: 'charmap' codec can't decode byte 0x9d` | Without `encoding="utf-8"` Python uses `cp1252`, and `jokes.json` has curly quotes. Same lesson as `export_report` in lectures 07 and 08 | `open("jokes.json", "r", encoding="utf-8")` |
| 5 | Packages missing from `pyproject.toml` | A fresh clone fails with `ModuleNotFoundError` | `uv add lancedb sentence-transformers cohere` (also updates `uv.lock`) |
| 6 | Data folders not in `.gitignore` | You could commit generated data | `09_lancedb/vector_database/` and `09_lancedb/knowledge_base/` added |

**How to check fix 1 yourself:** `table_jokes.schema` must show `fixed_size_list<item: float>[4096]`, not `[384]`.

### Still true

1. **Column names must match.** The DataFrame column must have the same name as the schema's text field (`joke` in notebook 1 after the rename, `jokes` in notebook 2).
2. **No `load_dotenv()` in the notebooks.** The key must already be in the environment. If `COHERE_API_KEY` is "missing", add `from dotenv import load_dotenv; load_dotenv()` in the first cell. (The `.env` in this repo currently has only `NVIDIA_API`.)
3. **Re-running cells.** `create_table("jokes_sentence_transformer", schema=JokeModel)` has no `exist_ok`, so a second run raises "table already exists". Use `exist_ok=True` or `mode="overwrite"`. Careful: re-running `table.add(df)` on a table you did not overwrite **adds the 30 jokes again** (duplicates).
4. **Embedding calls cost something.** Every `add` on the Cohere or NVIDIA tables is a network call and uses quota. Re-running the notebook re-embeds.
5. **NVIDIA embedding is one call per text** (`input=[text]`). For thousands of rows send a batch of texts in one call.
6. **Vector search never says "no match".** It returns the *nearest* k rows, however far. For a real app, look at `_distance` and decide a cut-off.
7. **Old outputs.** The saved outputs come from the lecturer's Mac, and the NVIDIA table cells were changed after they were saved. Re-run to refresh them.

### What I tested

| Checked | Result |
| --- | --- |
| Packages installed with `uv add` | OK |
| Animals vector search with 3-number vectors | Same top 3 and `_distance` values as the notebook (0.0354, 0.2413, 0.2673) |
| `NvidiaNemotronEmbedding` with the real NVIDIA API (2 short texts, in a scratch folder) | Worked. The table column is `fixed_size_list<item: float>[4096]`; searching `"kemi"` ranked the chemistry joke first |
| The Cohere cells, the local e5 model, and the notebooks end to end | **Not run**: no Cohere key, and I did not download the e5 model |

---

## 7. Glossary

| Term | Meaning |
| --- | --- |
| **Vector** | A list of numbers. Here: the meaning of a text |
| **Embedding** | A vector made from a text (also: the act of making it) |
| **Embedding model** | The AI model that turns text into a vector |
| **Dimensions** | The length of a vector. Fixed per model (3, 384, 1024, 4096 here) |
| **Vector database** | A database that can find the rows whose vectors are nearest to a query vector |
| **LanceDB** | An open-source, embedded vector database that stores data in Lance files in a folder |
| **Embedded database** | Runs inside your program. No server. Like SQLite or DuckDB |
| **Table** | Rows and typed columns. In LanceDB a folder ending in `.lance` |
| **Schema** | The column names and types of a table |
| **`LanceModel`** | A Pydantic model that LanceDB uses as a table schema |
| **`SourceField`** | Marks the column whose text is embedded |
| **`VectorField`** | Marks the column where the embedding is stored |
| **Registry** | LanceDB's catalogue of embedding providers: `get_registry().get("name")` |
| **Version** | A numbered snapshot of a table. Every write makes a new one |
| **Distance (`_distance`)** | How far two vectors are. Smaller = more similar. Here: squared Euclidean |
| **ANN** | Approximate nearest neighbours: a fast, nearly exact search using an index |
| **Top-k / `.limit(k)`** | Keep only the k best rows |
| **FTS** | Full-text search: keyword search over an index of words |
| **Hybrid search** | Vector search and FTS together, merged by a reranker |
| **Reranker** | A step that reorders or merges result lists |
| **RRF** | Reciprocal Rank Fusion: score `1 / (k + rank)` per list, added up |
| **Passage / query** | The two `input_type`s of a retrieval embedding model: a stored document and a search question |
| **RAG** | Retrieval-Augmented Generation: find relevant text first, then give it to the model. Built on this lecture |
| **Hugging Face** | A website that hosts open models. `sentence-transformers` downloads from it |
| **pyarrow** | The columnar table format returned by `table.head()` |

---

## 8. My questions

Write your own questions here as you study, and answer them when you find out.

- 
- 
- 
