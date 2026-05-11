# src/dashboard/Home.py
import streamlit as st

st.set_page_config(
    page_title="PhilCongressAI",
    page_icon="🏛️",
    layout="wide",
)

st.title("🏛️ PhilCongressAI")
st.caption("Philippine Congress Analytics & RAG Chatbot")

st.info(
    "Sprint 0 complete — infrastructure is running. "
    "Data ingestion begins in Sprint 1.",
    icon="🚧",
)

col1, col2, col3 = st.columns(3)
col1.metric("Bills", "—")
col2.metric("Legislators", "—")
col3.metric("Embeddings", "—")
