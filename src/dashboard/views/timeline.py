"""Timeline page — spending over time with cumulative view."""
from __future__ import annotations

from datetime import date

import streamlit as st

from src.dashboard.components.charts import spending_timeline, cumulative_area_chart
from src.db.repository import TransactionRepository


def render(repo: TransactionRepository, account_ids: list[int], start: date, end: date) -> None:
    if not repo.get_accounts():
        st.info("No accounts linked. Go to **Accounts** to connect one.")
        return

    if not account_ids:
        st.warning("Select at least one account in the sidebar.")
        return

    col_ctrl, _ = st.columns([1, 3])
    with col_ctrl:
        granularity = st.selectbox(
            "Granularity",
            options=["day", "week", "month"],
            index=2,
            key="timeline_granularity",
            format_func=lambda x: x.title(),
        )

    data = repo.get_spending_over_time(
        start.isoformat(), end.isoformat(), account_ids, granularity
    )
    if not data:
        st.info("No transactions found for the selected period.")
        return

    st.plotly_chart(spending_timeline(data, granularity=granularity), width="stretch", key="timeline_spending")

    cumulative = []
    running = 0.0
    for row in sorted(data, key=lambda r: r["period"]):
        running += row["total"]
        cumulative.append({"period": row["period"], "cumulative": running})

    st.plotly_chart(
        cumulative_area_chart(cumulative, title="Cumulative Spending"),
        width="stretch",
        key="timeline_cumulative",
    )
