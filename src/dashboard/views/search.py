"""Transaction Search page — full-text search with export."""
from __future__ import annotations

from datetime import date

import pandas as pd
import streamlit as st

from src.db.repository import TransactionRepository


def render(repo: TransactionRepository, account_ids: list[int], start: date, end: date) -> None:
    if not repo.get_accounts():
        st.info("No accounts linked yet. Go to the **Accounts** tab to connect your first account.")
        return

    if not account_ids:
        st.warning("Select at least one account in the sidebar.")
        return

    # ── Search controls ───────────────────────────────────────────────────────
    col_q, col_cat, col_min, col_max = st.columns([3, 2, 1, 1])

    with col_q:
        query = st.text_input(
            "Search",
            placeholder="Merchant, category, amount…",
            key="search_query",
            label_visibility="collapsed",
        )

    with col_cat:
        cat_data = repo.get_spending_by_category(start.isoformat(), end.isoformat(), account_ids)
        categories = ["All"] + [r["category"] for r in cat_data if r["category"]]
        selected_cat = st.selectbox("Category", options=categories, key="search_cat", label_visibility="collapsed")

    with col_min:
        min_amount = st.number_input("Min $", value=0.0, step=10.0, key="search_min", label_visibility="collapsed")

    with col_max:
        max_amount = st.number_input("Max $", value=0.0, step=10.0, key="search_max",
                                     help="0 = no max", label_visibility="collapsed")

    # ── Fetch and filter ──────────────────────────────────────────────────────
    if query:
        transactions = repo.search_transactions(query, account_ids)
    else:
        transactions = repo.get_transactions({
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "account_ids": account_ids,
            "pending": False,
        })

    # Apply category filter
    if selected_cat != "All":
        transactions = [tx for tx in transactions if tx.category == selected_cat]

    # Apply amount filters
    if min_amount > 0:
        transactions = [tx for tx in transactions if abs(tx.amount) >= min_amount]
    if max_amount > 0:
        transactions = [tx for tx in transactions if abs(tx.amount) <= max_amount]

    # ── Summary strip ─────────────────────────────────────────────────────────
    total = sum(tx.amount for tx in transactions if tx.amount > 0)
    st.markdown(
        f'<p style="font-size:13px;color:#64748b;margin-bottom:12px">'
        f'<strong style="color:#f1f5f9">{len(transactions)}</strong> transactions · '
        f'<strong style="color:#f1f5f9">${total:,.2f}</strong> total spending</p>',
        unsafe_allow_html=True,
    )

    if not transactions:
        st.info("No transactions match your search.")
        return

    # ── Results table ─────────────────────────────────────────────────────────
    df = pd.DataFrame([
        {
            "Date": tx.date,
            "Merchant": tx.merchant_name or tx.name,
            "Category": tx.category or "—",
            "Subcategory": tx.subcategory or "—",
            "Amount": tx.amount,
            "Pending": "Yes" if tx.pending else "No",
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

    # ── Export ────────────────────────────────────────────────────────────────
    st.divider()
    col_exp, _ = st.columns([2, 5])
    with col_exp:
        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="Download CSV",
            data=csv,
            file_name=f"transactions_{start}_{end}.csv",
            mime="text/csv",
            width="stretch",
        )
