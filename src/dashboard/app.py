"""Streamlit dashboard entry point.

Run with:
    streamlit run src/dashboard/app.py
"""
from __future__ import annotations

from datetime import date, timedelta

import streamlit as st

st.set_page_config(
    page_title="Financial Dashboard",
    page_icon="💳",
    layout="wide",
    initial_sidebar_state="expanded",
)

from src.config import load_config
from src.db.repository import TransactionRepository
from src.db.schema import initialize_db
from src.plaid_client import PlaidService
from src.sync.transaction_sync import TransactionSyncer
from src.dashboard.components.theme import inject_css

from src.dashboard.views import (
    budget as budget_page,
    overview,
    categories,
    merchants,
    timeline,
    accounts as accounts_page,
    income as income_page,
    net_worth as net_worth_page,
    cashflow as cashflow_page,
    goals as goals_page,
    search as search_page,
    yoy as yoy_page,
)


@st.cache_resource
def get_config():
    return load_config()


def get_repo(config) -> tuple[TransactionRepository, object]:
    import sqlite3
    conn = sqlite3.connect(config.database_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    initialize_db(conn)
    return TransactionRepository(conn), conn


def main():
    inject_css()

    try:
        config = get_config()
    except EnvironmentError as exc:
        st.error(f"**Configuration error:** {exc}\n\nCopy `.env.example` to `.env` and fill in your Plaid credentials.")
        st.stop()

    repo, _conn = get_repo(config)
    accounts = repo.get_accounts()

    # ── Sidebar — slim, logo + sync only ────────────────────────────────────
    with st.sidebar:
        st.markdown('<p class="sidebar-logo">◈ <span>Finboard</span></p>', unsafe_allow_html=True)
        st.divider()

        account_options = {f"{a.institution_name} — {a.account_name}": a.id for a in accounts}
        selected_labels = st.multiselect(
            "Accounts",
            options=list(account_options.keys()),
            default=list(account_options.keys()),
            key="global_accounts",
            label_visibility="collapsed" if not account_options else "visible",
            placeholder="All accounts",
        )
        account_ids = [account_options[label] for label in selected_labels]

        st.divider()

        if st.button("↻  Sync All", width="stretch", type="primary"):
            plaid_service = PlaidService(config)
            syncer = TransactionSyncer(plaid_service=plaid_service, repository=repo)
            with st.spinner("Syncing…"):
                results = syncer.sync_all_accounts()
            if not results:
                st.info("No accounts linked yet.")
            else:
                total_added = sum(r.added for r in results)
                errors = [e for r in results for e in r.errors]
                if errors:
                    st.error(f"Errors: {'; '.join(errors)}")
                else:
                    st.success(f"+{total_added} new transactions")

    # ── Top rail — date range ────────────────────────────────────────────────
    today = date.today()

    _PRESET_DATES = {
        "Last 30 days":   (today - timedelta(days=30), today),
        "This month":     (today.replace(day=1), today),
        "Last 3 months":  (today - timedelta(days=91), today),
        "Last 6 months":  (today - timedelta(days=182), today),
        "This year":      (today.replace(month=1, day=1), today),
        "Custom":         None,
    }

    # Initialise session state on first run
    if "global_start" not in st.session_state:
        st.session_state["global_start"] = today - timedelta(days=30)
    if "global_end" not in st.session_state:
        st.session_state["global_end"] = today
    if "date_preset" not in st.session_state:
        st.session_state["date_preset"] = "Last 30 days"

    c_title, c_space, c_preset, c_from, c_to = st.columns([3, 1, 2, 1.5, 1.5])

    with c_title:
        st.markdown(
            '<h1 style="font-size:22px;font-weight:700;color:#f1f5f9;margin:0;padding:6px 0">Financial Dashboard</h1>',
            unsafe_allow_html=True,
        )

    with c_preset:
        preset = st.selectbox(
            "Range",
            options=list(_PRESET_DATES.keys()),
            key="date_preset",
            label_visibility="collapsed",
        )

    # When a named preset is chosen, push its dates into session state
    if preset != "Custom":
        preset_start, preset_end = _PRESET_DATES[preset]
        st.session_state["global_start"] = preset_start
        st.session_state["global_end"] = preset_end

    with c_from:
        start = st.date_input("From", key="global_start", label_visibility="collapsed")
    with c_to:
        end = st.date_input("To", key="global_end", label_visibility="collapsed")

    # If the user manually edits dates, switch preset to Custom
    if preset != "Custom":
        preset_start, preset_end = _PRESET_DATES[preset]
        if start != preset_start or end != preset_end:
            st.session_state["date_preset"] = "Custom"
            st.rerun()

    st.divider()

    # ── Tab navigation ───────────────────────────────────────────────────────
    (
        tab_budget, tab_overview, tab_income, tab_net_worth, tab_cashflow, tab_goals,
        tab_search, tab_yoy, tab_categories, tab_merchants, tab_timeline, tab_accounts
    ) = st.tabs([
        "Budget", "Overview", "Income", "Net Worth", "Cash Flow", "Goals",
        "Search", "Year-over-Year", "Categories", "Merchants", "Timeline", "Accounts",
    ])

    with tab_budget:
        budget_page.render(repo, account_ids, start, end)

    with tab_overview:
        overview.render(repo, account_ids, start, end)

    with tab_income:
        income_page.render(repo, account_ids, start, end)

    with tab_net_worth:
        net_worth_page.render(repo, account_ids, config)

    with tab_cashflow:
        cashflow_page.render(repo, account_ids, start, end)

    with tab_goals:
        goals_page.render(repo, account_ids, start, end)

    with tab_search:
        search_page.render(repo, account_ids, start, end)

    with tab_yoy:
        yoy_page.render(repo, account_ids, start, end)

    with tab_categories:
        categories.render(repo, account_ids, start, end)

    with tab_merchants:
        merchants.render(repo, account_ids, start, end)

    with tab_timeline:
        timeline.render(repo, account_ids, start, end)

    with tab_accounts:
        accounts_page.render(repo, config)


if __name__ == "__main__":
    main()
