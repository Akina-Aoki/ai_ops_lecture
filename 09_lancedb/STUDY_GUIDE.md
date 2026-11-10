# Study guide: 09 LanceDB (vector database, embeddings, hybrid search)

| When you are reading... | Read this section |
| --- | --- |
| The big idea | [1. The 30-second version](#1-the-30-second-version) and [2. The pictures](#2-the-pictures-to-understand) |
| Words like vector, embedding, distance | [3.1](#31-embeddings-gps-coordinates-for-meaning) and [3.2](#32-vector-search-and-distance) |
| Tables, schemas, `SourceField` | [3.3 Tables](#33-tables-schemas-and-versions) and [3.4 Embedding registry](#34-the-embedding-registry-and-sourcefield--vectorfield) |
| Keyword vs vector vs hybrid | [3.5](#35-three-kinds-of-search) |
| `lancedb_basics.ipynb` | [4.1](#41-lancedb_basicsipynb--part-1) |
| `lancedb_embeddings.ipynb` | [4.2](#42-lancedb_embeddingsipynb--part-2) |
| `custom_embeddings/nvidia_nemotron.py` | [4.3 line table](#43-custom_embeddingsnvidia_nemotronpy--your-own-embedder) and the step-by-step [4.5 Deep dive](#45-deep-dive-understanding-nvidia_nemotronpy) |
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

This is the hardest file of the lecture if embeddings and vectors are new to you. So this section goes slowly: first **what an embedding is, in data terms**, then **what the file does in plain words**, then the **line-by-line reference table**. Read in that order.

| Part | What you get |
| --- | --- |
| [A. What is an embedding?](#a-what-is-an-embedding-in-data-terms) | The idea, with a tiny example you can check by hand |
| [B. Where the file sits in the pipeline](#b-where-the-file-sits-in-the-pipeline) | The file is the **Transform** step of an ETL |
| [C. The file in plain words](#c-the-file-in-plain-words) | Each piece, explained as a data concept |
| [D. Reference: the line table](#d-reference-the-line-table) | Line numbers and meaning (the original table) |
| [E. Questions beginners ask](#e-questions-beginners-ask) | The "but why?" answers |

For an even slower walk through the Python side (decorator, inheritance, who calls what, how to test it), read [4.5 Deep dive](#45-deep-dive-understanding-nvidia_nemotronpy) afterwards.

#### A. What is an embedding, in data terms

**The problem.** A computer can compare numbers easily (`5 < 7`) and can check if two strings are *equal* (`"cat" = "cat"`). But it cannot tell that `"kitten"` is *about the same thing* as `"cat"`, or that `"invoice"` is about something else. A `WHERE text = 'cat'` filter misses `"kitten"`.

**The fix.** Turn each text into a **row of numbers** (a *vector*, in SQL terms an array column like `FLOAT[4096]`) so that:

> texts with **similar meaning** get **similar numbers**, and texts with different meaning get different numbers.

The function that does this is called an **embedding model**. You give it text, it gives back an array of numbers. That output array is the **embedding**.

| Data word | In this lecture |
| --- | --- |
| Input column | `jokes` (text) |
| Transformation function (think of a UDF) | the embedding model |
| Output column | `vector` (an array of `FLOAT`, here 4096 numbers) |
| "Feature" (as in machine learning) | the vector: numbers that describe the text so a computer can compare it |

**A tiny example you can check by hand.** Pretend the model only used **3 numbers** (real models use hundreds or thousands; the numbers are made up):

| Text | Vector (3 numbers) |
| --- | --- |
| `"cat"` | `[0.90, 0.80, 0.10]` |
| `"kitten"` | `[0.85, 0.75, 0.15]` |
| `"invoice"` | `[0.10, 0.20, 0.95]` |

You can see by eye that `cat` and `kitten` are close, and `invoice` is far from both. LanceDB measures that with a **distance** (smaller = more similar):

| Pair | Calculation (squared difference per position, added up) | Distance |
| --- | --- | --- |
| cat ↔ kitten | 0.05² + 0.05² + 0.05² = 0.0025 + 0.0025 + 0.0025 | **0.0075** (very close) |
| cat ↔ invoice | 0.80² + 0.60² + 0.85² = 0.6400 + 0.3600 + 0.7225 | **1.7225** (far) |

That is all "search by meaning" is: **turn the question into numbers too, then return the rows with the smallest distance**. (The animals example in Picture D does exactly this.)

**Three things to remember.**

| Idea | Why it matters |
| --- | --- |
| **You never read the numbers.** Number 17 of 4096 does not mean "is it an animal" | Only the *distance between two vectors* means something |
| **It is not a hash.** A hash makes `cat` and `kitten` totally different, on purpose. An embedding does the opposite: similar meaning, similar numbers | That is why it can power search |
| **Only compare vectors from the same model.** Each model has its own "number language" | Store with NVIDIA, search with NVIDIA. Never mix |

> **Data engineer view:** a normal column lets you join on **equality**. An embedding column lets you join on **closeness**. It is the same table and the same SQL ideas, with `ORDER BY distance(vector, :query) LIMIT k` instead of `WHERE text = :x`.

**Size matters (storage maths).** Each number is a `float32` = 4 bytes. One row's vector is `dimensions × 4` bytes:

| Model | Numbers per row | Bytes per row | 30 jokes | 1,000,000 rows |
| --- | --- | --- | --- | --- |
| Hand-made animals | 3 | 12 B | tiny | 12 MB |
| Local e5-small | 384 | 1,536 B | ~46 KB | ~1.5 GB |
| Cohere light | 384 or 1024 (depends on your LanceDB version) | 1.5 to 4 KB | ~46 to 123 KB | ~1.5 to 4 GB |
| NVIDIA Nemotron (this file) | 4096 | 16,384 B (16 KB) | ~480 KB | **~16 GB** |

Bigger vectors can capture finer detail, but cost more to store, move and compare. That is a real data-engineering trade-off.

#### B. Where the file sits in the pipeline

Think of the whole lecture as an **ETL**:

```
EXTRACT                 TRANSFORM                                        LOAD
jokes.json  ──►  pandas DataFrame  ──►  [ embedding step ]  ──►  LanceDB table
(30 texts)       (column "jokes")        NVIDIA turns each         (columns: jokes, vector)
                                         text into 4096 numbers
                                                 ▲
                                                 │
                              THIS FILE: nvidia_nemotron.py
```

`nvidia_nemotron.py` is **only the Transform step**. It does not store anything and it does not search anything. LanceDB does those. The file answers one question for LanceDB: *"how do I turn text into numbers using NVIDIA?"*

Important: **the embedding model itself is not in this file.** It runs on NVIDIA's servers. The file only *calls* it over the internet (an API call), like calling an external transformation service. So the file is a thin wrapper.

LanceDB uses the wrapper at two moments:

| Moment | You write | LanceDB calls | It is like... |
| --- | --- | --- | --- |
| **Writing** the table | `table.add(df)` | `compute_source_embeddings` | The transform step of a **load** job, run on every new row |
| **Reading** the table | `table.search("kemi")` | `compute_query_embeddings` | The same transform, applied to the **search question** so it can be compared with the stored rows |

#### C. The file in plain words

Here is each piece of the file with a data-concept translation. (Line numbers are in section D.)

| Piece of the file | Plain words | Data concept |
| --- | --- | --- |
| `load_dotenv()` | Read the password file | Load **credentials** from config, not from the code |
| `client = OpenAI(base_url=..., api_key=...)` | Open one connection to NVIDIA's server, with retries and a timeout | A **connection / client object**, created once and reused, like a database connection |
| `class NvidiaNemotronEmbedding(TextEmbeddingFunction)` | "I am a kind of text-embedder; LanceDB already knows how to use those" | A **subclass that implements an interface**. LanceDB defines the shape; we fill in the NVIDIA part |
| `@get_registry().register("nvidia-nemotron")` | "Write my name in LanceDB's directory so it can find me" | **Registering a connector** under a key (like adding a source type to a config) |
| `model = "nvidia/nemotron-3.5-embed-8b"` | Which NVIDIA model to call | A **parameter** of the transform |
| `dimensions = 4096` | How long the output array is | The **declared output schema**: `FLOAT[4096]` |
| `ndims()` | Tell LanceDB the length | LanceDB uses it to build the **column type** of `vector` |
| `_embed_one(text, input_type)` | Send **one** text, get **one** array back | The **row-level transform**; the only place that does I/O |
| `generate_embeddings(texts)` | Do `_embed_one` for every text in the list | A **batch loop** over rows |
| `compute_source_embeddings` | The entry LanceDB uses when **writing** | The "on insert" hook |
| `compute_query_embeddings` | The entry LanceDB uses when **searching** | The "on query" hook |

**Follow one joke through the file.** Say you run `table_jokes.add(df)` and the first joke is `"Never trust an atom, they make up everything."`

```
1. LanceDB:   "this column is a SourceField, I need vectors for it"
              └─► compute_source_embeddings(["Never trust an atom...", ...30 jokes...])
2. our file:  generate_embeddings(texts)  ── loops over the 30 texts
              └─► _embed_one("Never trust an atom...", input_type="passage")
3. our file:  client.embeddings.create(model="nvidia/nemotron-3.5-embed-8b", input=[the text], ...)
              └─► HTTPS request to NVIDIA  ──►  NVIDIA runs the model  ──►  returns 4096 numbers
4. our file:  convert the list to a numpy float32 array of shape (4096,)
5. LanceDB:   writes the row:  jokes = "Never trust an atom...",  vector = [4096 numbers]
```

And one search, `table_jokes.search("kemi")`:

```
1. LanceDB:   compute_query_embeddings("kemi")
2. our file:  _embed_one("kemi", input_type="query")  ──►  NVIDIA  ──►  4096 numbers
3. LanceDB:   compares that array with the vector of every row, returns the nearest rows
```

**"passage" vs "query" in one line.** NVIDIA's model wants to know whether it is embedding a **stored document** (`"passage"`) or a **question** (`"query"`), because a question and its answer look very different. When I embedded the word "hello" both ways, the two vectors were **not identical** (cosine similarity about 0.75), which shows the flag really changes the result. So store with `"passage"`, search with `"query"`, and the model lines them up.

#### D. Reference: the line table

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

#### E. Questions beginners ask

| Question | Answer |
| --- | --- |
| Is this file the embedding model? | **No.** The model runs on NVIDIA's servers. This file is a small wrapper that calls it and hands the result to LanceDB |
| Why 4096 numbers? | The model was designed to output 4096. We just declare it in `dimensions` so LanceDB knows. More numbers = more detail but more storage (see the table in A) |
| Can I look at the numbers and understand them? | No. A single number has no meaning you can name. Only the distance between two vectors is meaningful |
| Why do I need a custom class at all? | LanceDB has built-in embedders for some providers, but not for this NVIDIA model. The class is the adapter that fills the gap |
| Why does the notebook import the class but never use its name? | The import runs `@register(...)`, which adds `"nvidia-nemotron"` to LanceDB's directory. Without the import, `get_registry().get("nvidia-nemotron")` fails |
| Does the table store the original text too? | Yes. A row has the text column **and** the vector column. The vector is only used to find the row; you still read the text |
| Why does `add` take a while? | One API call per text (see `_embed_one`). 30 jokes = 30 calls |
| Why must I search with the same model I stored with? | Each model has its own "number language". Comparing numbers from two different models is meaningless, like comparing kilometres with Fahrenheit |
| What does LanceDB do with `float32`? | It stores each number as 4 bytes. That is why we convert the API's Python list to a `float32` array |
| What if I change `dimensions`? | Only the declaration changes, not what NVIDIA returns. If they disagree, the table cannot store the vectors. Keep it equal to the model's real output length (4096) |

### 4.4 The two JSON files

| File | Shape | Used by |
| --- | --- | --- |
| [animals_text_embeddings.json](animals_text_embeddings.json) | A **list** of objects: `[{"text": "...", "vector": [a, b, c]}, ...]` (6 rows) | Basics notebook, vector search with fake 3-number vectors |
| [jokes.json](jokes.json) | An **object** with one key: `{"jokes": ["...", "..."]}` (30 strings) | Both notebooks. `pandas` turns it into one column called `jokes` |

Why the shapes differ: a list of dicts maps directly to table rows (`create_table(data=...)` accepts it). `jokes.json` has one key holding a list, so pandas makes a one-column DataFrame, and the column name comes from the key.

### 4.5 Deep dive: understanding `nvidia_nemotron.py`

This is the only Python file of the lecture. It is short (about 120 lines, most of them comments), but it uses four ideas that are new to many beginners: a **class that extends another class**, a **decorator**, **import-time code**, and a **contract** with LanceDB. This section walks through them one at a time. Keep [custom_embeddings/nvidia_nemotron.py](custom_embeddings/nvidia_nemotron.py) open next to it.

#### Step 0: the problem it solves

| LanceDB says... | NVIDIA says... |
| --- | --- |
| "I know Cohere, sentence-transformers, Gemini... but not NVIDIA Nemotron." | "Call me like you would call OpenAI: `client.embeddings.create(...)`." |

The file is a **travel adapter** between the two:

```
 LanceDB plug                     the adapter                     NVIDIA socket
 (table.add / table.search)  ──►  NvidiaNemotronEmbedding  ──►   integrate.api.nvidia.com/v1
 "give me vectors for these       translates the request          returns 4096 numbers per text
  texts"                          and the answer
```

> **Data engineer view:** this is a **connector / adapter class**. Same pattern as a custom Airflow operator, a Spark data source or a dbt adapter: the framework defines an interface, you implement it for a new system, then you register it so the framework can find it.

#### Step 1: the five blocks of the file

Read the file as five blocks, top to bottom. This is also the order they run in when the file is imported.

| Block | Lines | What it is | Runs when |
| --- | --- | --- | --- |
| 1. Imports | 42 to 46 | Tools the file needs | at import |
| 2. `load_dotenv()` | 49 | Puts the keys from `.env` into the environment | at import |
| 3. `client = OpenAI(...)` | 53 to 58 | One shared connection to the NVIDIA API | at import |
| 4. Decorator + class header | 63 to 64 | Registers the class in LanceDB under a name | at import |
| 5. Settings and methods | 74 to 120 | The real work: turn text into vectors | only when LanceDB **calls** them |

Blocks 1 to 4 run **once, the moment the notebook does `from custom_embeddings.nvidia_nemotron import ...`**. Block 5 only *defines* the methods. They run later, on `table.add(...)` and `table.search(...)`.

##### Block 1 and 2: imports and `.env`

```python
from openai import OpenAI
from lancedb.embeddings import TextEmbeddingFunction, get_registry
import numpy as np
load_dotenv()
```

| Import | Why it is here |
| --- | --- |
| `OpenAI` | NVIDIA's API copies the OpenAI format, so we reuse OpenAI's Python client. Same trick as `model.py` in lectures 01 to 08 |
| `TextEmbeddingFunction` | LanceDB's **base class** for text embedders. We build on top of it |
| `get_registry` | LanceDB's catalogue of embedders, used by the decorator |
| `numpy` | The vectors are stored as arrays of `float32` |
| `load_dotenv()` | Reads `.env`, so `NVIDIA_API=...` becomes available through `os.getenv("NVIDIA_API")` |

##### Block 3: the client

```python
client = OpenAI(
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=os.getenv("NVIDIA_API"),
    max_retries=3,
    timeout=60.0,
)
```

| Argument | Meaning |
| --- | --- |
| `base_url` | "Send my OpenAI-style requests to NVIDIA's server instead of OpenAI's" |
| `api_key` | Your key, read from `.env`. Never type a key into code |
| `max_retries=3` | If a request fails for a temporary reason (network hiccup, rate limit), try again up to 3 times |
| `timeout=60.0` | Give up on one request after 60 seconds |

It is created **once, at the top level**, and shared by every call. Opening a connection once and reusing it is cheaper than opening one per text. It is outside the class, so all instances use the same one.

##### Block 4: the decorator (how LanceDB finds your class)

```python
@get_registry().register("nvidia-nemotron")
class NvidiaNemotronEmbedding(TextEmbeddingFunction):
```

Two different things happen in these two lines:

| Part | Plain English |
| --- | --- |
| `class NvidiaNemotronEmbedding(TextEmbeddingFunction)` | "Make a new class that **inherits** from `TextEmbeddingFunction`." We get all of LanceDB's text-embedder machinery for free, and only fill in the parts that are specific to NVIDIA |
| `@get_registry().register("nvidia-nemotron")` | "Write this class into LanceDB's phone book under the name `nvidia-nemotron`." A **decorator** is a function that wraps the thing under it. Here it registers the class and returns it |

That is why the notebook can later write `get_registry().get("nvidia-nemotron").create()`: it asks the phone book for the name, gets the class, and `.create()` builds an object from it. **If you never import this file, the name is never registered, and `get("nvidia-nemotron")` fails.** That is the reason the notebook imports a class it never uses by name.

> **Data engineer view:** `register("name")` is like registering a plugin in an entry-point table, or adding a connector type to a config. The string `"nvidia-nemotron"` is the key you use later in config or code.

##### Block 5a: the settings

```python
model: str = "nvidia/nemotron-3.5-embed-8b"
dimensions: int = 4096
```

These are **fields** of the class (the base class is built on Pydantic, like the models in lecture 03). They are settings with defaults:

| Field | Meaning | Careful |
| --- | --- | --- |
| `model` | Which NVIDIA model to call | It must be a model name your key can use. A wrong name gives an API error (see the error table below) |
| `dimensions` | How many numbers each vector has | **You** declare it, the code does not check it. If it differs from what the API really returns, the table will refuse the data |

##### Block 5b: the five methods

| Method | Who calls it | Job | In one line |
| --- | --- | --- | --- |
| `ndims()` | LanceDB, once, when the table schema is built | Says how long vectors are | `return self.dimensions` |
| `_embed_one(text, input_type)` | our own methods | **The only method that talks to the network.** One text in, one vector out | the workhorse |
| `generate_embeddings(texts)` | `compute_source_embeddings` | Loop over the texts, embed each as `"passage"` | required by the base class |
| `compute_source_embeddings(texts)` | LanceDB on `table.add(...)` | Embed the **documents** you store | calls `generate_embeddings` |
| `compute_query_embeddings(query)` | LanceDB on `table.search("...")` | Embed the **question** | same, with `"query"` |

The leading underscore in `_embed_one` is a Python habit: "this is an internal helper, not meant to be called from outside the class".

**Look closely at `_embed_one`, the heart of the file:**

```python
response = client.embeddings.create(
    model=self.model,                       # which NVIDIA model
    input=[text],                           # a list with ONE text
    extra_body={"input_type": input_type},  # "passage" or "query"
)
vector = np.asarray(response.data[0].embedding, dtype=np.float32)
return vector
```

| Line | What it does |
| --- | --- |
| `self.model` | The value of the `model` field above |
| `input=[text]` | The API wants a **list** of texts. We send a list of one |
| `extra_body={...}` | The OpenAI client only knows standard options. `input_type` is a NVIDIA extra, so we slip it into the request body through `extra_body` |
| `response.data[0].embedding` | The answer is a list with one item per input text. We sent one text, so we take item `0`. `.embedding` is a plain Python list of 4096 floats |
| `np.asarray(..., dtype=np.float32)` | Convert to a numpy array of 32-bit floats. LanceDB stores `float32` columns |

#### Step 2: who calls what (follow one `table.add` and one `table.search`)

```
table_jokes.add(df)                                 ← in the notebook
   │  LanceDB sees: column "jokes" is a SourceField, column "vector" is a VectorField
   ▼
compute_source_embeddings(["joke 1", "joke 2", ...])
   ▼
generate_embeddings(texts)                          ← sanitize_input() cleans the list first
   ▼
[ _embed_one("joke 1", "passage"), _embed_one("joke 2", "passage"), ... ]   ← 1 API call per joke
   ▼
list of numpy arrays, each with 4096 float32  ──►  stored in the "vector" column


table_jokes.search("kemi")                          ← in the notebook
   ▼
compute_query_embeddings("kemi")                    ← sanitize_input() turns "kemi" into ["kemi"]
   ▼
[ _embed_one("kemi", "query") ]                     ← 1 API call
   ▼
one vector with 4096 numbers  ──►  LanceDB compares it with every stored vector  ──►  nearest rows
```

For the 30 jokes that is **30 API calls on `add`** and **1 on each `search`**.

#### Step 3: a worked example with shapes

| Step | What you write | What you get |
| --- | --- | --- |
| Texts in | `["Never trust an atom", "ETL stands for..."]` | a list of 2 strings |
| `_embed_one` for the first | `_embed_one("Never trust an atom", "passage")` | an array of shape `(4096,)`, dtype `float32` |
| `generate_embeddings` | `generate_embeddings(texts)` | a list of 2 arrays, each `(4096,)` |
| Stored in the table | the `vector` column | type `fixed_size_list<item: float>[4096]` |
| Query in | `compute_query_embeddings("kemi")` | a list of 1 array `(4096,)` |

**Why the lengths must match:** the `vector` column was created with room for exactly `ndims()` = 4096 numbers. A vector of any other length cannot be stored, and the query vector has to have the same length as the stored ones to be compared.

#### Step 4: try it yourself in a notebook cell

Run this in a new cell of `lancedb_embeddings.ipynb`. It costs **one** API call and does not touch any table:

```python
from custom_embeddings.nvidia_nemotron import NvidiaNemotronEmbedding
from lancedb.embeddings import get_registry

embedder = get_registry().get("nvidia-nemotron").create()

print(embedder.ndims())                                   # 4096
vectors = embedder.compute_query_embeddings("hello")      # a list with one array
print(len(vectors), vectors[0].shape, vectors[0].dtype)   # 1 (4096,) float32
```

When I tested this class against the real NVIDIA API, the table column was `[4096]` and search worked, so the numbers above are what you should expect. Then try `compute_source_embeddings("hello")` and compare it with the query vector for the same word. They are **not identical**, because of `"passage"` vs `"query"`.

#### Step 5: why two input types again

| | `"passage"` | `"query"` |
| --- | --- | --- |
| Used for | the documents you store | the question a user types |
| Method | `compute_source_embeddings` | `compute_query_embeddings` |
| Happens | on `table.add` | on `table.search` |

A question ("jokes about chemistry?") and its answer ("Never trust an atom") do not look alike. A retrieval model is trained to put a question near its matching documents, but it needs to know which side it is looking at.

#### Step 6: things that go wrong

| What you see | Likely cause | Fix |
| --- | --- | --- |
| An error right when you run the import cell, mentioning the `api_key` | `NVIDIA_API` is missing, so `OpenAI(api_key=None)` is built at import | Put `NVIDIA_API=...` in `.env` and restart the kernel |
| `ModuleNotFoundError: custom_embeddings` | The notebook is not running from `09_lancedb/` | Open the notebook from this folder |
| `ModuleNotFoundError` for `lancedb`, `openai` or `dotenv` | Wrong kernel | Select the project's `.venv` |
| `401` / authentication error | Wrong or expired key | Create a new key and update `.env` |
| `404` / model not found | `model` is not a model your key can call | Check the model name on build.nvidia.com |
| A vector-length / schema error on `add` | `dimensions` (4096) differs from what the model returns | Set `dimensions` to the real length |
| `get("nvidia-nemotron")` fails | The file was never imported, so the name is not registered | Import the class first |
| Very slow `add` | One API call per text | Fine for 30 jokes. For thousands, batch the texts into one call |
| Timeouts or rate-limit errors | Too many calls, or slow network | `max_retries=3` already retries. Try fewer rows at a time |

#### Step 7: reuse it as a template for another provider

To add a different embedding service to LanceDB, copy the file and change only these parts:

| Part | Change it to |
| --- | --- |
| `client = ...` | The new provider's client and key |
| `register("...")` | A new name, for example `"my-embedder"` |
| `class ...` | A new class name |
| `model`, `dimensions` | The new model and its real vector length |
| `_embed_one` | The new provider's call. Return a `float32` numpy array |
| `compute_query_embeddings` | Keep the `"query"` idea only if the provider has one |

Everything else (`ndims`, the loop in `generate_embeddings`, the two `compute_*` methods) stays the same.

#### Check yourself

| Question | Answer |
| --- | --- |
| Which lines run when the file is **imported**? | `load_dotenv()`, `client = OpenAI(...)`, and the decorator that registers the class |
| Which method is the only one that uses the network? | `_embed_one` |
| How many API calls does `table.add` make for 30 jokes? | 30 (one per text) |
| Why does the notebook import `NvidiaNemotronEmbedding` without using it by name? | The import runs the decorator, which registers `"nvidia-nemotron"` |
| What happens if `dimensions` is wrong? | The table cannot store the vectors, or queries cannot be compared |
| Why `float32`? | LanceDB stores `float32` vectors |

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
| **Decorator** | A line starting with `@` above a function or class. It wraps it. `@get_registry().register("nvidia-nemotron")` adds our class to LanceDB's registry |
| **Inheritance** | `class A(B)`: A gets everything B has and only adds or changes parts. Here `NvidiaNemotronEmbedding(TextEmbeddingFunction)` |
| **Adapter / connector class** | A class that translates between a framework's interface and an outside service. `nvidia_nemotron.py` is one |
| **`input_type`** | NVIDIA's extra request field: `"passage"` for stored documents, `"query"` for search questions |
| **pyarrow** | The columnar table format returned by `table.head()` |

---

## 8. My questions

Write your own questions here as you study, and answer them when you find out.

- 
- 
- 
