# PydanticAI FastAPI

- [Lecture Video](https://youtu.be/mp650k5T2T8)

- ![PydanticAI FastAPI Architecture](04_pydanticai_fastapi.png) 

## Install dependencies
```
 uv add uvicorn fastapi duckdb python -dotenv
 -- pydantic-ai (if not exists yet in toml)
```

## Google API Key
- [Google AI Studio](https://aistudio.google.com/docs/api-key)

## Running the models in FastAPI
- cd into 04 file and src
- `uv run uvicorn movies_api:app --reload`
- `http://127.0.0.1:8000/movies`
- `http://127.0.0.1:8000/docs`


> [!Note]
> in the video I have used gemini, but in this code here I have used OpenRouter API. If you want to go for free API, gemini is quite limited and very easy to reach the roof. Using OpenRouterAPI you can experiment much more before reaching the roof.

> [!NOTE]
> models come and go quite quickly in OpenRouter, some may change their billing, some could be rate limited upstreams or other reasons you can't use the models. The easiest solution here is to check for another model and use that instead


## Read more
- [pydantic docs](https://docs.pydantic.dev/latest/)

