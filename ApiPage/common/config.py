import os
import streamlit as st


def get_secret(name: str, default: str = "") -> str:
    """Read secret from st.secrets first, then environment variable."""
    try:
        if name in st.secrets and st.secrets[name]:
            return str(st.secrets[name])
    except Exception:
        pass
    return os.getenv(name, default)


def get_bool(name: str, default: bool = False) -> bool:
    raw = get_secret(name, str(default))
    return str(raw).strip().lower() in {"1", "true", "yes", "y", "on"}

