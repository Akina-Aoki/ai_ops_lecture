# Exercise 1 - PydanticAI, FastAPI 

In this exercise, you get to work with fastapi to serve PydanticAI models to different endpoints and then consume these endpoints. 

## 0. PydanticAI fundamentals

Make a PydanticAI model that can take an input of a location and then it should suggest 5 restaurants nearby that place. The restaurant model should have

- name
- type of food (cuisine)
- price level
- rating
- short description
- opening hours
- location

It's okay if your model is making up a restaurant that doesn't exist

## 1. FastAPI to serve PydanticAI
- **In app folder**

Now make a fastapi with a post endpoint in natural language to prompt for a location and what type of food. Based on these it should generate a restaurant and store it in a duckdb database.

Also implement a get endpoint for showing all restaurants in the database. Implement a simple frontend in for example streamlit to consume this API.

How to run 
```
cd exercises/exercise_1/app
python setup_db.py
uvicorn restaurant_api:app --reload
```

## 2. A pedagogical programming bot

Create a chatbot that is specialized in helping out with programming tasks. It should answer shortly, so not spoonfeeding with long answers, and it should be socratic, that is always ask follow up questions rather than giving the answer.

- **In Chatbot folder**


## Theory questions
### a) What problem does PydanticAI solve when using LLMs?
By default, an LLM just returns free text, not something a program can loop over safely. PydanticAI solves this by forcing models to answer into Pydantic model defined. It handles prompting, parsing and validation and automatically asks the model to retry if the reply doesnt fit. You get back a typed Python object instead of writing fragile string-parsing code.

### b) Why is schema validation critical in LLM-based systems?
LLMs aren't deterministic, meaning the same prompt can produce different texts every run, and a model can invent a field (hallucination), use the wrong type, or skip one entirely. Without a schema sitting between an LLM and the rest of the system, bad data flows straight into the database or API responses and fails (or silently corrupts). 

Validatin enforces a contract right at that boundary before it even reaches the db or API.

### c) What risks exist if retries are unlimited?
- **Cost**: Every retry is another paid LLM call. A model that keeps failing validation can run up an unexpectedly large bill.
- **Latency**: A request could HANG INDEFINITELY instead of ever returning to the user.
- **No termination**: if the model simply can’t produce a valid answer for that input, unlimited retries never stop. That’s why PydanticAI caps retries by default and raises an error afterward instead of looping forever.

### d) How can FastAPI be used to serve PydanticAI? Give an example
- FastAPI turns an agent into an HTTP endpoint: a client sends a request, FASTAPI validates it against a Pydantic model, your endpoint calls `agent.run()` - FASTAPI serializes the structured result back as JSON.
- Any other program can then use LLM logic over a plain URL, without an API KEy or knowing Pydantic exists. (exercise restaurant)

```python
@app.post("/restaurant")
async def create_restaurant(query: Prompt):
    result = await restaurant_agent.run(query.prompt, model_settings={"timeout": 120})
    restaurant = result.output  # a validated Restaurant object
    query_duckdb("INSERT INTO restaurants VALUES (?,?,?,?,?,?,?)", parameters=[...])
    return restaurant  # FastAPI turns this into JSON automatically
```

## Glossary

Fill in this table either by copying this into your own markdown file or copy it into a spreadsheet if you feel that is easier to work with.

| terminology          | explanation |
| -------------------- | ----------- |
| tools                | Functions registered with an AGENT that the LLM can choose to call midrun. It's how an agent can take actions. |
| dependencies         | Exernal things an agent/tool can use/call to do it's job (a DB connection, an API client) that you pass in at run time via deps=... rather than hard-coding inside the agent. |
| output_type          | The Pydantic model you tell the Agent to force its final answer into, e.g. output_type=Restaurant. PydanticAI validates the reply against it and retries if it doesn’t fit  |
| dependency injection | Supplying an object’s dependencies from the outside instead of it building them itself — e.g. FastAPI handing your endpoint a validated Prompt object, rather than your function parsing raw JSON itself. |
| request body         | The JSON a client sends in a POST request. FastAPI reads and validates it against a Pydantic model declared as a parameter, e.g. query: Prompt in create_restaurant. |
| response model       | The Pydantic model FastAPI uses to validate and shape what an endpoint returns, e.g. response_model=ChatResponse in the chatbot’s api.py. |
| pydantic model       | A Python class inheriting from BaseModel with named, typed fields; Pydantic validates any data assigned to it and raises a clear error on a mismatch. |
| Agent                | PydanticAI’s core object — bundles a model, instructions/system prompt, and optionally output_type/tools/deps, and exposes .run() to talk to the LLM. |
| model                | 	The actual LLM being called (e.g. "nvidia/nemotron-3.5-lightning-30b-a3b"), wrapped in a class like OpenAIChatModel that knows how to speak to that provider’s API. |
| run                  | The method that actually sends a prompt to the LLM and gets a result. |
| system prompt        | Standing instructions sent with every call, invisible to the end user, that shape the model’s behavior. |
| retry loop           | PydanticAI’s built-in behavior of sending an invalid reply (plus the validation error) back to the model and asking it to try again, up to a limited number of attempts, before giving up. |
| tool call            | When the LLM asks to invoke one of the agent’s registered tools with specific arguments instead of (or before) replying with text; the agent runs it and feeds the result back to the model. |
| messages             | The structured record of everything said so far (system prompt, user turns, model replies) — what you pass as message_history so the model “remembers” earlier turns, as in the chatbot. |
