"""Overview page — monthly totals, top categories, top merchants."""
from __future__ import annotations

from datetime import date, timedelta

import streamlit as st

from src.dashboard.components.charts import (
    category_bar_chart,
    spending_by_period_chart,
)
from src.db.repository import TransactionRepository


def render(repo: TransactionRepository, account_ids: list[int], start: date, end: date) -> None:
    st.title("Overview")

    if not repo.get_accounts():
        st.info("No accounts linked yet. Go to the **Accounts** page to connect your first account.")
        return

    if not account_ids:
        st.warning("Select at least one account in the sidebar.")
        return

    start_str = start.isoformat()
    end_str = end.isoformat()

    cat_data = repo.get_spending_by_category(start_str, end_str, account_ids)
    total = sum(r["total"] for r in cat_data)

    # Previous period for delta
    delta_days = (end - start).days + 1
    prev_end = start - timedelta(days=1)
    prev_start = prev_end - timedelta(days=delta_days - 1)
    prev_cat = repo.get_spending_by_category(prev_start.isoformat(), prev_end.isoformat(), account_ids)
    prev_total = sum(r["total"] for r in prev_cat)
    delta = total - prev_total

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Spending", f"${total:,.2f}", delta=f"${delta:+,.2f} vs prior period")
    col2.metric("Transactions", sum(r["count"] for r in cat_data))
    col3.metric("Categories", len(cat_data))

    st.divider()

    col_left, col_right = st.columns(2)

    with col_left:
        st.subheader("Top Categories")
        top_cats = sorted(cat_data, key=lambda r: r["total"], reverse=True)[:5]
        for row in top_cats:
            pct = (row["total"] / total * 100) if total else 0
            st.write(f"**{row['category']}** — ${row['total']:,.2f} ({pct:.0f}%)")

    with col_right:
        st.subheader("Top Merchants")
        merchant_data = repo.get_spending_by_merchant(start_str, end_str, account_ids)
        top_merch = sorted(merchant_data, key=lambda r: r["total"], reverse=True)[:5]
        for row in top_merch:
            st.write(f"**{row['merchant_name']}** — ${row['total']:,.2f}")

    st.divider()
    granularity = st.selectbox(
        "Spending chart granularity",
        options=["Daily", "Weekly", "Monthly", "Yearly"],
        index=2,
        key="overview_granularity",
    )
    granularity_key = {"Daily": "day", "Weekly": "week", "Monthly": "month", "Yearly": "year"}[granularity]
    period_data = repo.get_spending_over_time(start_str, end_str, account_ids, granularity_key)
    st.plotly_chart(spending_by_period_chart(period_data, title=f"{granularity} Spending"), width="stretch")
