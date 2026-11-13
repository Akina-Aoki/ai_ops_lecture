"""
frontend.py - the page the user sees (built with Streamlit).

WHAT THIS FILE IS FOR:
    Draws a small form to request a restaurant and a table of saved ones.
    It contains NO AI code - it only talks to restaurant_api.py over HTTP
    with `httpx`, so the API must already be running.

HOW IT CONNECTS:
    frontend.py --POST /restaurant--> restaurant_api.py --> AI --> DuckDB
    frontend.py --GET  /restaurants-> restaurant_api.py --> DuckDB

RUN (after `uvicorn restaurant_api:app --reload`):
    streamlit run frontend.py
"""

import streamlit as st
import httpx

API_URL = "http://127.0.0.1:8000"

st.markdown("# Aira's Restaurant Finder")

# A form groups the input + button so the page only reacts on submit, not on every keystroke.
with st.form("restaurant_form"):
    prompt = st.text_input(
        "Describe what you're looking for",
        placeholder="A cheap vegan place near Södermalm, Stockholm",
    )
    submitted = st.form_submit_button("Find a restaurant")
if submitted and prompt:
    # Calls POST /restaurant; .json() turns the API's JSON reply into a dict.
    response = httpx.post(f"{API_URL}/restaurant", json={"prompt": prompt}).json()
    st.success(f"{response['name']} ({response['cuisine']})")
    st.write(response["description"])
    st.write(f"Price: {response['price_level']} | Rating: {response['rating']}/5")
    st.write(f"Hours: {response['opening_hours']} | Location: {response['location']}")

st.markdown("## All saved restaurants")
# Calls GET /restaurants every time Streamlit re-runs this script (e.g.
# after the form above is submitted), so the table always shows the latest.
restaurants = httpx.get(f"{API_URL}/restaurants").json()
if restaurants:
    st.dataframe(restaurants)
else:
    st.write("No restaurants saved yet.")