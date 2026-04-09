"""Pure chart builder functions using Plotly — all styled with the executive dark theme."""
from __future__ import annotations

import plotly.express as px
import plotly.graph_objects as go

from src.dashboard.components.theme import (
    apply_theme,
    BLUE, GREEN, RED, AMBER, BORDER, SURFACE, TEXT_MUTED, TEXT_PRIMARY,
)

# Consistent category color sequence
_PALETTE = [
    "#6366f1", "#22c55e", "#f59e0b", "#f43f5e", "#06b6d4",
    "#a78bfa", "#34d399", "#fb923c", "#60a5fa", "#e879f9",
]


def category_bar_chart(data: list[dict]) -> go.Figure:
    """Vertical bar chart of spending totals by category."""
    if not data:
        return _empty_figure("No category data")
    sorted_data = sorted(data, key=lambda r: r["total"], reverse=True)
    fig = px.bar(
        sorted_data,
        x="category",
        y="total",
        labels={"total": "Amount ($)", "category": ""},
        color="category",
        color_discrete_sequence=_PALETTE,
    )
    fig.update_layout(showlegend=False, xaxis_tickangle=-25)
    fig.update_traces(marker_line_width=0, hovertemplate="<b>%{x}</b><br>$%{y:,.2f}<extra></extra>")
    return apply_theme(fig, "Spending by Category")


def category_pie_chart(data: list[dict]) -> go.Figure:
    """Donut chart of spending by category."""
    if not data:
        return _empty_figure("No category data")
    fig = px.pie(
        data,
        names="category",
        values="total",
        hole=0.55,
        color_discrete_sequence=_PALETTE,
    )
    fig.update_traces(
        textposition="outside",
        textinfo="percent+label",
        hovertemplate="<b>%{label}</b><br>$%{value:,.2f} (%{percent})<extra></extra>",
        marker=dict(line=dict(color="#0f1117", width=2)),
    )
    return apply_theme(fig, "Spending Distribution")


def spending_timeline(data: list[dict], granularity: str = "month") -> go.Figure:
    """Area chart of spending over time."""
    if not data:
        return _empty_figure("No timeline data")
    _titles = {"day": "Daily", "week": "Weekly", "month": "Monthly", "year": "Yearly"}
    title = f"{_titles.get(granularity, granularity.title())} Spending"
    sorted_data = sorted(data, key=lambda r: r["period"])
    fig = go.Figure(go.Scatter(
        x=[r["period"] for r in sorted_data],
        y=[r["total"] for r in sorted_data],
        mode="lines+markers",
        line=dict(color=BLUE, width=2.5),
        marker=dict(color=BLUE, size=5),
        fill="tozeroy",
        fillcolor="rgba(99,102,241,0.12)",
        hovertemplate="<b>%{x}</b><br>$%{y:,.2f}<extra></extra>",
    ))
    return apply_theme(fig, title)


def merchant_bar_chart(data: list[dict], top_n: int = 15) -> go.Figure:
    """Horizontal bar chart of top merchants by total spend."""
    if not data:
        return _empty_figure("No merchant data")
    top = sorted(data, key=lambda r: r["total"], reverse=True)[:top_n]
    top = list(reversed(top))
    fig = go.Figure(go.Bar(
        x=[r["total"] for r in top],
        y=[r["merchant_name"] for r in top],
        orientation="h",
        marker=dict(
            color=[r["total"] for r in top],
            colorscale=[[0, "rgba(99,102,241,0.4)"], [1, "#6366f1"]],
            line=dict(width=0),
        ),
        hovertemplate="<b>%{y}</b><br>$%{x:,.2f}<extra></extra>",
    ))
    fig.update_layout(yaxis=dict(tickfont=dict(size=11)))
    return apply_theme(fig, f"Top {top_n} Merchants by Spend")


def spending_by_period_chart(data: list[dict], title: str = "Spending") -> go.Figure:
    """Bar chart of spending totals by period."""
    if not data:
        return _empty_figure("No data")
    sorted_data = sorted(data, key=lambda r: r["period"])
    fig = go.Figure(go.Bar(
        x=[r["period"] for r in sorted_data],
        y=[r["total"] for r in sorted_data],
        marker=dict(
            color=[r["total"] for r in sorted_data],
            colorscale=[[0, "rgba(99,102,241,0.35)"], [1, "#6366f1"]],
            line=dict(width=0),
        ),
        hovertemplate="<b>%{x}</b><br>$%{y:,.2f}<extra></extra>",
    ))
    return apply_theme(fig, title)


def income_by_source_chart(data: list[dict]) -> go.Figure:
    """Horizontal bar chart of income totals by source."""
    if not data:
        return _empty_figure("No income data")
    sorted_data = sorted(data, key=lambda r: r["total"])
    fig = go.Figure(go.Bar(
        x=[r["total"] for r in sorted_data],
        y=[r["category"] for r in sorted_data],
        orientation="h",
        marker=dict(
            color=[r["total"] for r in sorted_data],
            colorscale=[[0, "rgba(34,197,94,0.35)"], [1, "#22c55e"]],
            line=dict(width=0),
        ),
        hovertemplate="<b>%{y}</b><br>$%{x:,.2f}<extra></extra>",
    ))
    fig.update_layout(yaxis=dict(tickfont=dict(size=11)))
    return apply_theme(fig, "Income by Source")


def income_over_time_chart(data: list[dict], title: str = "Income") -> go.Figure:
    """Area chart of income over time."""
    if not data:
        return _empty_figure("No income data")
    sorted_data = sorted(data, key=lambda r: r["period"])
    fig = go.Figure(go.Scatter(
        x=[r["period"] for r in sorted_data],
        y=[r["total"] for r in sorted_data],
        mode="lines+markers",
        line=dict(color=GREEN, width=2.5),
        marker=dict(color=GREEN, size=5),
        fill="tozeroy",
        fillcolor="rgba(34,197,94,0.12)",
        hovertemplate="<b>%{x}</b><br>$%{y:,.2f}<extra></extra>",
    ))
    return apply_theme(fig, title)


def income_vs_spending_chart(
    income_data: list[dict], spending_data: list[dict]
) -> go.Figure:
    """Grouped bar chart: income (green) vs spending (indigo) by period."""
    if not income_data and not spending_data:
        return _empty_figure("No data")

    all_periods = sorted(
        set(r["period"] for r in income_data) | set(r["period"] for r in spending_data)
    )
    income_map = {r["period"]: r["total"] for r in income_data}
    spending_map = {r["period"]: r["total"] for r in spending_data}

    fig = go.Figure(data=[
        go.Bar(
            name="Income",
            x=all_periods,
            y=[income_map.get(p, 0) for p in all_periods],
            marker=dict(color=GREEN, line=dict(width=0)),
            hovertemplate="<b>Income %{x}</b><br>$%{y:,.2f}<extra></extra>",
        ),
        go.Bar(
            name="Spending",
            x=all_periods,
            y=[spending_map.get(p, 0) for p in all_periods],
            marker=dict(color=BLUE, line=dict(width=0)),
            hovertemplate="<b>Spending %{x}</b><br>$%{y:,.2f}<extra></extra>",
        ),
    ])
    fig.update_layout(barmode="group", bargap=0.2, bargroupgap=0.05)
    return apply_theme(fig, "Income vs Spending")


def cumulative_area_chart(data: list[dict], color: str = BLUE, title: str = "Cumulative") -> go.Figure:
    """Smooth cumulative area chart."""
    if not data:
        return _empty_figure("No data")
    fig = go.Figure(go.Scatter(
        x=[r["period"] for r in data],
        y=[r["cumulative"] for r in data],
        mode="lines",
        line=dict(color=color, width=2.5, shape="spline", smoothing=0.8),
        fill="tozeroy",
        fillcolor=f"rgba({_hex_to_rgb(color)},0.12)",
        hovertemplate="<b>%{x}</b><br>$%{y:,.2f}<extra></extra>",
    ))
    return apply_theme(fig, title)


def account_balances_donut(latest_balances: list[dict]) -> go.Figure:
    """Donut showing current balance per account, coloured by type."""
    if not latest_balances:
        return _empty_figure("No balance data — sync accounts")

    _TYPE_COLORS = {
        "depository": GREEN,
        "investment": "#06b6d4",
        "brokerage":  "#06b6d4",
        "credit":     RED,
        "loan":       "#f97316",
    }
    labels, values, colors = [], [], []
    for row in sorted(latest_balances, key=lambda r: abs(r["current"] or 0), reverse=True):
        name = f"{row['institution_name']} · {row['account_name']}"
        val = abs(row["current"] or 0)
        if val == 0:
            continue
        labels.append(name)
        values.append(val)
        colors.append(_TYPE_COLORS.get(row["account_type"], TEXT_MUTED))

    fig = go.Figure(go.Pie(
        labels=labels,
        values=values,
        hole=0.6,
        marker=dict(colors=colors, line=dict(color="#0f1117", width=2)),
        textposition="outside",
        textinfo="label+percent",
        hovertemplate="<b>%{label}</b><br>$%{value:,.0f}<extra></extra>",
    ))
    # Centre annotation
    assets = sum(r["current"] or 0 for r in latest_balances if r["account_type"] in ("depository", "investment", "brokerage"))
    liabilities = sum(r["current"] or 0 for r in latest_balances if r["account_type"] in ("credit", "loan"))
    nw = assets - liabilities
    fig.add_annotation(
        text=f"<b>${nw:,.0f}</b><br><span style='font-size:10px'>net worth</span>",
        x=0.5, y=0.5, showarrow=False,
        font=dict(size=14, color=GREEN if nw >= 0 else RED),
        xref="paper", yref="paper",
    )
    return apply_theme(fig, "Account Balances")


def spending_donut(cat_data: list[dict]) -> go.Figure:
    """Donut of spending by category."""
    if not cat_data:
        return _empty_figure("No spending data")
    top = sorted(cat_data, key=lambda r: r["total"], reverse=True)[:8]
    fig = go.Figure(go.Pie(
        labels=[r["category"] or "Uncategorized" for r in top],
        values=[r["total"] for r in top],
        hole=0.55,
        marker=dict(colors=_PALETTE, line=dict(color="#0f1117", width=2)),
        textposition="outside",
        textinfo="percent+label",
        hovertemplate="<b>%{label}</b><br>$%{value:,.2f} (%{percent})<extra></extra>",
    ))
    fig.update_layout(margin=dict(l=60, r=60, t=48, b=60))
    return apply_theme(fig, "Spending by Category")


def running_net_chart(income_data: list[dict], spending_data: list[dict]) -> go.Figure:
    """Cumulative net (income − spending) over time — shows if you're building or burning."""
    all_periods = sorted(
        set(r["period"] for r in income_data) | set(r["period"] for r in spending_data)
    )
    if not all_periods:
        return _empty_figure("No data")

    income_map = {r["period"]: r["total"] for r in income_data}
    spending_map = {r["period"]: r["total"] for r in spending_data}

    cumulative, running = [], 0.0
    for p in all_periods:
        running += income_map.get(p, 0) - spending_map.get(p, 0)
        cumulative.append({"period": p, "net": running})

    color = GREEN if running >= 0 else RED
    fig = go.Figure(go.Scatter(
        x=[r["period"] for r in cumulative],
        y=[r["net"] for r in cumulative],
        mode="lines+markers",
        line=dict(color=color, width=2.5, shape="spline", smoothing=0.6),
        marker=dict(size=5, color=color),
        fill="tozeroy",
        fillcolor=f"rgba({_hex_to_rgb(color)},0.10)",
        hovertemplate="<b>%{x}</b><br>Cumulative net $%{y:,.2f}<extra></extra>",
    ))
    fig.add_hline(y=0, line_color=BORDER, line_width=1)
    return apply_theme(fig, "Cumulative Net (Income − Spending)")


def balance_history_chart(data: list[dict]) -> go.Figure:
    """Multi-line chart of account balance history over time."""
    if not data:
        return _empty_figure("No balance history yet — sync an account to populate")

    accounts = list({r["account_name"] for r in data})
    fig = go.Figure()
    for i, name in enumerate(accounts):
        rows = sorted([r for r in data if r["account_name"] == name], key=lambda r: r["date"])
        color = _PALETTE[i % len(_PALETTE)]
        fig.add_trace(go.Scatter(
            x=[r["date"] for r in rows],
            y=[r["current"] for r in rows],
            name=name,
            mode="lines+markers",
            line=dict(color=color, width=2),
            marker=dict(size=4),
            fill="tozeroy",
            fillcolor=f"rgba({_hex_to_rgb(color)},0.06)",
            hovertemplate="<b>" + name + "</b><br>%{x}<br>$%{y:,.2f}<extra></extra>",
        ))
    return apply_theme(fig, "Account Balances Over Time")


def yoy_chart(data: list[dict], years: list[int]) -> go.Figure:
    """Grouped bar chart comparing monthly spending year-over-year."""
    if not data:
        return _empty_figure("No data")

    month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                   "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    fig = go.Figure()
    colors = [BLUE, GREEN, AMBER, RED]
    for i, year in enumerate(years):
        year_rows = [r for r in data if r["year"] == year]
        by_month = {r["month"]: r["total"] for r in year_rows}
        fig.add_trace(go.Bar(
            name=str(year),
            x=month_names,
            y=[by_month.get(m, 0) for m in range(1, 13)],
            marker=dict(color=colors[i % len(colors)], line=dict(width=0)),
            hovertemplate="<b>" + str(year) + " %{x}</b><br>$%{y:,.2f}<extra></extra>",
        ))
    fig.update_layout(barmode="group", bargap=0.15, bargroupgap=0.05)
    return apply_theme(fig, "Year-over-Year Spending")


def cashflow_forecast_chart(history: list[dict], forecast: list[dict]) -> go.Figure:
    """Area chart of actual spending + shaded forecast region."""
    if not history:
        return _empty_figure("No data")

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=[r["period"] for r in history],
        y=[r["total"] for r in history],
        name="Actual",
        mode="lines+markers",
        line=dict(color=BLUE, width=2.5),
        marker=dict(size=4),
        fill="tozeroy",
        fillcolor="rgba(99,102,241,0.1)",
        hovertemplate="<b>%{x}</b><br>$%{y:,.2f}<extra></extra>",
    ))
    if forecast:
        fig.add_trace(go.Scatter(
            x=[r["period"] for r in forecast],
            y=[r["total"] for r in forecast],
            name="Forecast",
            mode="lines+markers",
            line=dict(color=AMBER, width=2, dash="dot"),
            marker=dict(size=4, symbol="circle-open"),
            hovertemplate="<b>%{x} (forecast)</b><br>$%{y:,.2f}<extra></extra>",
        ))
    return apply_theme(fig, "Cash Flow — Actual & Forecast")


def _hex_to_rgb(hex_color: str) -> str:
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"{r},{g},{b}"


def _empty_figure(message: str) -> go.Figure:
    fig = go.Figure()
    fig.add_annotation(
        text=message,
        xref="paper", yref="paper",
        x=0.5, y=0.5,
        showarrow=False,
        font={"size": 14, "color": TEXT_MUTED},
    )
    fig.update_layout(
        xaxis={"visible": False},
        yaxis={"visible": False},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=0, r=0, t=0, b=0),
    )
    return fig
