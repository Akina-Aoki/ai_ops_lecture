"""
Connects to: every other file imports one or both of these constants instead of hardcoding paths — pdfs_to_text.py
ingestion.py use DATA_PATH; 
ingestion.py and rag.py use VECTOR_DATABASE_PATH.
"""

from pathlib import Path

# Folder holding raw source documents (PDFs, then the .txt files converted from them).
# parents[1] = go up one level from this file's folder (backend/) to the project root (11_rag/).

DATA_PATH = Path(__file__).parents[1] / "data"

# Folder where the LanceDB vector database lives on disk.
# A single source of truth: ingestion.py writes here, rag.py reads from here.

VECTOR_DATABASE_PATH = Path(__file__).parents[1] / "knowledge_base"

