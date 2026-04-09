"""Income page — total income, sources, and income vs spending comparison."""
from __future__ import annotations

from datetime import date, timedelta

import streamlit as st

from src.dashboard.components.charts import (
    income_by_source_chart,
    income_over_time_chart,
    income_vs_spending_chart,
)
from src.db.repository import TransactionRepository


def render(repo: TransactionRepository, account_ids: list[int], start: date, end: date) -> None:
    st.title("Income")

    if not repo.get_accounts():
        st.info("No accounts linked yet. Go to the **Accounts** page to connect your first account.")
        return

    if not account_ids:
        st.warning("Select at least one account in the sidebar.")
        return

    start_str = start.isoformat()
    end_str = end.isoformat()

    income_total = repo.get_income_total(start_str, end_str, account_ids)
    income_by_cat = repo.get_income_by_category(start_str, end_str, account_ids)

    spending_cat = repo.get_spending_by_category(start_str, end_str, account_ids)
    spending_total = sum(r["total"] for r in spending_cat)

    net = income_total - spending_total
    savings_rate = (net / income_total * 100) if income_total else 0.0

    # Previous period for deltas
    delta_days = (end - start).days + 1
    prev_end = start - timedelta(days=1)
    prev_start = prev_end - timedelta(days=delta_days - 1)
    prev_income = repo.get_income_total(prev_start.isoformat(), prev_end.isoformat(), account_ids)
    income_delta = income_total - prev_income

    col1, col2, col3, col4 = st.columns(4)
    col1.metric(
        "Total Income",
        f"${income_total:,.2f}",
        delta=f"${income_delta:+,.2f} vs prior period",
    )
    col2.metric("Total Spending", f"${spending_total:,.2f}")
    col3.metric(
        "Net",
        f"${net:,.2f}",
        delta_color="normal" if net >= 0 else "inverse",
    )
    col4.metric("Savings Rate", f"{savings_rate:.1f}%")

    st.divider()

    col_left, col_right = st.columns(2)

    with col_left:
        st.subheader("Income by Source")
        if income_by_cat:
            for row in income_by_cat:
                pct = (row["total"] / income_total * 100) if income_total else 0
                label = _format_category(row["category"])
                st.write(f"**{label}** — ${row['total']:,.2f} ({pct:.0f}%)")
        else:
            st.info("No income transactions found in this period.")

    with col_right:
        st.plotly_chart(income_by_source_chart(
            [{"category": _format_category(r["category"]), "total": r["total"]} for r in income_by_cat]
        ), width="stretch")

    st.divider()

    granularity = st.selectbox(
        "Chart granularity",
        options=["Daily", "Weekly", "Monthly", "Yearly"],
        index=2,
        key="income_granularity",
    )
    granularity_key = {"Daily": "day", "Weekly": "week", "Monthly": "month", "Yearly": "year"}[granularity]

    income_over_time = repo.get_income_over_time(start_str, end_str, account_ids, granularity_key)
    spending_over_time = repo.get_spending_over_time(start_str, end_str, account_ids, granularity_key)

    col_a, col_b = st.columns(2)
    with col_a:
        st.plotly_chart(
            income_over_time_chart(income_over_time, title=f"{granularity} Income"),
            width="stretch",
        )
    with col_b:
        st.plotly_chart(
            income_vs_spending_chart(income_over_time, spending_over_time),
            width="stretch",
        )


def _format_category(raw: str) -> str:
    """Convert INCOME_WAGES → Wages, INCOME_OTHER_INCOME → Other Income, etc."""
    label = raw.removeprefix("INCOME_").replace("_", " ").title()
    return label if label else raw
