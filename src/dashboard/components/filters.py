"""Reusable Streamlit filter widgets."""
from __future__ import annotations

from datetime import date, datetime


def date_range_filter(
    key_prefix: str = "main",
    default_start: date | None = None,
    default_end: date | None = None,
) -> tuple[date, date]:
    """Render start/end date pickers. Returns (start_date, end_date)."""
    import streamlit as st

    today = date.today()
    if default_start is None:
        default_start = today.replace(day=1)
    if default_end is None:
        default_end = today

    col1, col2 = st.columns(2)
    with col1:
        start = st.date_input("From", value=default_start, key=f"{key_prefix}_start")
    with col2:
        end = st.date_input("To", value=default_end, key=f"{key_prefix}_end")

    return start, end


def account_filter(accounts: list, key: str = "account_filter") -> list[int]:
    """Render a multi-select for accounts. Returns list of selected account IDs."""
    import streamlit as st

    if not accounts:
        return []

    options = {f"{a.institution_name} — {a.account_name}": a.id for a in accounts}
    selected_labels = st.multiselect(
        "Accounts",
        options=list(options.keys()),
        default=list(options.keys()),
        key=key,
    )
    return [options[label] for label in selected_labels]


def category_filter(categories: list[str], key: str = "category_filter") -> list[str]:
    """Render a multi-select for transaction categories."""
    import streamlit as st

    if not categories:
        return []

    selected = st.multiselect(
        "Categories",
        options=categories,
        default=categories,
        key=key,
    )
    return selected
