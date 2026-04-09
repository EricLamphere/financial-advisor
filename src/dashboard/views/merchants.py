"""Merchants page — per-merchant spending breakdown."""
from __future__ import annotations

from datetime import date

import streamlit as st

from src.dashboard.components.charts import merchant_bar_chart
from src.db.repository import TransactionRepository


def render(repo: TransactionRepository, account_ids: list[int], start: date, end: date) -> None:
    st.title("Merchants")

    if not repo.get_accounts():
        st.info("No accounts linked. Go to **Accounts** to connect one.")
        return

    if not account_ids:
        st.warning("Select at least one account in the sidebar.")
        return

    top_n = st.slider("Top N merchants", min_value=5, max_value=50, value=15, key="merch_top_n")

    data = repo.get_spending_by_merchant(start.isoformat(), end.isoformat(), account_ids)
    if not data:
        st.info("No transactions found for the selected period.")
        return

    st.plotly_chart(merchant_bar_chart(data, top_n=top_n), width="stretch")

    st.divider()
    st.subheader("All Merchants")

    search = st.text_input("Search merchant", key="merch_search").lower()
    filtered = [r for r in data if search in r["merchant_name"].lower()] if search else data

    import pandas as pd
    df = pd.DataFrame([
        {
            "Merchant": r["merchant_name"],
            "Total Spent": r["total"],
            "Transactions": r["count"],
            "Last Purchase": r["last_date"],
            "Avg per Transaction": r["total"] / r["count"] if r["count"] else 0.0,
        }
        for r in filtered
    ])
    st.dataframe(
        df,
        width="stretch",
        hide_index=True,
        column_config={
            "Total Spent": st.column_config.NumberColumn(format="dollar"),
            "Avg per Transaction": st.column_config.NumberColumn(format="dollar"),
        },
    )
