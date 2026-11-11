# LanceDB lecture 09: slide-by-slide lesson (code on every slide)

AUDIENCE: a junior data engineer (beginner to intermediate). First time with embeddings and vectors.
HOW TO USE THIS SOURCE: this document IS the lesson. It has 32 slides. Make ONE video slide per "SLIDE" below, in the same order. On every slide that has a "CODE" block, show that code on screen, exactly as written, in a monospace code box, and read the explanation next to it. On every slide that has an "OUTPUT" block, show that output on screen as a table or code box. Do not replace code with a summary. Do not skip slides. Do not invent code, numbers or outputs that are not in this document.
All outputs below come from a real run of the notebooks.

---

## PART 1. THE IDEA

### SLIDE 1. Title and the whole pipeline
ON SCREEN: the architecture picture (architecture_9.png) and this line:
text -> embedding model -> vector -> LanceDB table -> search by meaning
SAY: Today we store our own text in a database and search it by meaning, not by spelling. This is the foundation for RAG. We will go file by file: two JSON files, two notebooks (lancedb_basics.ipynb, lancedb_embeddings.ipynb), and one Python file (custom_embeddings/nvidia_nemotron.py).

### SLIDE 2. The problem
ON SCREEN (two lines, side by side):
User question: "How do I get my money back?"
Document title: "Refund policy"
SAY: SQL "WHERE text = ..." or LIKE matches the same words. These two share no words, but they mean the same. We need search by meaning.

### SLIDE 3. What an embedding is
ON SCREEN (table, made-up numbers, 3 numbers only to teach):
text      | vector
cat       | [0.90, 0.80, 0.10]
kitten    | [0.85, 0.75, 0.15]
invoice   | [0.10, 0.20, 0.95]
distance cat-kitten  = 0.05^2 + 0.05^2 + 0.05^2 = 0.0075   (very close)
distance cat-invoice = 0.80^2 + 0.60^2 + 0.85^2 = 1.7225   (far)
SAY: An embedding is a list of numbers that represents the meaning of a text. Similar meaning gives similar numbers. Smaller distance means more similar. In data terms: a normal column lets you join on equality; an embedding column lets you join on closeness. It is not a hash (a hash makes cat and kitten completely different). You never read the numbers; only the distance between two vectors means something. Only compare vectors made by the same model.

### SLIDE 4. Where the pieces sit (ETL view)
ON SCREEN:
EXTRACT: jokes.json -> pandas DataFrame
TRANSFORM: embedding model turns each text into N numbers   <- nvidia_nemotron.py is ONLY this step
LOAD: LanceDB table with two columns: text, vector
SAY: Think of the lecture as an ETL job. LanceDB stores and searches. The embedding model is the transform.

---

## PART 2. LANCEDB BASICS (notebook: lancedb_basics.ipynb)

### SLIDE 5. A database that is a folder
CODE:
import lancedb

db = lancedb.connect(uri = "vector_database")
db
OUTPUT:
LanceDBConnection(uri='c:\Users\adelo\de25\ai_ops_lecture\09_lancedb\vector_database')
ON SCREEN (folder tree):
vector_database/
  animals_text.lance/
    _versions/        one manifest per change (version 1, 2, ...)
    _transactions/    the log of what changed
    data/             the rows
SAY: LanceDB is embedded, like DuckDB or SQLite: no server, no port, no password. connect() creates the folder if it does not exist. Every table is a folder ending in .lance. Data files plus a log, the same idea as Delta Lake or Iceberg.

### SLIDE 6. Load the animals data
CODE:
import json
with open("animals_text_embeddings.json") as file:
    data = json.loads(file.read())

data
OUTPUT (first rows):
[{'text': 'A small brown dog running.', 'vector': [0.12, 0.85, 0.33]},
 {'text': 'A cat resting quietly on a sofa.', 'vector': [0.4, 0.91, 0.1]},
 {'text': 'A large gray elephant drinking water.', 'vector': [0.88, 0.22, 0.55]},
 {'text': 'A fast cheetah sprinting across the savannah.', 'vector': [0.95, 0.12, 0.72]},
 {'text': 'A colorful parrot perched on a branch.', 'vector': [0.25, 0.66, 0.81]},
 {'text': 'A frog sitting on a lily pad.', 'vector': [0.14, 0.44, 0.27]}]
SAY: A list of dictionaries. Each dictionary is one row. The three numbers are a hand-made fake embedding, so we can learn vector search without calling any AI model.

### SLIDE 7. Create a table from the data
CODE:
table_animals = db.create_table("animals_text", exist_ok=True, data=data)
table_animals
CODE (look at it):
table_animals.head()
OUTPUT:
pyarrow.Table
text: string
vector: fixed_size_list<item: float>[3]
SAY: LanceDB guessed the schema from the data: text is a string, vector is a fixed-size list of 3 floats. exist_ok=True means "if it exists, open it": it is like CREATE TABLE IF NOT EXISTS, so the cell is idempotent (safe to run twice). head() returns the first 5 rows as a pyarrow table. to_pandas() gives all rows.

### SLIDE 8. Add rows (and a trap)
CODE:
more_data = [
    {"text": "A panda eating bamboo peacefully.", "vector": [0.51, 0.37, 0.82]},
    {"text": "A lion roaring loudly on a rock.", "vector": [0.93, 0.18, 0.41]},
]

table_animals.add(more_data)
OUTPUT (from a real run where this cell was run several times):
AddResult(version=5)
table_animals.to_pandas() showed 9 rows instead of 8: the panda row (0.51, 0.37, 0.82) appears twice, and the next search returned it three times, so it had been added more than once.
SAY: add() appends rows and creates a new table version each time. add() is NOT idempotent: run the cell again and you get duplicate rows. That is what happened here (version=5, and the panda is repeated). For a clean demo, drop the table or use mode="overwrite" before re-running.

### SLIDE 9. Vector search with a raw vector
CODE:
query_vector = [0.5, 0.2, 0.9]

table_animals.search(query_vector).limit(3).to_pandas()
ON SCREEN (how the distance is calculated for the panda, vector [0.51, 0.37, 0.82]):
(0.51 - 0.5)^2 + (0.37 - 0.2)^2 + (0.82 - 0.9)^2 = 0.0001 + 0.0289 + 0.0064 = 0.0354
OUTPUT from a clean table (no duplicates):
text                                             _distance
A panda eating bamboo peacefully.                0.0354
A fast cheetah sprinting across the savannah.    0.2413
A large gray elephant drinking water.            0.2673
OUTPUT from the real run (duplicate panda rows):
panda 0.0354, panda 0.0354, panda 0.0354
SAY: search() compares the query vector with the vector of every row and returns the nearest rows. _distance is the squared Euclidean distance: smaller means closer. limit(3) keeps the top 3. In the real run the duplicates made the same panda come back three times, which shows why duplicates matter. Note: vector search always returns k rows. It never says "no match".

### SLIDE 10. An empty table from a schema, list, drop
CODE:
from lancedb.pydantic import LanceModel

class JokeSchema(LanceModel):
    joke: str 
    rating: int

db.create_table(name = "jokes",schema=JokeSchema, mode="overwrite")
db.table_names()
db.drop_table("jokes")
db.table_names()
OUTPUT:
['animals_text', 'jokes']
['animals_text']
SAY: LanceModel is a Pydantic model that LanceDB turns into a table schema. This makes an empty table with two columns. mode="overwrite" replaces a table of the same name (CREATE OR REPLACE). We used it because an older table called "jokes" with different columns already existed; with exist_ok=True LanceDB raised "Provided schema does not match existing table schema". table_names() prints a deprecation warning: list_tables() is the newer name.

### SLIDE 11. Open an existing table
CODE:
db.open_table("animals_text").head()
SAY: This is how you come back to your data in a new session: connect(), then open_table().

---

## PART 3. LET LANCEDB CREATE THE EMBEDDINGS

### SLIDE 12. The embedding registry, SourceField and VectorField
CODE:
from dotenv import load_dotenv
load_dotenv()

from lancedb.pydantic import LanceModel, Vector
from lancedb.embeddings import get_registry

model = get_registry().get("cohere").create(name = "embed-multilingual-light-v3.0")

class JokeModel(LanceModel):
    joke: str = model.SourceField()
    vector: Vector(model.ndims()) = model.VectorField()

table_jokes = db.create_table("jokes", schema = JokeModel, exist_ok=True)
table_jokes
ON SCREEN (diagram):
joke (SourceField, text IN) -> embedding model -> vector (VectorField, numbers OUT)
SAY: get_registry() is LanceDB's catalogue of embedding providers. get("cohere").create(...) picks one. SourceField marks the column LanceDB sends to the model. VectorField marks the column where the numbers are stored. model.ndims() gives the vector length so the column type matches. In data terms: a computed column. You declare it once in the schema and every insert is enriched automatically. Cohere needs COHERE_API_KEY in the environment; load_dotenv() reads it from the .env file.

### SLIDE 13. Load the jokes and add them
CODE:
import pandas as pd 
with open("jokes.json", "r", encoding="utf-8") as file:
    jokes_data = json.loads(file.read())

df_jokes = pd.DataFrame(jokes_data).rename({"jokes": "joke"}, axis=1)
df_jokes.head()

table_jokes.add(df_jokes)
OUTPUT:
AddResult(version=2)
SAY: jokes.json is {"jokes": [30 strings]}, so pandas makes one column called "jokes". The schema field is "joke", so we rename the column. The names must match. encoding="utf-8" is needed on Windows because the file has curly quotes. We only provide the text column: LanceDB calls the embedding model for each joke and fills the vector column.

### SLIDE 14. What is in the table now
CODE:
table_jokes.head(2)
OUTPUT (schema part):
joke: string not null
vector: fixed_size_list<item: float>[384]
SAY: The vector column exists and holds 384 numbers per joke (the length depends on the model; check model.ndims() in your own run). The first values of the first joke are about -0.0192, 0.0164, 0.0031, 0.0219. Nobody reads those numbers. Their only use is distance.

### SLIDE 15. Search with plain text
CODE:
table_jokes.search("give me chemistry related jokes").limit(8).to_pandas()
OUTPUT (top rows, with _distance):
0  I told a chemistry joke... there was no reaction.   0.951342
1  Oxygen and Magnesium got together... OMg!          1.161264
2  Chemists have all the solutions... mostly in beakers
3  Why did the chemist ground his kids? ...
4  Never trust an atom... they make up everything.
SAY: LanceDB embeds the question with the SAME model, then returns the nearest jokes. The chemistry jokes win, even though the word "chemistry" is not in all of them. Same model to store and to search, always.

### SLIDE 16. More searches
CODE:
table_jokes.search("data engineering jokes").limit(8).to_pandas()
table_jokes.search("give me jokes on C#").limit(8).to_pandas()
OUTPUT:
"data engineering jokes": top rows are about data engineers, a data lake, a data pipeline (distance about 1.18 and 1.22 for the first two).
"give me jokes on C#": the C# compiler joke is first (distance about 0.995), then more C# jokes (1.034), then other programming and school jokes.
SAY: Meaning matches, not spelling. The first result is not always perfect: for "data engineering jokes" a nature joke about data engineers came first.

### SLIDE 17. A vague question
CODE:
table_jokes.search("give me nature related jokes").limit(8).to_pandas()
OUTPUT:
0  I told a chemistry joke... there was no reaction.   1.455355
1  Why do data engineers hate nature? Too many un...   1.527386
SAY: No joke is really about nature. Vector search still returns 8 rows, and the distances (1.45, 1.53) are much larger than for the chemistry search (0.95). A large distance is a warning sign. This is why we look at the distance, and why hybrid search exists.

---

## PART 4. THREE KINDS OF SEARCH

### SLIDE 18. Full-text search index
CODE:
table_jokes.create_fts_index("joke", replace=True)
OUTPUT (warning):
create_fts_index is deprecated as of 0.25.0. Use create_index() with config=FTS() instead.
SAY: FTS is classic keyword search: LanceDB builds an index of the words in the joke column, like the index at the back of a book. replace=True rebuilds it. It still works, but newer LanceDB prefers create_index with an FTS config.

### SLIDE 19. Hybrid search with RRF
CODE:
from lancedb import rerankers

reranker = rerankers.RRFReranker()

results = table_jokes.search(
    "give me nature related jokes",
    query_type="hybrid",
    vector_column_name="vector",
    fts_columns="joke",
).rerank(reranker).limit(8).to_pandas()
results
OUTPUT:
0  I told a chemistry joke... there was no reaction.   _relevance_score 0.032787
ON SCREEN (diagram and calculation):
question -> vector search (list 1) + keyword search (list 2) -> RRF -> one list
RRF score of a row = 1/(60 + rank in list 1) + 1/(60 + rank in list 2)
rank 1 in both lists: 1/61 + 1/61 = 0.032787   <- exactly the score on the first row
SAY: Hybrid runs both searches and merges the two ranked lists. RRF (reciprocal rank fusion) only uses positions, not the different score scales. The first row scored 0.032787, which equals 2/61: the score of a row ranked first in both lists. A row that is good in both lists beats a row that is great in only one.

### SLIDE 20. Rule of thumb
ON SCREEN (table):
Exact words, names, codes   -> full-text search (FTS)
Meaning, any wording        -> vector search
Unpredictable or mixed      -> hybrid search
Vector search: always returns k rows. Check _distance.

---

## PART 5. OTHER EMBEDDING MODELS (notebook: lancedb_embeddings.ipynb)

### SLIDE 21. A free local model
CODE:
import lancedb
import pandas as pd 

df = pd.read_json("jokes.json")

db = lancedb.connect("knowledge_base")

from lancedb.embeddings import get_registry
from lancedb.pydantic import LanceModel, Vector

model = (
    get_registry()
    .get("sentence-transformers")
    .create(name="intfloat/multilingual-e5-small", device="cpu")
)

class JokeModel(LanceModel):
    jokes: str = model.SourceField()
    vector: Vector(model.ndims()) = (
        model.VectorField()
    )

table = db.create_table("jokes_sentence_transformer", schema=JokeModel)
table.add(df)
OUTPUT:
AddResult(version=2)
SAY: A second database folder, knowledge_base. This model runs on your own CPU: no API key and no cost. It downloads from Hugging Face the first time (the warning about HF_TOKEN is only a speed notice). It outputs 384 numbers per text. Here the text column is called "jokes" (plural), because that is the DataFrame column, so no rename is needed.

### SLIDE 22. Searching in another language
CODE:
table.search("why do mathematicians have problems?").to_pandas()
table.search("kemi ...").to_pandas()   # the query is the word "kemi" plus one more Danish or Swedish-style word
OUTPUT:
"why do mathematicians have problems?": first row is "Why's 6 afraid of 7? Because 7 8 9."
"kemi ..." query (kemi means chemistry in Danish and Swedish): chemistry jokes are first: "Chemists have all the solutions...", "Why did the chemist ground his kids?", "Oxygen and Magnesium got together... OMg!"
SAY: The model is multilingual, so a non-English query finds the English chemistry jokes. The query is in one language and the data in another, and the meaning still matches.

### SLIDE 23. Local model vs hosted model
ON SCREEN (table):
                     | Local model (sentence-transformers) | Hosted API (Cohere, NVIDIA)
Cost                 | free                                | pay per use or quota
API key              | no                                  | yes
Privacy              | text stays on your computer         | text is sent over the internet
Offline              | yes, after the first download       | no
Vector length        | 384                                 | 384 (Cohere light), 4096 (NVIDIA)

---

## PART 6. THE CUSTOM EMBEDDER (file: custom_embeddings/nvidia_nemotron.py)

### SLIDE 24. Why we write our own
ON SCREEN:
LanceDB has built-in embedders for some providers, but not for this NVIDIA model.
NVIDIA's API speaks the OpenAI format.
So: we write a small ADAPTER class and register it in LanceDB's registry.
LanceDB  <--- NvidiaNemotronEmbedding (adapter) --->  NVIDIA API
SAY: Important: this file is NOT the embedding model. The model runs on NVIDIA's servers. The file only calls it. In ETL terms it is only the Transform step. The same pattern as a custom Airflow operator or a dbt adapter: the framework defines an interface, you implement it for a new system and register it.

### SLIDE 25. nvidia_nemotron.py part 1: imports, key, client
CODE:
import os
from dotenv import load_dotenv
from openai import OpenAI
from lancedb.embeddings import TextEmbeddingFunction, get_registry
import numpy as np

load_dotenv()

client = OpenAI(
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=os.getenv("NVIDIA_API"),
    max_retries=3,
    timeout=60.0,
)
SAY: load_dotenv() puts NVIDIA_API from the .env file into the environment. OpenAI is only a client library: base_url sends the OpenAI-style requests to NVIDIA's server. max_retries=3 retries temporary failures, timeout=60 gives up after 60 seconds. This code runs once, when the file is imported. If the key is missing, the OpenAI client fails right here, with "Missing credentials".

### SLIDE 26. nvidia_nemotron.py part 2: register the class
CODE:
@get_registry().register("nvidia-nemotron")
class NvidiaNemotronEmbedding(TextEmbeddingFunction):
    model: str = "nvidia/nemotron-3.5-embed-8b"
    dimensions: int = 4096

    def ndims(self) -> int:
        return self.dimensions
SAY: The line starting with @ is a decorator: it writes this class into LanceDB's registry under the name "nvidia-nemotron". That is why the notebook can later call get_registry().get("nvidia-nemotron"), and why importing the file is enough (the import runs the decorator). The class inherits from TextEmbeddingFunction, LanceDB's base class for text embedders, so we only fill in the NVIDIA-specific parts. model is which NVIDIA model to call. dimensions is the length of each vector, 4096. We declare it ourselves, and ndims() tells LanceDB, so the table column becomes a vector of 4096 numbers.

### SLIDE 27. nvidia_nemotron.py part 3: the one method that calls the network
CODE:
    def _embed_one(self, text: str, input_type: str) -> np.ndarray:
        response = client.embeddings.create(
            model=self.model,
            input=[text],
            extra_body={"input_type": input_type},
        )
        vector = np.asarray(response.data[0].embedding, dtype=np.float32)
        return vector
ON SCREEN (line by line):
input=[text]                     the API takes a list; we send one text
extra_body={"input_type": ...}   NVIDIA-specific option: "passage" or "query"
response.data[0].embedding       list of 4096 floats for that text
np.asarray(..., dtype=float32)   LanceDB stores float32 numbers
SAY: This is the only method that talks to the network. One text in, one array of 4096 numbers out.

### SLIDE 28. nvidia_nemotron.py part 4: the two entry points
CODE:
    def generate_embeddings(self, texts, *args, **kwargs):
        texts = self.sanitize_input(texts)
        return [self._embed_one(text, input_type="passage") for text in texts]

    def compute_source_embeddings(self, texts, *args, **kwargs):
        return self.generate_embeddings(texts)

    def compute_query_embeddings(self, query, *args, **kwargs):
        texts = self.sanitize_input(query)
        return [self._embed_one(text, input_type="query") for text in texts]
ON SCREEN (diagram):
table.add(df)            -> compute_source_embeddings -> generate_embeddings -> _embed_one(..., "passage")  (1 API call per joke)
table.search("kemi")     -> compute_query_embeddings  ->                        _embed_one(..., "query")    (1 API call)
SAY: LanceDB calls compute_source_embeddings when we write rows and compute_query_embeddings when we search. Why two labels? A question and its answer do not look alike, so the NVIDIA model wants to know which side it is embedding. When we embedded the word "hello" both ways, the two vectors were not identical (cosine similarity about 0.75). Store as "passage", search as "query". It is one API call per text: 30 jokes means 30 calls.

### SLIDE 29. Using the custom embedder in the notebook
CODE:
from lancedb.pydantic import LanceModel, Vector
from custom_embeddings.nvidia_nemotron import NvidiaNemotronEmbedding
from lancedb.embeddings import get_registry 

embedding_model = get_registry().get("nvidia-nemotron").create()

class NvidiaJokeModel(LanceModel):
    jokes: str = embedding_model.SourceField()
    vector: Vector(embedding_model.ndims()) = embedding_model.VectorField()

table_jokes = db.create_table("jokes_nvidia", schema=NvidiaJokeModel, mode="overwrite")
table_jokes.add(df)
OUTPUT:
AddResult(version=2)
SAY: We import the class only to run its decorator. We build a NEW schema tied to the NVIDIA embedder: the schema decides which model runs. An earlier version of this notebook reused the schema of the local model, so NVIDIA was never called. mode="overwrite" replaces the table.

### SLIDE 30. Searching the NVIDIA table
CODE:
table_jokes.search("kemi").to_pandas()
table_jokes.search("why do mathematicians have problems?").to_pandas()
OUTPUT:
"kemi": Why did the chemist ground his kids?, I told a chemistry joke..., Chemists have all the solutions..., Never trust an atom..., Oxygen and Magnesium got together...
"why do mathematicians have problems?": first row is "Chemists have all the solutions...", the "Why's 6 afraid of 7" joke comes only 10th.
SAY: Same notebook, different model, different ranking. The NVIDIA model found the chemistry jokes for "kemi" but ranked the maths question differently than the local model. Two models are two different "number languages": results differ, and you can never mix them in one table.

---

## PART 7. COST, TRAPS, RECAP

### SLIDE 31. Storage maths and the traps
ON SCREEN (storage table, a float32 number is 4 bytes):
Model                          | numbers per row | bytes per row | 1,000,000 rows
hand-made animals              | 3               | 12            | 12 MB
Cohere light / local e5-small  | 384             | 1,536         | about 1.5 GB
Gemini (seen in a real run)    | 768             | 3,072         | about 3 GB
NVIDIA Nemotron                | 4096            | 16,384        | about 16 GB
ON SCREEN (traps, each seen in the real run):
1. Re-running add() duplicates rows (animals table: version=5, panda three times).
2. exist_ok=True with a different schema fails: "Provided schema does not match existing table schema". Use mode="overwrite".
3. The schema decides which embedding model runs.
4. Column names must match: "joke" vs "jokes".
5. Windows: open() needs encoding="utf-8".
6. API keys: COHERE_API_KEY, NVIDIA_API. LanceDB's Gemini embedder reads GOOGLE_API_KEY.
7. Pass a LIST to generate_embeddings: model.generate_embeddings("hello") returned shape (5, 768), one vector per LETTER; ["hello"] gives (1, 768).
8. Vector search never says "no match": look at _distance.
9. create_fts_index and table_names are deprecated (they still work).
SAY: Bigger vectors capture more detail but cost more to store and to compare. That is a real data engineering trade-off.

### SLIDE 32. Recap and exercises
ON SCREEN (5 sentences):
1. An embedding turns a text into a list of numbers; similar meaning gives similar numbers.
2. LanceDB stores text and vectors together in a folder, with no server.
3. Search turns the question into numbers and returns the rows with the smallest distance.
4. Full-text search for exact words, vector search for meaning, hybrid for both (merged by RRF).
5. A custom embedder is only an adapter: a class registered under a name that calls a model and returns numbers.
EXERCISES:
1. Run embedder = get_registry().get("nvidia-nemotron").create() then print(embedder.ndims()) and embedder.compute_query_embeddings("hello")[0].shape. Expect 4096 and (4096,).
2. Calculate by hand the distance from the query [0.5, 0.2, 0.9] to the frog [0.14, 0.44, 0.27]. Expect 0.5841.
3. In three sentences, explain what nvidia_nemotron.py does and what it does not do.
