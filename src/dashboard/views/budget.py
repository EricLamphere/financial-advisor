"""Budget tab — monthly budget tracking vs. actual spending per category."""
from __future__ import annotations

import calendar
from datetime import date, datetime, timezone
from typing import NamedTuple

import plotly.graph_objects as go
import streamlit as st

from src.dashboard.components.theme import (
    AMBER,
    BLUE,
    BORDER,
    GREEN,
    RED,
    SURFACE,
    TEXT_MUTED,
    TEXT_PRIMARY,
    apply_theme,
)
from src.db.models import BudgetCategory
from src.db.repository import TransactionRepository

# ── Default budgets seeded from spreadsheet ──────────────────────────────────
# (name, monthly_limit, plaid_categories_csv, sort_order)
_DEFAULT_BUDGETS: list[tuple[str, float, str, int]] = [
    ("Housing",               3359.85, "Rent,Mortgage,Utilities,Home Improvement,Home Supplies", 0),
    ("Food",                  1800.00, "Food and Drink,Restaurants,Groceries,Coffee Shop,Fast Food", 1),
    ("Monthly Subscriptions",  440.46, "Service,Subscription,Software,Entertainment,Streaming", 2),
    ("Retirement",            1083.32, "Transfer,Investment,Retirement,401k,IRA", 3),
    ("Car",                    270.00, "Auto,Gas Stations,Parking,Service & Parts,Auto Insurance", 4),
    ("Investments",             50.00, "Brokerage,529,Investment", 5),
]


class _BudgetRow(NamedTuple):
    category: BudgetCategory
    actual: float
    tx_count: int
    pct: float
    remaining: float
    status: str  # "ok" | "warning" | "over"


def _seed_defaults(repo: TransactionRepository) -> None:
    """Insert default budget categories if none exist yet."""
    existing = repo.get_budget_categories()
    if existing:
        return
    now = datetime.now(timezone.utc).isoformat()
    for name, limit, plaid_cats, order in _DEFAULT_BUDGETS:
        repo.upsert_budget_category(BudgetCategory(
            id=None,
            name=name,
            monthly_limit=limit,
            plaid_categories=plaid_cats,
            sort_order=order,
            created_at=now,
        ))


def _match_actual(
    budget_cat: BudgetCategory,
    actuals_by_plaid: dict[str, float],
) -> tuple[float, int]:
    """Sum actual spending for all Plaid categories mapped to this budget category."""
    if not budget_cat.plaid_categories:
        return 0.0, 0
    mapped = {c.strip().lower() for c in budget_cat.plaid_categories.split(",")}
    total = 0.0
    count = 0
    for plaid_cat, row in actuals_by_plaid.items():
        if plaid_cat.lower() in mapped:
            total += row["actual"]
            count += row["tx_count"]
    return total, count


def _build_rows(
    categories: list[BudgetCategory],
    actuals_by_plaid: dict[str, dict],
) -> list[_BudgetRow]:
    rows: list[_BudgetRow] = []
    for cat in categories:
        actual, tx_count = _match_actual(cat, actuals_by_plaid)
        pct = (actual / cat.monthly_limit * 100) if cat.monthly_limit > 0 else 0.0
        remaining = cat.monthly_limit - actual
        if pct >= 100:
            status = "over"
        elif pct >= 80:
            status = "warning"
        else:
            status = "ok"
        rows.append(_BudgetRow(
            category=cat,
            actual=actual,
            tx_count=tx_count,
            pct=pct,
            remaining=remaining,
            status=status,
        ))
    return rows


def _status_color(status: str) -> str:
    return {
        "over": RED,
        "warning": AMBER,
        "ok": GREEN,
    }[status]


def _progress_bar_html(pct: float, color: str) -> str:
    clamped = min(pct, 100)
    overflow = max(pct - 100, 0)
    bar = (
        f'<div style="background:#0f1117;border-radius:4px;height:8px;width:100%;position:relative;overflow:hidden">'
        f'<div style="background:{color};width:{clamped:.1f}%;height:8px;border-radius:4px;'
        f'transition:width 0.4s ease"></div>'
        f'</div>'
    )
    if overflow > 0:
        bar += (
            f'<div style="background:{RED};width:{min(overflow, 100):.1f}%;height:4px;'
            f'border-radius:0 0 4px 4px;margin-top:1px"></div>'
        )
    return bar


def _category_chart(rows: list[_BudgetRow]) -> go.Figure:
    names = [r.category.name for r in rows]
    budgets = [r.category.monthly_limit for r in rows]
    actuals = [r.actual for r in rows]
    colors = [_status_color(r.status) for r in rows]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        name="Budget",
        x=names,
        y=budgets,
        marker_color=BORDER,
        marker_line_width=0,
        hovertemplate="<b>%{x}</b><br>Budget: $%{y:,.0f}<extra></extra>",
    ))
    fig.add_trace(go.Bar(
        name="Actual",
        x=names,
        y=actuals,
        marker_color=colors,
        marker_line_width=0,
        hovertemplate="<b>%{x}</b><br>Actual: $%{y:,.0f}<extra></extra>",
    ))
    fig.update_layout(barmode="overlay", bargap=0.3)
    return apply_theme(fig, "Budget vs. Actual")


def render(repo: TransactionRepository, account_ids: list[int], start: date, end: date) -> None:
    if not repo.get_accounts():
        st.info("No accounts linked yet. Go to the **Accounts** tab to connect your first account.")
        return

    _seed_defaults(repo)

    # Budget tab always operates on the current calendar month
    today = date.today()
    year, month = today.year, today.month
    month_start = today.replace(day=1)
    days_in_month = calendar.monthrange(year, month)[1]
    days_elapsed = (today - month_start).days + 1
    month_progress_pct = days_elapsed / days_in_month * 100

    categories = repo.get_budget_categories()
    if not account_ids:
        st.warning("No accounts selected.")
        return

    actual_rows = repo.get_budget_vs_actual(year, month, account_ids)
    actuals_by_plaid: dict[str, dict] = {
        r["category"]: {"actual": r["actual"], "tx_count": r["tx_count"]}
        for r in actual_rows
    }

    rows = _build_rows(categories, actuals_by_plaid)

    total_budget = sum(r.category.monthly_limit for r in rows)
    total_actual = sum(r.actual for r in rows)
    total_remaining = total_budget - total_actual
    total_pct = (total_actual / total_budget * 100) if total_budget > 0 else 0.0
    over_count = sum(1 for r in rows if r.status == "over")
    warning_count = sum(1 for r in rows if r.status == "warning")

    # ── Month header ─────────────────────────────────────────────────────────
    month_name = today.strftime("%B %Y")
    pace_note = f"Day {days_elapsed} of {days_in_month} — {month_progress_pct:.0f}% through the month"
    expected_spend = total_budget * (days_elapsed / days_in_month)
    pace_delta = total_actual - expected_spend
    pace_label = (
        f"${abs(pace_delta):,.0f} {'over' if pace_delta > 0 else 'under'} pace"
        if abs(pace_delta) > 1 else "on pace"
    )
    pace_color = RED if pace_delta > 0 else GREEN

    st.markdown(
        f'<div style="display:flex;align-items:baseline;gap:16px;margin-bottom:4px">'
        f'<h2 style="font-size:20px;font-weight:700;color:{TEXT_PRIMARY};margin:0">{month_name} Budget</h2>'
        f'<span style="font-size:13px;color:{TEXT_MUTED}">{pace_note}</span>'
        f'<span style="font-size:13px;font-weight:600;color:{pace_color}">{pace_label}</span>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # ── Summary tiles ─────────────────────────────────────────────────────────
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(
            f'<div class="tile"><p class="tile-label">Total Budget</p>'
            f'<p class="tile-value">${total_budget:,.0f}</p>'
            f'<p class="tile-delta neu">per month</p></div>',
            unsafe_allow_html=True,
        )
    with c2:
        actual_color = RED if total_actual > total_budget else TEXT_PRIMARY
        st.markdown(
            f'<div class="tile"><p class="tile-label">Spent This Month</p>'
            f'<p class="tile-value" style="color:{actual_color}">${total_actual:,.0f}</p>'
            f'<p class="tile-delta neu">{total_pct:.0f}% of budget</p></div>',
            unsafe_allow_html=True,
        )
    with c3:
        rem_color = RED if total_remaining < 0 else GREEN
        rem_label = "over budget" if total_remaining < 0 else "remaining"
        st.markdown(
            f'<div class="tile"><p class="tile-label">Remaining</p>'
            f'<p class="tile-value" style="color:{rem_color}">${abs(total_remaining):,.0f}</p>'
            f'<p class="tile-delta neu">{rem_label}</p></div>',
            unsafe_allow_html=True,
        )
    with c4:
        alert_color = RED if over_count > 0 else (AMBER if warning_count > 0 else GREEN)
        alert_text = (
            f"{over_count} over budget" if over_count > 0
            else f"{warning_count} near limit" if warning_count > 0
            else "All on track"
        )
        alert_sub = f"{over_count + warning_count} categories need attention" if (over_count + warning_count) > 0 else f"{len(rows)} categories tracked"
        st.markdown(
            f'<div class="tile"><p class="tile-label">Status</p>'
            f'<p class="tile-value" style="color:{alert_color};font-size:20px">{alert_text}</p>'
            f'<p class="tile-delta neu">{alert_sub}</p></div>',
            unsafe_allow_html=True,
        )

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    # ── Category rows ─────────────────────────────────────────────────────────
    col_left, col_right = st.columns([3, 2])

    with col_left:
        st.markdown(
            '<p style="font-size:13px;font-weight:600;letter-spacing:.06em;'
            'text-transform:uppercase;color:#64748b;margin:0 0 12px 0">Categories</p>',
            unsafe_allow_html=True,
        )
        for row in rows:
            color = _status_color(row.status)
            pct_display = min(row.pct, 100)
            status_icon = "🔴" if row.status == "over" else ("🟡" if row.status == "warning" else "🟢")
            rem_str = (
                f'<span style="color:{RED}">−${abs(row.remaining):,.0f} over</span>'
                if row.remaining < 0
                else f'<span style="color:{TEXT_MUTED}">${row.remaining:,.0f} left</span>'
            )
            st.markdown(
                f'<div class="tile" style="margin-bottom:10px;padding:14px 20px">'
                f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">'
                f'<span style="font-size:14px;font-weight:600;color:{TEXT_PRIMARY}">'
                f'{status_icon} {row.category.name}</span>'
                f'<span style="font-size:13px;color:{color};font-weight:700">'
                f'${row.actual:,.0f} <span style="font-weight:400;color:{TEXT_MUTED}">/ ${row.category.monthly_limit:,.0f}</span>'
                f'</span>'
                f'</div>'
                f'{_progress_bar_html(row.pct, color)}'
                f'<div style="display:flex;justify-content:space-between;margin-top:6px">'
                f'<span style="font-size:11px;color:{TEXT_MUTED}">{row.pct:.0f}% used · {row.tx_count} transactions</span>'
                f'{rem_str}'
                f'</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

    with col_right:
        if rows:
            fig = _category_chart(rows)
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    st.divider()

    # ── Manage budgets ────────────────────────────────────────────────────────
    with st.expander("Manage Budget Categories"):
        st.markdown(
            '<p style="font-size:12px;color:#64748b;margin-bottom:16px">'
            'Set monthly limits per category. Use <b>Plaid categories</b> (comma-separated) '
            'to map transactions automatically.</p>',
            unsafe_allow_html=True,
        )

        editing_key = "budget_editing_id"
        if editing_key not in st.session_state:
            st.session_state[editing_key] = None

        for cat in categories:
            is_editing = st.session_state[editing_key] == cat.id

            if is_editing:
                with st.form(key=f"edit_budget_{cat.id}", clear_on_submit=False):
                    ec1, ec2, ec3 = st.columns([2, 1.5, 3])
                    new_name = ec1.text_input("Name", value=cat.name)
                    new_limit = ec2.number_input(
                        "Monthly ($)", value=cat.monthly_limit, min_value=0.0, step=50.0
                    )
                    new_plaid = ec3.text_input(
                        "Plaid categories (comma-separated)",
                        value=cat.plaid_categories or "",
                    )
                    btn1, btn2, _ = st.columns([1, 1, 4])
                    save = btn1.form_submit_button("Save", type="primary")
                    cancel = btn2.form_submit_button("Cancel")
                    if save:
                        if not new_name.strip():
                            st.error("Name is required.")
                        else:
                            repo.upsert_budget_category(BudgetCategory(
                                id=cat.id,
                                name=new_name.strip(),
                                monthly_limit=new_limit,
                                plaid_categories=new_plaid.strip() or None,
                                sort_order=cat.sort_order,
                                created_at=cat.created_at,
                            ))
                            st.session_state[editing_key] = None
                            st.rerun()
                    if cancel:
                        st.session_state[editing_key] = None
                        st.rerun()
            else:
                row_c1, row_c2, row_c3, row_c4 = st.columns([2, 1.5, 3, 1])
                row_c1.markdown(
                    f'<p style="margin:8px 0;font-size:14px;color:{TEXT_PRIMARY}">{cat.name}</p>',
                    unsafe_allow_html=True,
                )
                row_c2.markdown(
                    f'<p style="margin:8px 0;font-size:14px;color:{TEXT_MUTED}">${cat.monthly_limit:,.2f}</p>',
                    unsafe_allow_html=True,
                )
                row_c3.markdown(
                    f'<p style="margin:8px 0;font-size:12px;color:{TEXT_MUTED}">'
                    f'{cat.plaid_categories or "—"}</p>',
                    unsafe_allow_html=True,
                )
                btn_edit, btn_del = row_c4.columns(2)
                if btn_edit.button("Edit", key=f"edit_btn_{cat.id}"):
                    st.session_state[editing_key] = cat.id
                    st.rerun()
                if btn_del.button("✕", key=f"del_budget_{cat.id}", help="Delete"):
                    repo.delete_budget_category(cat.id)
                    st.rerun()

        st.markdown("---")
        st.markdown("**Add New Category**")
        with st.form("add_budget_form", clear_on_submit=True):
            nc1, nc2, nc3 = st.columns([2, 1.5, 3])
            add_name = nc1.text_input("Name", placeholder="e.g. Healthcare")
            add_limit = nc2.number_input("Monthly ($)", min_value=0.0, value=200.0, step=50.0)
            add_plaid = nc3.text_input(
                "Plaid categories",
                placeholder="e.g. Medical, Pharmacy, Dentist",
            )
            if st.form_submit_button("Add Category", type="primary"):
                if not add_name.strip():
                    st.error("Name is required.")
                else:
                    now = datetime.now(timezone.utc).isoformat()
                    max_order = max((c.sort_order for c in categories), default=-1) + 1
                    repo.upsert_budget_category(BudgetCategory(
                        id=None,
                        name=add_name.strip(),
                        monthly_limit=add_limit,
                        plaid_categories=add_plaid.strip() or None,
                        sort_order=max_order,
                        created_at=now,
                    ))
                    st.rerun()

    # ── Uncategorized spending ────────────────────────────────────────────────
    mapped_plaid_cats: set[str] = set()
    for cat in categories:
        if cat.plaid_categories:
            for c in cat.plaid_categories.split(","):
                mapped_plaid_cats.add(c.strip().lower())

    untracked = [
        r for r in actual_rows
        if r["category"].lower() not in mapped_plaid_cats
        and r["actual"] > 0
    ]
    if untracked:
        with st.expander(f"Untracked Spending ({len(untracked)} Plaid categories not in your budget)"):
            st.markdown(
                '<p style="font-size:12px;color:#64748b;margin-bottom:8px">'
                'These transactions are not mapped to any budget category. '
                'Add them to a category above to track them.</p>',
                unsafe_allow_html=True,
            )
            total_untracked = sum(r["actual"] for r in untracked)
            st.markdown(
                f'<p style="font-size:13px;font-weight:600;color:{AMBER}">Total untracked: ${total_untracked:,.0f}</p>',
                unsafe_allow_html=True,
            )
            for r in sorted(untracked, key=lambda x: x["actual"], reverse=True):
                st.markdown(
                    f'<div style="display:flex;justify-content:space-between;padding:6px 0;'
                    f'border-bottom:1px solid {BORDER}">'
                    f'<span style="font-size:13px;color:{TEXT_PRIMARY}">{r["category"]}</span>'
                    f'<span style="font-size:13px;color:{TEXT_MUTED}">'
                    f'${r["actual"]:,.0f} · {r["tx_count"]} tx</span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
