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
| 3        | logfire: traces, llm judge, lancedb vector database, rag                       |              | 2            |
| 4        | rag, project start                                                             |              |              |
| 5        | dockerization and azure deployment, project                                    |              |              |
| 6        | github actions and CI/CD, MCP, project                                         |              |              |
| 7        | project                                                                        |              |              |


# Study Map
# Study map

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


