"""Cash Flow Forecast page — recurring detection and 90-day projection."""
from __future__ import annotations

from datetime import date, timedelta
from statistics import mean

import streamlit as st

from src.dashboard.components.charts import cashflow_forecast_chart
from src.dashboard.components.theme import AMBER, GREEN, RED, TEXT_PRIMARY, metric_tiles
from src.db.repository import TransactionRepository


_DAYS_PER_FREQ = {
    "Weekly": 7,
    "Biweekly": 14,
    "Monthly": 30,
    "Quarterly": 91,
    "Annual": 365,
}

_FREQ_TOLERANCE = {
    "Weekly": 4,
    "Biweekly": 5,
    "Monthly": 10,
    "Quarterly": 20,
    "Annual": 30,
}


def _classify_frequency(avg_days: float | None) -> str:
    if avg_days is None:
        return "Irregular"
    for label, days in _DAYS_PER_FREQ.items():
        tol = _FREQ_TOLERANCE[label]
        if abs(avg_days - days) <= tol:
            return label
    return "Irregular"


def render(repo: TransactionRepository, account_ids: list[int], start: date, end: date) -> None:
    if not repo.get_accounts():
        st.info("No accounts linked yet. Go to the **Accounts** tab to connect your first account.")
        return

    if not account_ids:
        st.warning("Select at least one account in the sidebar.")
        return

    start_str = start.isoformat()
    end_str = end.isoformat()

    # ── Actual spending history (monthly) ────────────────────────────────────
    history = repo.get_spending_over_time(start_str, end_str, account_ids, "month")
    income_history = repo.get_income_over_time(start_str, end_str, account_ids, "month")

    avg_spending = mean(r["total"] for r in history) if history else 0.0
    avg_income = mean(r["total"] for r in income_history) if income_history else 0.0
    projected_net_monthly = avg_income - avg_spending

    metric_tiles([
        {"label": "Avg Monthly Spending", "value": f"${avg_spending:,.2f}"},
        {"label": "Avg Monthly Income", "value": f"${avg_income:,.2f}", "value_color": GREEN},
        {"label": "Projected Monthly Net", "value": f"${projected_net_monthly:,.2f}",
         "value_color": GREEN if projected_net_monthly >= 0 else RED},
        {"label": "Projected 90-day Net", "value": f"${projected_net_monthly * 3:,.2f}",
         "value_color": GREEN if projected_net_monthly >= 0 else RED},
    ])

    # ── Forecast: project 3 months forward from end of range ────────────────
    today = date.today()
    forecast_months = []
    for i in range(1, 4):
        future = end + timedelta(days=30 * i)
        forecast_months.append({
            "period": future.strftime("%Y-%m"),
            "total": avg_spending,
        })

    col_a, col_b = st.columns(2)
    with col_a:
        st.plotly_chart(
            cashflow_forecast_chart(history, forecast_months),
            width="stretch",
            key="cashflow_spending_forecast",
        )
    with col_b:
        st.plotly_chart(
            cashflow_forecast_chart(income_history, []),
            width="stretch",
            key="cashflow_income_actual",
        )

    st.divider()

    # ── Recurring transactions ────────────────────────────────────────────────
    st.markdown('<p class="section-header">Detected Recurring Charges</p>', unsafe_allow_html=True)

    col_ctrl, _ = st.columns([1, 3])
    with col_ctrl:
        min_occ = st.slider("Min occurrences", 2, 10, 3, key="recur_min_occ")

    recurring = repo.get_recurring_candidates(account_ids, min_occurrences=min_occ)

    if not recurring:
        st.info("No recurring patterns detected. Try lowering the minimum occurrences.")
        return

    # Classify and show only non-irregular
    classified = [
        {**r, "frequency": _classify_frequency(r.get("avg_days_between"))}
        for r in recurring
    ]
    regular = [r for r in classified if r["frequency"] != "Irregular"]
    irregular = [r for r in classified if r["frequency"] == "Irregular"]

    if regular:
        monthly_recurring_total = sum(
            r["avg_amount"] * (30 / _DAYS_PER_FREQ.get(r["frequency"], 30))
            for r in regular
        )
        st.markdown(
            f'<p style="font-size:13px;color:#94a3b8;margin-bottom:16px">'
            f'Estimated monthly cost of recurring charges: '
            f'<strong style="color:#f1f5f9">${monthly_recurring_total:,.2f}</strong></p>',
            unsafe_allow_html=True,
        )

    for row in classified[:30]:
        freq = row["frequency"]
        freq_color = {"Weekly": GREEN, "Biweekly": GREEN, "Monthly": AMBER,
                      "Quarterly": AMBER, "Annual": "#64748b", "Irregular": "#475569"}.get(freq, "#475569")
        st.markdown(
            f'<div style="display:flex;justify-content:space-between;align-items:center;'
            f'padding:10px 0;border-bottom:1px solid #1e1f2e">'
            f'<div>'
            f'<span style="font-size:13px;color:#cbd5e1">{row["merchant"]}</span>'
            f'<span style="font-size:11px;color:#64748b;margin-left:10px">'
            f'{row["occurrences"]}x · last {row["last_seen"]}</span>'
            f'</div>'
            f'<div style="display:flex;align-items:center;gap:16px">'
            f'<span style="font-size:11px;font-weight:600;color:{freq_color};'
            f'background:rgba(0,0,0,0.2);padding:2px 8px;border-radius:99px;'
            f'border:1px solid {freq_color}40">{freq}</span>'
            f'<span style="font-size:13px;font-weight:600;color:#f1f5f9">${row["avg_amount"]:,.2f}</span>'
            f'</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
