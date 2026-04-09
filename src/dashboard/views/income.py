"""Income page — total income, sources, and income vs spending comparison."""
from __future__ import annotations

from datetime import date, timedelta

import streamlit as st

from src.dashboard.components.charts import (
    income_by_source_chart,
    income_over_time_chart,
    income_vs_spending_chart,
)
from src.dashboard.components.theme import metric_tiles, GREEN, RED, TEXT_PRIMARY
from src.db.repository import TransactionRepository


def render(repo: TransactionRepository, account_ids: list[int], start: date, end: date) -> None:
    if not repo.get_accounts():
        st.info("No accounts linked yet. Go to the **Accounts** tab to connect your first account.")
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

    delta_days = (end - start).days + 1
    prev_end = start - timedelta(days=1)
    prev_start = prev_end - timedelta(days=delta_days - 1)
    prev_income = repo.get_income_total(prev_start.isoformat(), prev_end.isoformat(), account_ids)

    metric_tiles([
        {
            "label": "Total Income",
            "value": f"${income_total:,.2f}",
            "delta": income_total - prev_income,
            "value_color": GREEN,
        },
        {
            "label": "Total Spending",
            "value": f"${spending_total:,.2f}",
        },
        {
            "label": "Net",
            "value": f"${net:,.2f}",
            "value_color": GREEN if net >= 0 else RED,
        },
        {
            "label": "Savings Rate",
            "value": f"{savings_rate:.1f}%",
            "value_color": GREEN if savings_rate >= 20 else (TEXT_PRIMARY if savings_rate >= 0 else RED),
        },
    ])

    # ── Income sources breakdown ──────────────────────────────────────────────
    col_left, col_right = st.columns(2)

    with col_left:
        st.markdown('<p class="section-header">Income Sources</p>', unsafe_allow_html=True)
        if income_by_cat:
            for row in income_by_cat:
                pct = (row["total"] / income_total * 100) if income_total else 0
                label = _fmt_category(row["category"])
                bar_w = int(pct)
                st.markdown(
                    f"""
                    <div style="margin-bottom:10px">
                        <div style="display:flex;justify-content:space-between;margin-bottom:4px">
                            <span style="font-size:13px;color:#cbd5e1">{label}</span>
                            <span style="font-size:13px;font-weight:600;color:#f1f5f9">${row['total']:,.0f} <span style="color:#64748b;font-weight:400">({pct:.0f}%)</span></span>
                        </div>
                        <div style="background:#1e1f2e;border-radius:4px;height:5px">
                            <div style="background:#22c55e;width:{bar_w}%;height:5px;border-radius:4px"></div>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
        else:
            st.info("No income transactions found in this period.")

    with col_right:
        display_data = [
            {"category": _fmt_category(r["category"]), "total": r["total"]}
            for r in income_by_cat
        ]
        st.plotly_chart(income_by_source_chart(display_data), width="stretch", key="income_by_source")

    st.divider()

    granularity = st.selectbox(
        "Granularity",
        options=["Daily", "Weekly", "Monthly", "Yearly"],
        index=2,
        key="income_granularity",
    )
    gran_key = {"Daily": "day", "Weekly": "week", "Monthly": "month", "Yearly": "year"}[granularity]

    income_over_time = repo.get_income_over_time(start_str, end_str, account_ids, gran_key)
    spending_over_time = repo.get_spending_over_time(start_str, end_str, account_ids, gran_key)

    col_a, col_b = st.columns(2)
    with col_a:
        st.plotly_chart(
            income_over_time_chart(income_over_time, title=f"{granularity} Income"),
            width="stretch",
            key="income_over_time",
        )
    with col_b:
        st.plotly_chart(
            income_vs_spending_chart(income_over_time, spending_over_time),
            width="stretch",
            key="income_income_vs_spending",
        )


def _fmt_category(raw: str) -> str:
    return raw.removeprefix("INCOME_").replace("_", " ").title() or raw
