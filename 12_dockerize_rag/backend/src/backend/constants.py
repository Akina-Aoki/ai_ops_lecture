"""
if you ever move the data folder, you only change it here.
ingestion.py and rag.py both import DATA_PATH/VECTOR_DATABASE_PATH 
from this one place instead of each hardcoding their own path.
"""

from pathlib import Path

# __file__ is a built-in variable Python gives every module — it's the path
# to *this* file on disk. We use it so paths work no matter where you run
# the script from (your laptop, a Docker container, etc.) instead of hardcoding
# something like "C:/Users/you/project/data".
#
# Path(__file__).parents[1] means: "go up one folder from this file's location."
# If this file lives at  backend/src/backend/constants.py
# then parents[0] = backend/src/backend
#      parents[1] = backend/src        <-- this is what we land on

# Folder where the raw PDFs and the extracted .txt files live.
DATA_PATH = Path(__file__).parents[1] / "data"

# Folder where the LanceDB vector database gets stored on disk.
VECTOR_DATABASE_PATH = Path(__file__).parents[1] / "knowledge_base"