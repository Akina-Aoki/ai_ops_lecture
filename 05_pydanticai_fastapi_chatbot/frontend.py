"""
frontend.py - the chat web page the user sees (built with Streamlit).

WHAT IS THIS FILE FOR?
    Streamlit turns a normal Python script into a web page. This file draws
    the chat window, takes what the user types, sends it to our FastAPI
    backend (api.py), and shows the answer.

    It contains NO AI code. It only talks to the API over HTTP using `httpx`.
    So the API (api.py) must be running first, otherwise the request fails.

HOW IT CONNECTS TO THE OTHER FILES:
    frontend.py --POST /chat--> api.py --> chat_agent.py --> AI model
    The JSON it sends/reads has the same fields as ChatRequest / ChatResponse
    in data_models.py ("question", "message_history", "response").

HOW TO RUN (after starting the API with `uv run uvicorn api:app --reload`):
    uv run streamlit run frontend.py

IMPORTANT STREAMLIT IDEA:
    Streamlit re-runs this WHOLE script from top to bottom every time the user
    does something (e.g. sends a message). Normal variables are reset on each
    run, so anything we want to remember is stored in `st.session_state`,
    which survives between re-runs (one per browser tab).
"""

import streamlit as st
# httpx is a library for making HTTP requests (like calling a web API).
import httpx


def init_session_states():
    """Create the two memory slots in session_state (only on the first run)."""
    # "messages": what we DISPLAY: a list of {"role": ..., "content": ...}.
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # "message_history": what the AI needs: the conversation in PydanticAI's
    # format, returned by the API. We send it back with every question so the
    # AI remembers the earlier messages.
    if "message_history" not in st.session_state:
        st.session_state.message_history = []


def display_chat_messages():
    """Re-draw all earlier messages (needed because the script re-runs each time)."""
    for message in st.session_state.messages:
        # message["role"] is "user" or "assistant"; Streamlit picks the icon/side.
        with st.chat_message(message["role"]):
            st.markdown(message["content"])


def handle_user_input():
    """Read the user's new message, call the API, and show the reply."""
    # st.chat_input draws the text box at the bottom. When the user presses
    # Enter it returns the text; otherwise it returns None (the `if` is skipped).
    # `:=` assigns the value to `prompt` and checks it in one step.
    if prompt := st.chat_input("Talk to the JokeBot"):
        # Remember the user's message so it can be re-drawn on the next re-run.
        st.session_state.messages.append({"role": "user", "content": prompt})

        # Call our FastAPI backend. The body matches the ChatRequest model.
        # `.json()` turns the API's JSON answer into a Python dict.
        response = httpx.post(
            "http://127.0.0.1:8000/chat",
            json={
                "question": prompt, "message_history": st.session_state.message_history
            },
        ).json()

        # Save the updated conversation to send along with the next question.
        st.session_state.message_history = response.get("message_history")

        # The AI's text answer (the `response` field of ChatResponse).
        bot_response = response.get("response")
        # Shows the raw answer on the page (it's also shown in the chat bubble
        # below, so you'll see it twice; the line is useful for debugging).
        st.write(bot_response)

        # Add a "Ro Båt:" label for display in the chat bubble.
        response = f"Ro Båt: {bot_response}"

        # Draw the new user message and bot reply right away. (Earlier messages
        # are drawn by display_chat_messages(); these two are the newest.)
        with st.chat_message("user"):
            st.markdown(prompt)
        with st.chat_message("assistant"):
            st.markdown(response)

        # Remember the bot's reply for the next re-run.
        st.session_state.messages.append({"role": "assistant", "content": response})


def layout():
    """Draw the page: title, description, old messages, then the input box."""
    st.markdown("# Chat with Ro Båt")
    st.write(
        "RO BÅT is a funny robot that can help you out with programming tasks. However he doesn't directly answer your question, usually he asks another question back."
    )

    display_chat_messages()
    handle_user_input()


# Streamlit runs this file as the main script, so this block runs on every re-run:
# first make sure the memory slots exist, then draw the page.
if __name__ == "__main__":
    init_session_states()
    layout()
