"""Streamlit chat UI for the Jetson Edge LLM gateway.

Each browser tab is its own Streamlit session with its own chat history
(st.session_state) and its own session id, which the gateway uses for rate limiting.

Run:  streamlit run frontend/app.py
"""
import hmac
import os
import time
import uuid

import requests
import streamlit as st

GATEWAY_URL = os.getenv("GATEWAY_URL", "http://127.0.0.1:8000").rstrip("/")
GATEWAY_KEY = os.getenv("GATEWAY_KEY", "change-me")
APP_PASSWORD = os.getenv("APP_PASSWORD", "")
MAX_HISTORY = int(os.getenv("MAX_HISTORY_MESSAGES", "6"))

st.set_page_config(page_title="Jetson Edge Chat", page_icon="💬", layout="centered")

# ---- optional password gate -------------------------------------------------
if APP_PASSWORD and not st.session_state.get("authed"):
    st.title("Jetson Edge Chat")
    entered = st.text_input("Password", type="password")
    if entered and hmac.compare_digest(entered, APP_PASSWORD):
        st.session_state["authed"] = True
        st.rerun()
    elif entered:
        st.error("Wrong password.")
    st.stop()

# ---- per-tab state ----------------------------------------------------------
if "sid" not in st.session_state:
    st.session_state["sid"] = uuid.uuid4().hex
if "messages" not in st.session_state:
    st.session_state["messages"] = []


@st.cache_data(ttl=5)
def get_health():
    try:
        return requests.get(f"{GATEWAY_URL}/health", timeout=3).json()
    except (requests.RequestException, ValueError):
        return None


def open_stream(history, temperature, max_tokens):
    """POST to the gateway. Returns (response, None) on success or (None, error text)."""
    payload = {
        "messages": [{"role": m["role"], "content": m["content"]} for m in history],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    headers = {"x-api-key": GATEWAY_KEY, "x-session-id": st.session_state["sid"]}
    try:
        resp = requests.post(f"{GATEWAY_URL}/chat", json=payload, headers=headers,
                             stream=True, timeout=(5, 300))
    except requests.RequestException:
        return None, "Cannot reach the gateway. Check that it is running on port 8000."
    if resp.status_code != 200:
        try:
            detail = resp.json().get("detail", resp.text)
        except ValueError:
            detail = resp.text
        resp.close()
        return None, str(detail)
    resp.encoding = "utf-8"
    return resp, None


def iter_text(resp):
    try:
        for chunk in resp.iter_content(chunk_size=None, decode_unicode=True):
            if chunk:
                yield chunk
    finally:
        resp.close()


# ---- sidebar ----------------------------------------------------------------
health = get_health()
with st.sidebar:
    st.header("Server")
    if health is None:
        st.error("Gateway is offline.")
    elif health.get("model_server") != "ok":
        st.warning("Gateway is up, but the model server is down.")
    else:
        st.success("Online")
        st.caption(f"Model: {health.get('model', 'unknown')}")
        st.caption(f"Active requests: {health.get('inflight', 0)} of {health.get('max_inflight', '?')}")
    st.header("Settings")
    temperature = st.slider("Temperature", 0.0, 1.2, 0.7, 0.1,
                            help="Lower is more focused and repeatable. Higher is more varied.")
    max_tokens = st.slider("Maximum reply length (tokens)", 64, 512, 256, 32)
    if st.button("Clear chat"):
        st.session_state["messages"] = []
        st.rerun()
    st.caption(f"Session {st.session_state['sid'][:8]}")

# ---- chat -------------------------------------------------------------------
st.title("Jetson Edge Chat")
st.caption("Runs on an NVIDIA Jetson Orin Nano. Your messages are processed on this device.")

for msg in st.session_state["messages"]:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("meta"):
            st.caption(msg["meta"])

if prompt := st.chat_input("Ask something"):
    st.session_state["messages"].append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    history = st.session_state["messages"][-MAX_HISTORY:]
    resp, error = open_stream(history, temperature, max_tokens)
    with st.chat_message("assistant"):
        if error:
            st.error(error)
            st.session_state["messages"].pop()  # keep history free of failed turns
        else:
            started = time.perf_counter()
            reply = st.write_stream(iter_text(resp))
            meta = f"{time.perf_counter() - started:.1f} s"
            st.caption(meta)
            st.session_state["messages"].append({"role": "assistant", "content": reply, "meta": meta})
