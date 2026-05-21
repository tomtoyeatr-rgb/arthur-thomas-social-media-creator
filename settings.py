import os


def get_setting(name: str, default: str = "") -> str:
    value = os.getenv(name)
    if value not in {None, ""}:
        return value

    try:
        import streamlit as st

        secret_value = st.secrets.get(name, default)
    except Exception:
        secret_value = default

    if secret_value is None:
        return default
    return str(secret_value)


def setting_bool(name: str, default: bool = False) -> bool:
    value = get_setting(name, str(default)).strip().lower()
    return value in {"1", "true", "yes", "on"}
