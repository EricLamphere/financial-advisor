"""Shared visual theme — CSS injection and Plotly layout defaults."""
from __future__ import annotations

import streamlit as st
import plotly.graph_objects as go

# ── Palette ──────────────────────────────────────────────────────────────────
BLUE = "#6366f1"          # primary accent
GREEN = "#22c55e"         # income / positive
RED = "#f43f5e"           # negative / spending
AMBER = "#f59e0b"         # warning / neutral
SURFACE = "#1e1f2e"       # card background
SURFACE_2 = "#161723"     # page background
BORDER = "#2d2e45"        # subtle border
TEXT_PRIMARY = "#f1f5f9"
TEXT_MUTED = "#94a3b8"

# ── Global CSS ────────────────────────────────────────────────────────────────
_CSS = """
<style>
/* ── Base ─────────────────────────────────────────────────── */
[data-testid="stAppViewContainer"] {
    background: #0f1117;
}
[data-testid="stHeader"] {
    background: transparent;
}
section[data-testid="stSidebar"] {
    background: #13141f;
    border-right: 1px solid #1e1f2e;
}
section[data-testid="stSidebar"] * {
    color: #94a3b8;
}
/* Button text must stay white */
section[data-testid="stSidebar"] [data-testid="stBaseButton-primary"],
section[data-testid="stSidebar"] [data-testid="stBaseButton-primary"] * {
    color: #ffffff !important;
}
/* Multiselect fills sidebar width */
section[data-testid="stSidebar"] [data-testid="stMultiSelect"],
section[data-testid="stSidebar"] [data-testid="stMultiSelect"] > div {
    width: 100% !important;
}
section[data-testid="stSidebar"] [data-baseweb="select"] {
    width: 100% !important;
    min-width: 0 !important;
}

/* ── Metric tiles ─────────────────────────────────────────── */
.tile-grid {
    display: grid;
    gap: 16px;
    margin-bottom: 24px;
}
.tile-grid-4 { grid-template-columns: repeat(4, 1fr); }
.tile-grid-5 { grid-template-columns: repeat(5, 1fr); }
.tile-grid-6 { grid-template-columns: repeat(6, 1fr); }
.tile-grid-7 { grid-template-columns: repeat(7, 1fr); }
.tile {
    background: #1e1f2e;
    border: 1px solid #2d2e45;
    border-radius: 12px;
    padding: 20px 24px;
    display: flex;
    flex-direction: column;
    gap: 6px;
    transition: border-color 0.2s;
}
.tile:hover { border-color: #6366f1; }
.tile-label {
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: #64748b;
    margin: 0;
}
.tile-value {
    font-size: 28px;
    font-weight: 700;
    color: #f1f5f9;
    margin: 0;
    line-height: 1.1;
    font-variant-numeric: tabular-nums;
}
.tile-delta {
    font-size: 12px;
    font-weight: 500;
    margin: 0;
}
.tile-delta.pos { color: #22c55e; }
.tile-delta.neg { color: #f43f5e; }
.tile-delta.neu { color: #64748b; }

/* ── Tab bar ──────────────────────────────────────────────── */
[data-testid="stTabs"] [role="tablist"] {
    background: #13141f;
    border-radius: 10px;
    padding: 4px;
    gap: 2px;
    border: 1px solid #1e1f2e;
    margin-bottom: 24px;
}
[data-testid="stTabs"] [role="tab"] {
    border-radius: 7px !important;
    font-size: 13px !important;
    font-weight: 500 !important;
    color: #64748b !important;
    padding: 8px 18px !important;
    border: none !important;
    background: transparent !important;
    transition: all 0.15s !important;
}
[data-testid="stTabs"] [role="tab"][aria-selected="true"] {
    background: #6366f1 !important;
    color: #ffffff !important;
}
[data-testid="stTabs"] [role="tab"]:hover:not([aria-selected="true"]) {
    background: #1e1f2e !important;
    color: #cbd5e1 !important;
}
[data-testid="stTabs"] [data-baseweb="tab-highlight"] {
    display: none !important;
}
[data-testid="stTabs"] [data-baseweb="tab-border"] {
    display: none !important;
}

/* ── Top rail ─────────────────────────────────────────────── */
.top-rail {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0 0 20px 0;
    border-bottom: 1px solid #1e1f2e;
    margin-bottom: 24px;
    flex-wrap: wrap;
    gap: 12px;
}
.top-rail-title {
    font-size: 22px;
    font-weight: 700;
    color: #f1f5f9;
    margin: 0;
}
.top-rail-sub {
    font-size: 12px;
    color: #64748b;
    margin: 2px 0 0 0;
}

/* ── Dividers ─────────────────────────────────────────────── */
hr[data-testid="stDivider"] {
    border-color: #1e1f2e !important;
    margin: 20px 0 !important;
}

/* ── Dataframe ────────────────────────────────────────────── */
[data-testid="stDataFrame"] {
    border-radius: 10px;
    overflow: hidden;
    border: 1px solid #2d2e45;
}

/* ── Selectbox / inputs ───────────────────────────────────── */
[data-testid="stSelectbox"] > div > div,
[data-testid="stMultiSelect"] > div > div {
    background: #1e1f2e !important;
    border-color: #2d2e45 !important;
    color: #f1f5f9 !important;
    border-radius: 8px !important;
}
[data-testid="stDateInput"] > div > div > input {
    background: #1e1f2e !important;
    border-color: #2d2e45 !important;
    color: #f1f5f9 !important;
    border-radius: 8px !important;
}

/* ── Multiselect tags (selected items) ────────────────────── */
[data-testid="stMultiSelect"] span[data-baseweb="tag"],
[data-baseweb="tag"] {
    background: #2d2e45 !important;
    border: 1px solid #3d3e58 !important;
    border-radius: 6px !important;
}
[data-testid="stMultiSelect"] span[data-baseweb="tag"] span,
[data-baseweb="tag"] span {
    color: #cbd5e1 !important;
}
[data-testid="stMultiSelect"] span[data-baseweb="tag"] [data-testid="stMultiSelectChipAction"],
[data-baseweb="tag"] button,
[data-baseweb="tag"] [role="button"] {
    color: #64748b !important;
    background: transparent !important;
}
[data-baseweb="tag"] button:hover,
[data-baseweb="tag"] [role="button"]:hover {
    color: #f1f5f9 !important;
    background: rgba(255,255,255,0.08) !important;
}

/* ── Section headers ──────────────────────────────────────── */
.section-header {
    font-size: 13px;
    font-weight: 600;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: #64748b;
    margin: 0 0 14px 0;
}

/* ── Plotly charts ────────────────────────────────────────── */
[data-testid="stPlotlyChart"] {
    border-radius: 12px;
    overflow: hidden;
    border: 1px solid #2d2e45;
}

/* ── Sidebar logo ─────────────────────────────────────────── */
.sidebar-logo {
    font-size: 18px;
    font-weight: 700;
    color: #6366f1 !important;
    letter-spacing: -0.02em;
}
.sidebar-logo span {
    color: #f1f5f9 !important;
}

/* ── Buttons ──────────────────────────────────────────────── */
[data-testid="stBaseButton-primary"] {
    background: #6366f1 !important;
    border-color: #6366f1 !important;
    color: #ffffff !important;
}
[data-testid="stBaseButton-primary"]:hover {
    background: #4f52d6 !important;
    border-color: #4f52d6 !important;
}
[data-testid="stBaseButton-secondary"] {
    background: transparent !important;
    border-color: #2d2e45 !important;
    color: #94a3b8 !important;
}
[data-testid="stBaseButton-secondary"]:hover {
    border-color: #6366f1 !important;
    color: #f1f5f9 !important;
}

/* ── Info / warning / error ───────────────────────────────── */
[data-testid="stAlert"] {
    border-radius: 10px !important;
}
[data-testid="stAlert"][kind="error"],
div[data-baseweb="notification"][kind="negative"] {
    background: rgba(244,63,94,0.12) !important;
    border: 1px solid rgba(244,63,94,0.3) !important;
    color: #fca5a5 !important;
}
[data-testid="stAlert"][kind="info"],
div[data-baseweb="notification"][kind="info"] {
    background: rgba(99,102,241,0.1) !important;
    border: 1px solid rgba(99,102,241,0.25) !important;
    color: #a5b4fc !important;
}
[data-testid="stAlert"][kind="warning"] {
    background: rgba(245,158,11,0.1) !important;
    border: 1px solid rgba(245,158,11,0.25) !important;
    color: #fcd34d !important;
}
[data-testid="stAlert"][kind="success"] {
    background: rgba(34,197,94,0.1) !important;
    border: 1px solid rgba(34,197,94,0.25) !important;
    color: #86efac !important;
}
</style>
"""


def inject_css() -> None:
    """Inject global CSS into the Streamlit app."""
    st.markdown(_CSS, unsafe_allow_html=True)


# ── Plotly theme ──────────────────────────────────────────────────────────────

_PLOTLY_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Inter, system-ui, sans-serif", color=TEXT_MUTED, size=12),
    title=dict(font=dict(size=14, color=TEXT_PRIMARY, weight=700), x=0, xanchor="left", pad=dict(b=16)),
    xaxis=dict(
        gridcolor=BORDER,
        linecolor=BORDER,
        tickcolor=BORDER,
        tickfont=dict(color=TEXT_MUTED),
        title_font=dict(color=TEXT_MUTED),
        zeroline=False,
    ),
    yaxis=dict(
        gridcolor=BORDER,
        linecolor="rgba(0,0,0,0)",
        tickfont=dict(color=TEXT_MUTED),
        title_font=dict(color=TEXT_MUTED),
        zeroline=False,
        gridwidth=1,
    ),
    legend=dict(
        bgcolor="rgba(0,0,0,0)",
        font=dict(color=TEXT_MUTED),
        bordercolor=BORDER,
        borderwidth=1,
    ),
    margin=dict(l=16, r=16, t=48, b=16),
    hoverlabel=dict(
        bgcolor=SURFACE,
        bordercolor=BORDER,
        font=dict(color=TEXT_PRIMARY, size=12),
    ),
    coloraxis_showscale=False,
)


def apply_theme(fig: go.Figure, title: str | None = None) -> go.Figure:
    """Apply the dark executive theme to any Plotly figure."""
    fig.update_layout(**_PLOTLY_LAYOUT)
    if title:
        fig.update_layout(title_text=title)
    return fig


# ── Tile helpers ──────────────────────────────────────────────────────────────

def _delta_html(value: float | None, prefix: str = "$", suffix: str = "", label: str = "vs prior period") -> str:
    if value is None:
        return ""
    sign = "+" if value >= 0 else ""
    cls = "pos" if value >= 0 else "neg"
    abs_val = abs(value)
    formatted = f"{prefix}{sign}{abs_val:,.2f}{suffix}" if value >= 0 else f"{prefix}-{abs_val:,.2f}{suffix}"
    if not prefix:
        formatted = f"{sign}{abs_val:,.2f}{suffix}" if value >= 0 else f"-{abs_val:,.2f}{suffix}"
    return f'<p class="tile-delta {cls}">{formatted} {label}</p>'


def metric_tiles(metrics: list[dict]) -> None:
    """Render a row of styled metric tiles.

    Each metric dict supports:
      - label: str
      - value: str  (pre-formatted)
      - delta: float | None   (raw number, shown with sign + color)
      - delta_prefix: str     (default "$")
      - delta_suffix: str     (default "")
      - delta_label: str      (default "vs prior period")
      - value_color: str | None  (hex override for the value text)
    """
    n = len(metrics)
    if n >= 7:
        grid_class = "tile-grid-7"
    elif n >= 6:
        grid_class = "tile-grid-6"
    elif n >= 5:
        grid_class = "tile-grid-5"
    else:
        grid_class = "tile-grid-4"

    parts: list[str] = [f'<div class="tile-grid {grid_class}">']
    for m in metrics:
        delta_part = ""
        if (dv := m.get("delta")) is not None:
            delta_part = _delta_html(
                dv,
                prefix=m.get("delta_prefix", "$"),
                suffix=m.get("delta_suffix", ""),
                label=m.get("delta_label", "vs prior period"),
            )
        color = m.get("value_color", TEXT_PRIMARY)
        label = m["label"]
        value = m["value"]
        parts.append(
            f'<div class="tile">'
            f'<p class="tile-label">{label}</p>'
            f'<p class="tile-value" style="color:{color}">{value}</p>'
            f'{delta_part}'
            f'</div>'
        )
    parts.append("</div>")

    st.markdown("".join(parts), unsafe_allow_html=True)
