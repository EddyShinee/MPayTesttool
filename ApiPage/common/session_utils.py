import uuid
import pyperclip
import streamlit as st


def stable_key_prefix(page_name: str) -> str:
    return page_name.lower().replace(" ", "_")


def init_clipboard_value(session_key: str, prefix: str = "", fallback: str = "") -> str:
    if session_key not in st.session_state:
        try:
            clip = pyperclip.paste()
            st.session_state[session_key] = clip if (clip.startswith(prefix) if prefix else bool(clip)) else fallback
        except Exception:
            st.session_state[session_key] = fallback
    return st.session_state[session_key]


def init_client_id(session_key: str) -> str:
    if session_key not in st.session_state:
        st.session_state[session_key] = str(uuid.uuid4()).replace("-", "").upper()
    return st.session_state[session_key]

