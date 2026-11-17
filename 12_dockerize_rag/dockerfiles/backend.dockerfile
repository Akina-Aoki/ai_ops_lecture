FROM python:3.13-slim
# Start from a lightweight computer image that already has Python 3.13
# installed. "slim" means it's a smaller version without extra stuff we
# don't need — keeps the final container smaller and faster to build.

WORKDIR /app/
# Set the "current folder" for every command below to /app/.
# It's like doing `cd /app/` before running the rest of this file.

COPY backend backend
# Copy the "backend" folder from your own computer into the container,
# also naming it "backend" inside the container.

ENV PYTHONPATH=/app/backend
# Tells Python "also look inside /app/backend when I write an `import`
# statement." This is what makes `from backend.rag import rag_agent`
# (in api.py) actually work inside the container.

RUN pip install --no-cache-dir uv
# Install "uv" — the tool this project uses instead of plain pip to install
# dependencies (it's faster and reads the project's pyproject.toml file).
# --no-cache-dir just means "don't keep temporary install files around",
# which keeps the container smaller.

WORKDIR /app/backend/src/backend
# Move into the folder that actually contains api.py and the project's
# settings file (pyproject.toml), so the next command knows where to work.

RUN uv sync --no-dev
# Install every package this backend needs to run (reads pyproject.toml).
# --no-dev skips packages that are only useful while developing/testing,
# not needed to actually run the app.

CMD ["uv", "run", "uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]
# This is the command that runs when the container starts: launch our
# FastAPI app. "api:app" means "look inside api.py, for a variable called
# app" — that's the FastAPI() instance we created in api.py.
# --host 0.0.0.0 means "accept connections from outside this container",
# not just from inside it — without this, nobody outside the container
# could reach the API.
# --port 8000 is the port the API listens on inside the container.