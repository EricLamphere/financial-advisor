"""Savings Goals page — define targets and track progress against net cash flow."""
from __future__ import annotations

from datetime import date, datetime, timezone

import streamlit as st

from src.dashboard.components.theme import GREEN, RED, AMBER, TEXT_PRIMARY
from src.db.models import SavingsGoal
from src.db.repository import TransactionRepository


def render(repo: TransactionRepository, account_ids: list[int], start: date, end: date) -> None:
    if not repo.get_accounts():
        st.info("No accounts linked yet. Go to the **Accounts** tab to connect your first account.")
        return

    # ── Net saved in period ───────────────────────────────────────────────────
    start_str = start.isoformat()
    end_str = end.isoformat()
    income_total = repo.get_income_total(start_str, end_str, account_ids)
    spending_cat = repo.get_spending_by_category(start_str, end_str, account_ids)
    spending_total = sum(r["total"] for r in spending_cat)
    net_saved = income_total - spending_total

    delta_days = (end - start).days + 1
    monthly_net = (net_saved / delta_days * 30) if delta_days else 0.0

    goals = repo.get_savings_goals()

    # ── Add goal form ─────────────────────────────────────────────────────────
    with st.expander("+ Add New Goal", expanded=not goals):
        with st.form("new_goal_form", clear_on_submit=True):
            col1, col2, col3 = st.columns([3, 2, 2])
            name = col1.text_input("Goal name", placeholder="Emergency fund, vacation, etc.")
            target = col2.number_input("Target ($)", min_value=1.0, value=10000.0, step=500.0)
            deadline = col3.date_input("Deadline (optional)", value=None)

            if st.form_submit_button("Add Goal", type="primary"):
                if not name.strip():
                    st.error("Goal name is required.")
                else:
                    repo.create_savings_goal(SavingsGoal(
                        id=None,
                        name=name.strip(),
                        target=target,
                        deadline=deadline.isoformat() if deadline else None,
                        created_at=datetime.now(timezone.utc).isoformat(),
                    ))
                    st.rerun()

    if not goals:
        st.info("No goals yet. Add one above to start tracking.")
        return

    # ── Goal cards ────────────────────────────────────────────────────────────
    st.markdown('<p class="section-header">Your Goals</p>', unsafe_allow_html=True)

    for goal in goals:
        months_to_goal = (goal.target / monthly_net) if monthly_net > 0 else None
        pct = min((net_saved / goal.target * 100) if goal.target else 0, 100)
        pct_display = max(pct, 0)

        if goal.deadline:
            days_left = (date.fromisoformat(goal.deadline) - date.today()).days
            deadline_str = f"{goal.deadline} ({days_left}d left)" if days_left >= 0 else f"{goal.deadline} (past)"
        else:
            deadline_str = "No deadline"

        bar_color = GREEN if pct >= 100 else (AMBER if pct >= 50 else "#6366f1")

        col_main, col_del = st.columns([10, 1])
        with col_main:
            st.markdown(
                f'<div class="tile" style="margin-bottom:12px">'
                f'<div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:12px">'
                f'<div>'
                f'<p class="tile-label">{deadline_str}</p>'
                f'<p style="font-size:18px;font-weight:700;color:#f1f5f9;margin:4px 0">{goal.name}</p>'
                f'</div>'
                f'<p style="font-size:22px;font-weight:700;color:{bar_color};margin:0">'
                f'${goal.target:,.0f}</p>'
                f'</div>'
                f'<div style="background:#0f1117;border-radius:4px;height:6px;margin-bottom:10px">'
                f'<div style="background:{bar_color};width:{pct_display:.1f}%;height:6px;border-radius:4px;'
                f'transition:width 0.4s ease"></div>'
                f'</div>'
                f'<div style="display:flex;justify-content:space-between">'
                f'<span style="font-size:12px;color:#64748b">'
                f'{"Saved " + f"${net_saved:,.0f}" + f" ({pct:.0f}%) this period" if net_saved > 0 else "No savings this period"}'
                f'</span>'
                f'<span style="font-size:12px;color:#64748b">'
                f'{"~" + f"{months_to_goal:.1f} months at current rate" if months_to_goal else "Increase income or reduce spending to project"}'
                f'</span>'
                f'</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
        with col_del:
            if st.button("✕", key=f"del_goal_{goal.id}", help="Delete goal"):
                repo.delete_savings_goal(goal.id)
                st.rerun()
