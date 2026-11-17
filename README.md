# AIOps

In this course, dive into working with LLMs and LLMOps including

- Vector database
- RAG
- Evaluation
- LLM judge
- Hallucination detection
- Tracing
- Moniitoring
- Prompt management and optimization
- Deployment
- CI/CD
- MCP

Using the following tools:

- PydanticAI
- LanceDB
- FastAPI
- Logfire
- Azure
- Docker
- Github Actions
- pymcp

| **Week** | **Content**                                                                    | **Lectures** | **Exercise** |
| -------- | ------------------------------------------------------------------------------ | ------------ | ------------ |
| 1        | llm intro, llmops intro, nvidia build, pydanticai, pydantic, structured output | 00-03, a0    | 0            |
| 2        | pydanticai + fastapi, chatbot, tool use                                        | 04-06        | 1            |
| 3        | multi-agent handoff, logfire: traces + prompt management, lancedb vector database | 07-09     | 2            |
| 4        | rag, project start                                                             | 11           |              |
| 5        | dockerization and azure deployment, project                                    | 12           |              |
| 6        | github actions and CI/CD, MCP, project                                         |              |              |
| 7        | project                                                                        |              |              |


# Study Map

One study guide per lecture folder, written to sit next to the code in VS Code.
Each guide explains the **why**, how the lecture **connects to other files**, and ends with a "My questions" section.

| Lecture | Study guide | Status |
| --- | --- | --- |
| 01 Setup Pydantic AI + Nvidia Build | [STUDY_GUIDE.md](01_setup_pydantic_nvidia_build/STUDY_GUIDE.md) | written |
| 02 LLM intro | [STUDY_GUIDE.md](02_llm_intro/STUDY_GUIDE.md) | written |
| 03 Structured output | [STUDY_GUIDE_strctured_output_exercise.md](03_pydanticai_structured_output/STUDY_GUIDE_strctured_output_exercise.md) (whole folder) | written |
| 03 Structured output, main notebook only | [STUDY_GUIDE_lecture_pydanticai_pydantic_models.md](03_pydanticai_structured_output/STUDY_GUIDE_lecture_pydanticai_pydantic_models.md) (cell by cell) | written |
| 03 Structured output, `pydanticai_pydantic_model.ipynb` only | [STUDY_GUIDE_pydanticai_pydantic_model.md](03_pydanticai_structured_output/STUDY_GUIDE_pydanticai_pydantic_model.md) (cell by cell, nested models, dlt + DuckDB) | written |
| 04 Pydantic + FastAPI | [STUDY_GUIDE.md](04_pydantic_fastapi/STUDY_GUIDE.md) | written |
| 05 Chatbot | [STUDY_GUIDE.md](05_pydanticai_fastapi_chatbot/STUDY_GUIDE.md) | written |
| 06 Tool use | [STUDY_GUIDE.md](06_tool_use/STUDY_GUIDE.md) | written |
| 07 Multi-agent handoff | [STUDY_GUIDE.md](07_multiagent_handoff/STUDY_GUIDE.md) | written |
| 08 Logfire | [STUDY_GUIDE.md](08_logfire/STUDY_GUIDE.md) | written |
| 09 LanceDB | [STUDY_GUIDE.md](09_lancedb/STUDY_GUIDE.md) | written |
| 11 RAG | [STUDY_GUIDE.md](11_rag/STUDY_GUIDE.md) | written |
| 12 Dockerize RAG | [STUDY_GUIDE.md](12_dockerize_rag/STUDY_GUIDE.md) | written |

> There's no `10_...` folder in this repo yet — numbering picks back up at 11.

## The thread through the whole course

Every lecture is the same four steps with one more idea added:

```
Provider → Model → Agent → agent.run(...)  →  result.output
```

| Lecture | What gets added to that line |
| --- | --- |
| 01 | The line itself, built in a notebook |
| 02 | `system_prompt`, `temperature`, tokens, `message_history` |
| 03 | `output_type`: a Pydantic model, so the answer is validated data |
| 04 | FastAPI endpoint and DuckDB around it |
| 05 | Streamlit page → FastAPI → Agent, with chat history |
| 06 | Tools the model can call, `deps` |
| 07 | A second kind of tool: `ask_study_agent`/`ask_career_agent` call *other agents*, not just functions — the coach combines their answers |
| 08 | `logfire.instrument_pydantic_ai()` wraps the whole line with tracing; prompts move out of the code into Logfire (`get_prompt()`) |
| 09 | No `agent.run()` yet — this lecture builds the vector-search building block (LanceDB, embeddings) that lecture 11 plugs into an agent |
| 11 | A `retrieve_top_documents` tool backed by LanceDB, plus `output_type=RagResponse` — the agent looks something up before it answers |
| 12 | Same line, unchanged — now running inside two Docker containers instead of two local processes |


