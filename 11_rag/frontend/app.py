"""
It’s the only piece the end user actually sees and clicks on. Everything else runs behind the scenes.
"""

import streamlit as st
import requests
from pathlib import Path

# Streamlit is a library for building simple web pages purely in Python —
# no HTML/JavaScript needed. Every st.something() call adds something
# visible to the page.
ASSETS_PATH = Path(__file__).absolute().parents[1] / "assets"

def layout():
    st.markdown("# RAGbit")                               # a big heading
    st.markdown("Ask a question about different dwarf rabbits")
    text_input = st.text_input(label="Ask a questions")    # a text box; whatever the user types ends up in this variable

    if st.button("Send") and text_input.strip() != "":
        # requests.post sends the user's question, as JSON, to our FastAPI
        # server (api.py) which must already be running at this address.
        # This is a completely separate program — Streamlit and FastAPI
        # only talk to each other over this network request.
        response = requests.post(
            "http://127.0.0.1:8000/rag/query", json={"prompt": text_input}
        )

        # .json() turns the server's response back into a normal Python
        # dict, with keys matching RagResponse: "answer", "filepath", "filename".
        data = response.json()

        st.markdown("## Question:")
        st.markdown(text_input)

        st.markdown("## Answer:")
        st.markdown(data["answer"])

        st.markdown("## Source:")
        st.markdown(data["filepath"])
 
        # Shows a matching picture, e.g. assets/holland_lop.png,
        # using the breed name the AI returned.
        st.image(ASSETS_PATH / f"{data['filename']}.png")

# This only runs if you execute "streamlit run app.py" directly.
if __name__ == "__main__":
    layout()