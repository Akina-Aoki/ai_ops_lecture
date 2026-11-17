"""
The webpage the user actually sees.
Shows a simple webpage where someone types a question, 
sends it to our API, and sees the answer plus a picture.
"""

import streamlit as st
import requests
from pathlib import Path
import os

# This decides which address to send questions to.
# When running in Docker, docker-compose.yaml sets this to
# "http://backend:8000". If that's not set (e.g. running on your own
# laptop without Docker), we fall back to this default address instead.
BASE_URL = os.getenv("API_URL", default="http://127.0.0.1:8000/rag/query")

# Folder holding the little rabbit-breed pictures we show with each answer.
ASSETS_PATH = Path(__file__).absolute().parents[1] / "assets"


def layout():
    """Builds everything you see on the page: the title, the question box, and the results."""
    st.markdown("# RAGbit")
    st.markdown("Ask a question about different dwarf rabbits")

    text_input = st.text_input(label="Ask a questions")

    # Only actually send the question if the button was clicked AND the
    # user actually typed something (not just spaces).
    if st.button("Send") and text_input.strip() != "":
        # Heads up, this line might be a bug worth asking about: BASE_URL's
        # default value already ends in "/rag/query", and here we add
        # "/rag/query" again — so outside Docker this could send the
        # question to the wrong (doubled-up) address and fail. It only
        # lines up correctly when running inside Docker, where API_URL is
        # just "http://backend:8000" with no path on the end.
        response = requests.post(f"{BASE_URL}/rag/query", json={"prompt": text_input})

        data = response.json()

        st.markdown("## Question:")
        st.markdown(text_input)

        st.markdown("## Answer:")
        st.markdown(data.get("answer"))

        st.markdown("## Source:")
        st.markdown(data.get("filepath"))

        # Show the rabbit-breed picture matching whichever file the AI
        # said it used, e.g. "holland_lop.png".
        st.image(ASSETS_PATH / f"{data.get('filename')}.png")


# Only run the page-building code if this file is run directly
# (e.g. `streamlit run app.py`), not if something else imports from it.
if __name__ == "__main__":
    layout()