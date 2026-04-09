"""Timeline page — spending over time."""
from __future__ import annotations

from datetime import date

import plotly.express as px
import streamlit as st

from src.dashboard.components.charts import spending_timeline
from src.db.repository import TransactionRepository


def render(repo: TransactionRepository, account_ids: list[int], start: date, end: date) -> None:
    st.title("Spending Over Time")

    if not repo.get_accounts():
        st.info("No accounts linked. Go to **Accounts** to connect one.")
        return

    if not account_ids:
        st.warning("Select at least one account in the sidebar.")
        return

    granularity = st.selectbox(
        "Granularity",
        options=["day", "week", "month"],
        index=2,
        key="timeline_granularity",
    )

    data = repo.get_spending_over_time(
        start.isoformat(), end.isoformat(), account_ids, granularity
    )
    if not data:
        st.info("No transactions found for the selected period.")
        return

    st.plotly_chart(spending_timeline(data, granularity=granularity), width="stretch")

    running = []
    cumulative = 0.0
    for row in data:
        cumulative += row["total"]
        running.append({"period": row["period"], "cumulative": cumulative})

    fig = px.area(
        running,
        x="period",
        y="cumulative",
        labels={"cumulative": "Cumulative ($)", "period": "Period"},
        title="Cumulative Spending",
        color_discrete_sequence=["#635bff"],
    )
    st.plotly_chart(fig, width="stretch")
