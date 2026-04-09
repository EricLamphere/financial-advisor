"""Pure chart builder functions using Plotly."""
from __future__ import annotations

import plotly.express as px
import plotly.graph_objects as go


def category_bar_chart(data: list[dict]) -> go.Figure:
    """Bar chart of spending totals by category."""
    if not data:
        return _empty_figure("No category data")
    fig = px.bar(
        data,
        x="category",
        y="total",
        color="category",
        labels={"total": "Amount ($)", "category": "Category"},
        title="Spending by Category",
    )
    fig.update_layout(showlegend=False, xaxis_tickangle=-30)
    return fig


def category_pie_chart(data: list[dict]) -> go.Figure:
    """Pie chart of spending by category."""
    if not data:
        return _empty_figure("No category data")
    fig = px.pie(
        data,
        names="category",
        values="total",
        title="Spending Distribution",
    )
    return fig


def spending_timeline(data: list[dict], granularity: str = "month") -> go.Figure:
    """Line chart of spending over time."""
    if not data:
        return _empty_figure("No timeline data")

    _labels = {"day": "Date", "week": "Week", "month": "Month", "year": "Year"}
    _titles = {"day": "Daily", "week": "Weekly", "month": "Monthly", "year": "Yearly"}
    period_label = _labels.get(granularity, "Period")
    period_title = _titles.get(granularity, granularity.title())
    fig = px.line(
        data,
        x="period",
        y="total",
        markers=True,
        labels={"total": "Amount ($)", "period": period_label},
        title=f"Spending Over Time ({period_title})",
    )
    fig.update_traces(line_color="#635bff")
    return fig


def merchant_bar_chart(data: list[dict], top_n: int = 15) -> go.Figure:
    """Horizontal bar chart of top merchants by total spend."""
    if not data:
        return _empty_figure("No merchant data")

    top = sorted(data, key=lambda r: r["total"], reverse=True)[:top_n]
    top.reverse()  # plotly renders bottom-to-top for horizontal bars

    fig = px.bar(
        top,
        x="total",
        y="merchant_name",
        orientation="h",
        labels={"total": "Amount ($)", "merchant_name": "Merchant"},
        title=f"Top {top_n} Merchants",
    )
    return fig


def spending_by_period_chart(data: list[dict], title: str = "Spending") -> go.Figure:
    """Bar chart comparing spending totals by period (day/week/month/year)."""
    if not data:
        return _empty_figure("No data")

    sorted_data = sorted(data, key=lambda r: r["period"])
    ordered_periods = [r["period"] for r in sorted_data]
    fig = px.bar(
        sorted_data,
        x="period",
        y="total",
        labels={"total": "Amount ($)", "period": "Period"},
        title=title,
        color="total",
        color_continuous_scale="Blues",
        category_orders={"period": ordered_periods},
    )
    fig.update_layout(coloraxis_showscale=False)
    return fig


def _empty_figure(message: str) -> go.Figure:
    fig = go.Figure()
    fig.add_annotation(
        text=message,
        xref="paper",
        yref="paper",
        x=0.5,
        y=0.5,
        showarrow=False,
        font={"size": 16, "color": "#888"},
    )
    fig.update_layout(
        xaxis={"visible": False},
        yaxis={"visible": False},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    return fig
