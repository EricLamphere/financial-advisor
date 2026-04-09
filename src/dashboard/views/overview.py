"""Overview — daily financial command center."""
from __future__ import annotations

from datetime import date, timedelta

import streamlit as st

from src.dashboard.components.charts import (
    account_balances_donut,
    income_vs_spending_chart,
    running_net_chart,
    spending_donut,
)
from src.dashboard.components.theme import (
    AMBER, GREEN, RED, TEXT_PRIMARY,
    metric_tiles,
)
from src.db.repository import TransactionRepository

_FREQ_DAYS = {"Weekly": 7, "Biweekly": 14, "Monthly": 30, "Quarterly": 91, "Annual": 365}
_FREQ_TOL  = {"Weekly": 4, "Biweekly": 5, "Monthly": 10, "Quarterly": 20, "Annual": 30}


def _classify_freq(avg_days: float | None) -> str:
    if avg_days is None:
        return "Irregular"
    for label, days in _FREQ_DAYS.items():
        if abs(avg_days - days) <= _FREQ_TOL[label]:
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

    # ── Fetch all data up front ───────────────────────────────────────────────
    cat_data = repo.get_spending_by_category(start_str, end_str, account_ids)
    spending_total = sum(r["total"] for r in cat_data)
    income_total = repo.get_income_total(start_str, end_str, account_ids)
    net = income_total - spending_total
    savings_rate = (net / income_total * 100) if income_total else 0.0

    delta_days = (end - start).days + 1
    prev_end = start - timedelta(days=1)
    prev_start = prev_end - timedelta(days=delta_days - 1)
    prev_spending = sum(
        r["total"] for r in
        repo.get_spending_by_category(prev_start.isoformat(), prev_end.isoformat(), account_ids)
    )
    prev_income = repo.get_income_total(prev_start.isoformat(), prev_end.isoformat(), account_ids)

    latest_balances = repo.get_latest_balances(account_ids)
    assets = sum(r["current"] or 0 for r in latest_balances
                 if r["account_type"] in ("depository", "investment", "brokerage"))
    liabilities = sum(r["current"] or 0 for r in latest_balances
                      if r["account_type"] in ("credit", "loan"))
    net_worth = assets - liabilities

    merchant_data = repo.get_spending_by_merchant(start_str, end_str, account_ids)
    recurring = repo.get_recurring_candidates(account_ids, min_occurrences=2)
    income_period = repo.get_income_over_time(start_str, end_str, account_ids, "month")
    spending_period = repo.get_spending_over_time(start_str, end_str, account_ids, "month")

    # ── Row 1: Wealth tiles ───────────────────────────────────────────────────
    st.markdown('<p class="section-header">Wealth</p>', unsafe_allow_html=True)
    metric_tiles([
        {
            "label": "Net Worth",
            "value": f"${net_worth:,.0f}" if latest_balances else "—",
            "value_color": GREEN if net_worth >= 0 else RED,
        },
        {
            "label": "Assets",
            "value": f"${assets:,.0f}" if latest_balances else "—",
            "value_color": GREEN,
        },
        {
            "label": "Liabilities",
            "value": f"${liabilities:,.0f}" if latest_balances else "—",
        },
        {
            "label": "Income",
            "value": f"${income_total:,.2f}",
            "delta": income_total - prev_income,
            "value_color": GREEN,
        },
        {
            "label": "Spending",
            "value": f"${spending_total:,.2f}",
            "delta": spending_total - prev_spending,
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

    if not latest_balances:
        st.caption("No balance data — sync your accounts or click Refresh Balances on the Net Worth tab.")

    # ── Alerts ────────────────────────────────────────────────────────────────
    alerts = _build_alerts(
        cat_data, spending_total, latest_balances,
        income_total, prev_income, spending_total, prev_spending,
    )
    if alerts:
        st.markdown('<p class="section-header">Alerts</p>', unsafe_allow_html=True)
        for level, msg in alerts:
            color = {"warn": AMBER, "bad": RED, "good": GREEN}[level]
            icon  = {"warn": "⚠", "bad": "↑", "good": "↓"}[level]
            st.markdown(
                f'<div style="display:flex;align-items:center;gap:10px;padding:10px 14px;'
                f'background:#1e1f2e;border-left:3px solid {color};border-radius:0 8px 8px 0;'
                f'margin-bottom:8px">'
                f'<span style="color:{color};font-size:14px">{icon}</span>'
                f'<span style="font-size:13px;color:#cbd5e1">{msg}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )

    st.divider()

    # ── Row 2: Account balances donut + Income vs Spending ───────────────────
    col_donut, col_ivs = st.columns([1, 2])
    with col_donut:
        st.plotly_chart(
            account_balances_donut(latest_balances),
            width="stretch",
            key="overview_balances_donut",
        )
    with col_ivs:
        st.plotly_chart(
            income_vs_spending_chart(income_period, spending_period),
            width="stretch",
            key="overview_income_vs_spending",
        )

    st.divider()

    # ── Row 3: Spending donut + Cumulative net ───────────────────────────────
    col_spend_donut, col_net = st.columns([3, 4])
    with col_spend_donut:
        st.plotly_chart(
            spending_donut(cat_data),
            width="stretch",
            key="overview_spending_donut",
        )
    with col_net:
        st.plotly_chart(
            running_net_chart(income_period, spending_period),
            width="stretch",
            key="overview_running_net",
        )

    st.divider()

    # ── Row 4: Top merchants + Recurring charges ──────────────────────────────
    col_merch, col_recur = st.columns(2)

    with col_merch:
        st.markdown('<p class="section-header">Top Merchants</p>', unsafe_allow_html=True)
        for row in sorted(merchant_data, key=lambda r: r["total"], reverse=True)[:8]:
            st.markdown(
                f'<div style="display:flex;justify-content:space-between;align-items:center;'
                f'padding:8px 0;border-bottom:1px solid #1e1f2e">'
                f'<span style="font-size:13px;color:#cbd5e1;white-space:nowrap;overflow:hidden;'
                f'text-overflow:ellipsis;max-width:65%">{row["merchant_name"]}</span>'
                f'<span style="font-size:13px;font-weight:600;color:#f1f5f9">${row["total"]:,.2f}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )

    with col_recur:
        st.markdown('<p class="section-header">Recurring Charges</p>', unsafe_allow_html=True)
        regular = [
            r for r in recurring
            if _classify_freq(r.get("avg_days_between")) != "Irregular"
        ][:8]

        if regular:
            monthly_total = sum(
                r["avg_amount"] * (30 / _FREQ_DAYS.get(_classify_freq(r.get("avg_days_between")), 30))
                for r in regular
            )
            st.markdown(
                f'<p style="font-size:11px;color:#64748b;margin-bottom:10px">'
                f'Est. <strong style="color:#94a3b8">${monthly_total:,.0f}/mo</strong></p>',
                unsafe_allow_html=True,
            )
            for r in regular:
                freq = _classify_freq(r.get("avg_days_between"))
                freq_color = {
                    "Weekly": GREEN, "Biweekly": GREEN, "Monthly": AMBER,
                    "Quarterly": AMBER, "Annual": "#64748b",
                }.get(freq, "#475569")
                st.markdown(
                    f'<div style="display:flex;justify-content:space-between;align-items:center;'
                    f'padding:8px 0;border-bottom:1px solid #1e1f2e">'
                    f'<span style="font-size:13px;color:#cbd5e1;white-space:nowrap;overflow:hidden;'
                    f'text-overflow:ellipsis;max-width:55%">{r["merchant"]}</span>'
                    f'<div style="display:flex;gap:10px;align-items:center">'
                    f'<span style="font-size:11px;color:{freq_color}">{freq}</span>'
                    f'<span style="font-size:13px;font-weight:600;color:#f1f5f9">${r["avg_amount"]:,.2f}</span>'
                    f'</div></div>',
                    unsafe_allow_html=True,
                )
        else:
            st.caption("No recurring charges detected yet.")


# ── Alert logic ───────────────────────────────────────────────────────────────

def _build_alerts(
    cat_data: list[dict],
    spending_total: float,
    latest_balances: list[dict],
    income_total: float,
    prev_income: float,
    current_spending: float,
    prev_spending: float,
) -> list[tuple[str, str]]:
    alerts: list[tuple[str, str]] = []

    if prev_spending > 0:
        pct_change = (current_spending - prev_spending) / prev_spending * 100
        if pct_change >= 25:
            alerts.append(("bad",
                f"Spending is up {pct_change:.0f}% vs prior period "
                f"(${current_spending:,.0f} vs ${prev_spending:,.0f})"))
        elif pct_change <= -20:
            alerts.append(("good",
                f"Spending is down {abs(pct_change):.0f}% vs prior period — great discipline"))

    if prev_income > 0 and income_total < prev_income * 0.8:
        drop = (prev_income - income_total) / prev_income * 100
        alerts.append(("warn", f"Income is down {drop:.0f}% vs prior period"))

    for row in latest_balances:
        if row["account_type"] == "credit" and row.get("limit_amt") and row["limit_amt"] > 0:
            util = (row["current"] or 0) / row["limit_amt"] * 100
            if util >= 80:
                alerts.append(("bad",
                    f"{row['account_name']} credit utilization is {util:.0f}% — consider paying down"))
            elif util >= 60:
                alerts.append(("warn", f"{row['account_name']} credit utilization is {util:.0f}%"))

    if spending_total > 0:
        for row in cat_data:
            pct = row["total"] / spending_total * 100
            if pct >= 40 and row["total"] > 500:
                label = row["category"] or "Uncategorized"
                alerts.append(("warn",
                    f"{label} is {pct:.0f}% of total spending (${row['total']:,.0f})"))

    if income_total > 0 and current_spending > income_total:
        alerts.append(("bad",
            f"Spending exceeds income by ${current_spending - income_total:,.0f} this period"))

    return alerts
