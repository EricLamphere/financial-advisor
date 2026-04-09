"""Categories page — spending breakdown by category."""
from __future__ import annotations

from datetime import date

import streamlit as st

from src.dashboard.components.charts import category_bar_chart, category_pie_chart
from src.db.repository import TransactionRepository


def render(repo: TransactionRepository, account_ids: list[int], start: date, end: date) -> None:
    st.title("Spending by Category")

    if not repo.get_accounts():
        st.info("No accounts linked. Go to **Accounts** to connect one.")
        return

    if not account_ids:
        st.warning("Select at least one account in the sidebar.")
        return

    data = repo.get_spending_by_category(start.isoformat(), end.isoformat(), account_ids)
    if not data:
        st.info("No transactions found for the selected period.")
        return

    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(category_bar_chart(data), width="stretch")
    with col2:
        st.plotly_chart(category_pie_chart(data), width="stretch")

    st.divider()
    st.subheader("Category Detail")

    selected_cat = st.selectbox(
        "Drill into category",
        options=["All"] + [r["category"] for r in data],
        key="cat_drill",
    )

    tx_filters = {
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "account_ids": account_ids,
        "pending": False,
    }
    if selected_cat != "All":
        tx_filters["category"] = selected_cat

    transactions = repo.get_transactions(tx_filters)

    if transactions:
        import pandas as pd
        df = pd.DataFrame([
            {
                "Date": tx.date,
                "Merchant": tx.merchant_name or tx.name,
                "Category": tx.category or "—",
                "Amount": tx.amount,
            }
            for tx in transactions
        ])
        st.dataframe(
            df,
            width="stretch",
            hide_index=True,
            column_config={
                "Amount": st.column_config.NumberColumn(format="dollar"),
            },
        )
    else:
        st.info("No transactions match the current filters.")
