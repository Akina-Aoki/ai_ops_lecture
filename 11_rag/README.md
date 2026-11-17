# Lecture 11: Retrieval-Augmented Generation (RAG) with PydanticAI, LanceDB, FastAPI and Streamlit

- [Lecture Video](https://youtu.be/KdeoPglfpb8)

Until now the agents answered only from what the model learned in training. **RAG** fixes that: we build a small knowledge base (Wikipedia articles about dwarf rabbit breeds, as PDFs), turn each article into a vector with **LanceDB** (lecture 09), and let an agent **retrieve** the closest article before it answers. The whole thing is wrapped in a real client/server app: a **FastAPI** backend serves the agent over HTTP, and a **Streamlit** frontend is the page the user actually sees.

## The pipeline

There is no architecture picture for this lecture yet, so here is the same idea as a text diagram. Steps 1-3 happen **once** (or whenever the PDFs change); steps 4-6 happen **on every question**.

```
Setup (run once)
1  data/*.pdf ──[pdfs_to_text.py]──► data/*.txt
2  data/*.txt ──[ingestion.py]──► knowledge_base/ (LanceDB table "articles", Gemini embeddings)

Query (run every time you ask a question)
3  frontend/app.py (Streamlit) ──HTTP POST /rag/query──► api.py (FastAPI)
4  api.py ──► backend/rag.py: rag_agent.run(prompt)
5  rag_agent ──tool call: retrieve_top_documents──► knowledge_base/ (vector search)
6  rag_agent ──► RagResponse {filename, filepath, answer} ──► api.py ──► Streamlit shows the answer + a rabbit picture
```

## 1. What the picture says

| In the pipeline | In the code | Job |
| --- | --- | --- |
| **data/*.pdf** | [data/](data) | The source documents: one Wikipedia article per dwarf rabbit breed |
| **pdfs_to_text.py** | [pdfs_to_text.py](pdfs_to_text.py) | `extract_text_from_pdf()` + `export_text_to_txt()`: turns every PDF into a `.txt` file next to it |
| **ingestion.py** | [ingestion.py](ingestion.py) | `setup_vector_db()` creates the LanceDB table; `ingest_docs_to_vector_db()` reads every `.txt` file and adds it as a row (LanceDB embeds `content` for you) |
| **backend/constants.py** | [backend/constants.py](backend/constants.py) | `DATA_PATH` and `VECTOR_DATABASE_PATH`, the one place both paths are defined |
| **backend/data_models.py** | [backend/data_models.py](backend/data_models.py) | `Article` (table schema + embedding model), `Prompt` (what the user sends), `RagResponse` (what the agent must answer with) |
| **backend/rag.py** | [backend/rag.py](backend/rag.py) | `rag_agent`: the PydanticAI agent, its system prompt, and its one tool `retrieve_top_documents` |
| **api.py** | [api.py](api.py) | FastAPI app. `POST /rag/query` is the only door into `rag_agent` |
| **frontend/app.py** | [frontend/app.py](frontend/app.py) | The Streamlit page: a text box, a "Send" button, and the answer with a matching rabbit picture from `assets/` |
| **Gemini** | outside your code | Embeds the articles and the query (`gemini-embedding-001`), and answers as `gemini-2.5-flash` |

> **Why do this?** An LLM answering from training alone can't know about documents it never saw, and it can hallucinate instead of admitting that. RAG gives the model a **lookup step** first, so the answer is grounded in text you actually control, and the source file is returned alongside the answer.

## 2. How 11 differs from 09 (LanceDB)

| | **09 LanceDB** | **11 RAG** |
| --- | --- | --- |
| New idea | Store and search vectors | **Use** the search results to ground an agent's answer |
| Embedding model | Cohere, a local model, a custom NVIDIA class | Google **Gemini** (`gemini-embedding-001`, 3072 dims) |
| Who searches | You, directly in a notebook cell | The agent itself, through the `retrieve_top_documents` **tool** |
| Output shape | A pandas DataFrame of rows | A structured `RagResponse` (filename, filepath, answer) |
| Around the code | Two notebooks | A real app: FastAPI backend + Streamlit frontend, talking over HTTP |
| Extra key in `.env` | `COHERE_API_KEY` | `Gemini_API_Key` |

## 3. Key ideas in this lecture

| Word | Meaning | In this lecture |
| --- | --- | --- |
| **Retrieval** | Finding the stored document(s) closest in meaning to the question | `retrieve_top_documents()` in [backend/rag.py](backend/rag.py) |
| **Augmented generation** | Giving the model retrieved text before it answers, instead of answering from memory alone | The tool's return value is appended to the model's context automatically by PydanticAI |
| **Tool** | A function the agent can choose to call while answering (lecture 06) | `@rag_agent.tool_plain` on `retrieve_top_documents` |
| **Structured output** | Forcing the model's reply into a fixed shape (lecture 03) | `output_type=RagResponse` |
| **doc_id** | A stable key per document, used to avoid duplicate rows on re-ingestion | `table.delete(f"doc_id = '{doc_id}'")` in [ingestion.py](ingestion.py) |
| **Grounding** | Answering from retrieved text, and saying "I don't know" when the question is outside it | The system prompt in [backend/rag.py](backend/rag.py): "Don't hallucinate..." |

## 4. How the files depend on each other

```
backend/constants.py ──┐
                        ├──► pdfs_to_text.py        (writes data/*.txt)
                        └──► ingestion.py            (writes knowledge_base/)
                                   ▲
backend/data_models.py ───────────┤  (Article schema, Gemini embedding model)
                                   │
backend/rag.py ◄───────────────────  (reads knowledge_base/, builds rag_agent)
      │
      ▼
   api.py  ◄──HTTP── frontend/app.py   (two separate processes you run yourself)
```

| Dependency | What it means |
| --- | --- |
| `pdfs_to_text.py` **needs** PDFs already in `data/` | Run it first, or `ingestion.py` finds no `.txt` files to add |
| `ingestion.py` **needs** `.txt` files in `data/` and a Gemini key | Builds `knowledge_base/` (a LanceDB folder), used by `rag.py` |
| `backend/rag.py` **needs** `knowledge_base/` to already exist | It connects to it the moment it is imported, it does not create it |
| `api.py` **needs** `backend/rag.py` | The only thing it does is expose `rag_agent` over HTTP |
| `frontend/app.py` **needs** `api.py` running at `127.0.0.1:8000` | It only talks to the agent through that HTTP request, never imports `backend/` directly |

## 5. How a run works

**Setup, once:**

| Step | File | What happens |
| --- | --- | --- |
| 1 | [pdfs_to_text.py](pdfs_to_text.py) | Reads every PDF in `data/`, extracts the text with `pypdf`, saves it as `data/<name>.txt` |
| 2 | [ingestion.py](ingestion.py) | Connects to (creates) `knowledge_base/`, creates the `articles` table from `Article`'s schema, then adds each `.txt` file as a row. LanceDB calls the Gemini embedding model for you, because `content` is a `SourceField()` and `embedding` is a `VectorField()` |

**Per question, every time:**

| Step | File | What happens |
| --- | --- | --- |
| 3 | [frontend/app.py](frontend/app.py) | User types a question and clicks "Send". `requests.post(...)` sends `{"prompt": text}` to the API |
| 4 | [api.py](api.py) | `query_documentation()` validates the body against `Prompt`, then calls `rag_agent.run(query.prompt)` |
| 5 | [backend/rag.py](backend/rag.py) | The model decides to call `retrieve_top_documents(query)`. It embeds `query` and vector-searches `knowledge_base/articles`, returning the top match's filename, filepath and content |
| 6 | [backend/rag.py](backend/rag.py) | The model writes its final answer, forced into the `RagResponse` shape |
| 7 | [api.py](api.py) → [frontend/app.py](frontend/app.py) | FastAPI returns the JSON; Streamlit shows the answer, the source filepath, and `assets/<filename>.png` |

## 6. What is in this folder

| File | What it is | Read it when you want to know... |
| --- | --- | --- |
| [pdfs_to_text.py](pdfs_to_text.py) | PDF → text step | How the raw PDFs become plain text |
| [ingestion.py](ingestion.py) | Builds the vector database | How documents are embedded and stored, and how re-running avoids duplicates |
| [backend/constants.py](backend/constants.py) | `DATA_PATH`, `VECTOR_DATABASE_PATH` | Where the data and database folders are, in one place |
| [backend/data_models.py](backend/data_models.py) | `Article`, `Prompt`, `RagResponse` | The shared shapes: what's stored, what comes in, what goes out |
| [backend/rag.py](backend/rag.py) | `rag_agent` and its tool | How retrieval and generation are wired together |
| [api.py](api.py) | FastAPI app, `POST /rag/query` | How the agent is exposed over HTTP |
| [frontend/app.py](frontend/app.py) | Streamlit page | The user-facing side: the text box, the request, the rendered answer |
| [explorations.ipynb](explorations.ipynb) | Notebook version of `pdfs_to_text.py` and the ingestion ideas, cell by cell, with explanations | A beginner-friendly walk-through before trusting the scripts |
| [data/](data) | The 4 source PDFs (and, after step 1, their `.txt` versions) | What goes into the knowledge base |
| [assets/](assets) | One picture per rabbit breed, named to match `filename` in `RagResponse` | What the frontend shows next to the answer |
| `knowledge_base/` | The LanceDB database (created by `ingestion.py` when you run it) | — |

## Setup

```bash
uv add pypdf
```

> `pypdf` is imported in [pdfs_to_text.py](pdfs_to_text.py) but isn't yet in `pyproject.toml` — add it before running the pipeline. `fastapi`, `uvicorn`, `streamlit`, `lancedb`, `pydantic-ai`, `google-generativeai` and `python-dotenv` are already there.

Add your Gemini key to the repo's `.env` (already listed in `.env.example`):

```env
Gemini_API_Key=YOUR_GEMINI_KEY
```

Get a key from [Google AI Studio](https://aistudio.google.com/apikey). LanceDB's embedding function actually reads `GOOGLE_API_KEY`, not `Gemini_API_Key` — [backend/data_models.py](backend/data_models.py) copies the value across automatically after `load_dotenv()`, so you only need to set `Gemini_API_Key` above.

## 7. Run it

All commands run from this folder (`11_rag/`), since the backend imports are written as `backend.xxx` and `assets`/`data` are found relative to it.

```bash
cd 11_rag
```

**1. Build the knowledge base (once):**

```bash
uv run python pdfs_to_text.py
```

```bash
uv run python -m ingestion
```

The ingestion script prints the row count and filenames after each document, and pauses 30 seconds between documents to stay under the Gemini embedding rate limit — expect it to take a couple of minutes for 4 PDFs.

**2. Start the backend, in one terminal:**

```bash
uv run uvicorn api:app --reload
```

**3. Start the frontend, in another terminal:**

```bash
uv run streamlit run frontend/app.py
```

Open the Streamlit page, ask something like "What is special about the Holland Lop?", and you should get an answer, the source file, and a matching picture.

## 8. Known quirks

| Quirk | Where | Effect |
| --- | --- | --- |
Fixed (kept here so you know what to watch for in your own code):

| Was | Fix |
| --- | --- |
| `Article` defined `file_path`, but `ingestion.py` added rows with the key `filepath` | Renamed the schema field to `filepath` in [backend/data_models.py](backend/data_models.py) |
| `embedding_model` didn't pass `dim=`, so `GeminiText.ndims()` defaulted to 768 while the schema hardcoded `Vector(3072)` | `.create(name="gemini-embedding-001", dim=EMBEDDING_DIM)` in [backend/data_models.py](backend/data_models.py) |
| LanceDB's `gemini-text` embedder reads `GOOGLE_API_KEY` specifically (hardcoded in the library), not the `Gemini_API_Key` name used in this repo's `.env` | A bridge right after `load_dotenv()` in [backend/data_models.py](backend/data_models.py) copies `Gemini_API_Key` into `GOOGLE_API_KEY` if the latter isn't already set |
| `rag_agent`'s model string was `"google-gla:gemini-2.5-flash"`, a prefix the installed `pydantic-ai` no longer recognizes | Changed to `"google:gemini-2.5-flash"` in [backend/rag.py](backend/rag.py) |
| `pypdf` is used but was missing from `pyproject.toml` | `uv add pypdf` (see [Setup](#setup)) |

Still true:

| Quirk | Where | Effect |
| --- | --- | --- |
| `retrieve_top_documents` asks for `k=3` results but only ever reads `results[0]` | [backend/rag.py](backend/rag.py) | The other 2 matches are fetched and thrown away; fine for 4 documents, wasteful at scale |
| `open(..., "w")` / `open(..., "r")` have no `encoding="utf-8"` | [pdfs_to_text.py](pdfs_to_text.py), [ingestion.py](ingestion.py) | Can raise `UnicodeDecodeError`/`UnicodeEncodeError` if you read the `.txt` files with another tool that assumes UTF-8; the scripts themselves round-trip fine since both sides use the same default encoding |
| `time.sleep(30)` between every document in `ingest_docs_to_vector_db` | [ingestion.py](ingestion.py) | Re-ingesting many documents is slow by design (rate-limit safety), not a bug |
| `knowledge_base/` must already exist when `backend/rag.py` is imported | [backend/rag.py](backend/rag.py) | Starting `api.py` before running `ingestion.py` once will fail to find the `articles` table |
| `setup_vector_db(..., exist_ok=True)` can reject a schema that looks identical | [ingestion.py](ingestion.py) | If `create_table` raises "Provided schema does not match existing table schema" after you change `Article`, drop the table (`lancedb.connect(path).drop_table("articles")`) and re-ingest rather than debugging the diff |
| No `.gitignore` entry for `knowledge_base/` or `data/*.txt` yet | — | Generated files may end up tracked by git if you `git add` broadly (the repo root `.gitignore` now covers this for `11_rag/`) |

## Read more
- [pydanticai rags](https://ai.pydantic.dev/examples/rag/)
- [lancedb embeddings](https://lancedb.com/docs/embedding/) (same idea as lecture 09, here with the Gemini provider)
- [FastAPI docs](https://fastapi.tiangolo.com/)
- [Streamlit docs](https://docs.streamlit.io/)

Earlier lectures
- [Lecture 09: LanceDB](../09_lancedb/README.md): vector search and embeddings, the building block used here
- [Lecture 06: Tool use](../06_tool_use/README.md): how an agent calls a Python function, the same pattern `retrieve_top_documents` uses
- [Lecture 04: Pydantic + FastAPI](../04_pydantic_fastapi/README.md) and [Lecture 05: Chatbot](../05_pydanticai_fastapi_chatbot/README.md): the FastAPI + Streamlit shape reused here
