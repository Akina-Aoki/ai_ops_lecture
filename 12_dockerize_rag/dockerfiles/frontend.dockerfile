FROM python:3.13-slim
# Start from a lightweight computer image that already has Python 3.13
# installed. "slim" means it's a smaller version without extra stuff we
# don't need — keeps the final container smaller and faster to build.

WORKDIR /app/
# Set the "current folder" for every command below to /app/.
# It's like doing `cd /app/` before running the rest of this file.

COPY frontend frontend
# Copy the "frontend" folder from your own computer into the container,
# also naming it "frontend" inside the container.

ENV PYTHONPATH=/app/frontend
# Tells Python "also look inside /app/frontend when I write an `import`
# statement." Without this, Python might not find your frontend code.

RUN pip install --no-cache-dir uv
# Install "uv" — the tool this project uses instead of plain pip to install
# dependencies (it's faster and reads the project's pyproject.toml file).
# --no-cache-dir just means "don't keep temporary install files around",
# which keeps the container smaller.

WORKDIR /app/frontend/src/frontend
# Move into the folder that actually contains app.py and the project's
# settings file (pyproject.toml), so the next command knows where to work.

RUN uv sync --no-dev
# Install every package this frontend needs to run (reads pyproject.toml).
# --no-dev skips packages that are only useful while developing/testing,
# not needed to actually run the app.

CMD [ "uv" , "run", "streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
# This is the command that runs when the container starts: launch our
# Streamlit app (app.py) on port 8501.
# --server.address=0.0.0.0 means "accept connections from outside this
# container", not just from inside it — without this, nobody outside the
# container could reach the page.