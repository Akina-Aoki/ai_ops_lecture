"""
frontend.py - the chat page (Streamlit).

Talks to api.py over HTTP only - no AI code here. The API must be running.

RUN (after `uvicorn api:app --reload`):
    streamlit run frontend.py

Streamlit re-runs this whole script on every interaction, so anything to
remember across re-runs (the conversation) lives in st.session_state.
"""

import streamlit as st
import httpx

API_URL = "http://127.0.0.1:8000"


def init_session_state():
    """Create the two memory slots in session_state (only on the first run)."""
    if "messages" not in st.session_state:
        st.session_state.messages = []  # what we DISPLAY
    if "message_history" not in st.session_state:
        st.session_state.message_history = []  # what the AI needs, PydanticAI's format


def display_messages():
    """Re-draw earlier messages (needed because the script re-runs each time)."""
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])


def handle_user_input():
    """Read the new message, call the API, show and store the reply."""
    if prompt := st.chat_input("Ask a programming question"):
        st.session_state.messages.append({"role": "user", "content": prompt})

        response = httpx.post(
            f"{API_URL}/chat",
            json={
                "question": prompt,
                "message_history": st.session_state.message_history,
            },
            timeout=60,
        ).json()

        # Save the updated conversation to send along with the next question.
        st.session_state.message_history = response["message_history"]
        bot_reply = response["response"]

        with st.chat_message("user"):
            st.markdown(prompt)
        with st.chat_message("assistant"):
            st.markdown(bot_reply)

        st.session_state.messages.append({"role": "assistant", "content": bot_reply})


def layout():
    st.markdown("# Socratic Programming Tutor")
    st.write(
        "Ask a programming question. Instead of the answer, you'll get a "
        "guiding question back - the point is to think it through yourself."
    )
    display_messages()
    handle_user_input()


if __name__ == "__main__":
    init_session_state()
    layout()