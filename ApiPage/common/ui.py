import streamlit as st


def apply_submit_button_style() -> None:
    """Apply a unified style for primary submit buttons."""
    st.markdown(
        """
        <style>
        div[data-testid="stButton"] > button[kind="primary"] {
            background: #ef5b54 !important;
            color: #ffffff !important;
            border: 0 !important;
            border-radius: 16px !important;
            font-weight: 700 !important;
            font-size: 1.05rem !important;
            min-height: 52px !important;
            padding: 0.6rem 1.1rem !important;
            box-shadow: none !important;
        }
        div[data-testid="stButton"] > button[kind="primary"]:hover {
            background: #e14a43 !important;
            color: #ffffff !important;
        }
        div[data-testid="stButton"] > button[kind="primary"]:focus {
            box-shadow: none !important;
            outline: none !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

