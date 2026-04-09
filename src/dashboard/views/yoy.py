"""Year-over-Year page — compare spending and income across years."""
from __future__ import annotations

from datetime import date

import streamlit as st

from src.dashboard.components.charts import yoy_chart
from src.dashboard.components.theme import metric_tiles, GREEN, RED
from src.db.repository import TransactionRepository


def render(repo: TransactionRepository, account_ids: list[int], start: date, end: date) -> None:
    if not repo.get_accounts():
        st.info("No accounts linked yet. Go to the **Accounts** tab to connect your first account.")
        return

    if not account_ids:
        st.warning("Select at least one account in the sidebar.")
        return

    current_year = date.today().year
    available_years = list(range(current_year - 4, current_year + 1))

    col_ctrl, _ = st.columns([2, 3])
    with col_ctrl:
        selected_years = st.multiselect(
            "Compare years",
            options=available_years,
            default=[current_year - 1, current_year],
            key="yoy_years",
        )

    if not selected_years or len(selected_years) < 1:
        st.info("Select at least one year to compare.")
        return

    selected_years_sorted = sorted(selected_years)
    data = repo.get_spending_by_month_yoy(account_ids, selected_years_sorted)

    if not data:
        st.info("No transaction data found for the selected years.")
        return

    # ── Year totals summary ───────────────────────────────────────────────────
    tiles = []
    year_totals: dict[int, float] = {}
    for year in selected_years_sorted:
        total = sum(r["total"] for r in data if r["year"] == year)
        year_totals[year] = total

    for i, year in enumerate(selected_years_sorted):
        total = year_totals[year]
        delta = None
        if i > 0:
            prev = year_totals[selected_years_sorted[i - 1]]
            delta = total - prev
        tiles.append({
            "label": str(year),
            "value": f"${total:,.2f}",
            "delta": delta,
        })

    if len(selected_years_sorted) >= 2:
        first = year_totals[selected_years_sorted[0]]
        last = year_totals[selected_years_sorted[-1]]
        change_pct = ((last - first) / first * 100) if first else 0
        tiles.append({
            "label": f"{selected_years_sorted[0]}→{selected_years_sorted[-1]} Change",
            "value": f"{change_pct:+.1f}%",
            "value_color": RED if change_pct > 0 else GREEN,
        })

    metric_tiles(tiles)

    st.plotly_chart(
        yoy_chart(data, selected_years_sorted),
        width="stretch",
        key="yoy_spending_chart",
    )

    # ── Month-by-month delta table ────────────────────────────────────────────
    if len(selected_years_sorted) == 2:
        st.divider()
        st.markdown('<p class="section-header">Month-by-Month Comparison</p>', unsafe_allow_html=True)

        yr_a, yr_b = selected_years_sorted
        month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                       "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        a_map = {r["month"]: r["total"] for r in data if r["year"] == yr_a}
        b_map = {r["month"]: r["total"] for r in data if r["year"] == yr_b}

        rows_html = ""
        for m in range(1, 13):
            a = a_map.get(m, 0)
            b = b_map.get(m, 0)
            diff = b - a
            diff_color = RED if diff > 0 else GREEN
            sign = "+" if diff >= 0 else ""
            rows_html += (
                f'<div style="display:grid;grid-template-columns:1fr 1fr 1fr 1fr;'
                f'padding:8px 0;border-bottom:1px solid #1e1f2e;align-items:center">'
                f'<span style="color:#94a3b8;font-size:13px">{month_names[m-1]}</span>'
                f'<span style="color:#f1f5f9;font-size:13px;text-align:right">${a:,.0f}</span>'
                f'<span style="color:#f1f5f9;font-size:13px;text-align:right">${b:,.0f}</span>'
                f'<span style="color:{diff_color};font-size:13px;text-align:right;font-weight:600">'
                f'{sign}${abs(diff):,.0f}</span>'
                f'</div>'
            )

        st.markdown(
            f'<div style="background:#1e1f2e;border-radius:10px;padding:16px;border:1px solid #2d2e45">'
            f'<div style="display:grid;grid-template-columns:1fr 1fr 1fr 1fr;'
            f'padding-bottom:8px;margin-bottom:4px;border-bottom:1px solid #2d2e45">'
            f'<span style="font-size:11px;font-weight:600;letter-spacing:.06em;text-transform:uppercase;color:#475569">Month</span>'
            f'<span style="font-size:11px;font-weight:600;letter-spacing:.06em;text-transform:uppercase;color:#475569;text-align:right">{yr_a}</span>'
            f'<span style="font-size:11px;font-weight:600;letter-spacing:.06em;text-transform:uppercase;color:#475569;text-align:right">{yr_b}</span>'
            f'<span style="font-size:11px;font-weight:600;letter-spacing:.06em;text-transform:uppercase;color:#475569;text-align:right">Δ</span>'
            f'</div>'
            f'{rows_html}'
            f'</div>',
            unsafe_allow_html=True,
        )
