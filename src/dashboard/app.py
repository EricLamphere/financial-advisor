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

from src.dashboard.views import overview, categories, merchants, timeline, accounts as accounts_page


@st.cache_resource
def get_config():
    return load_config()


def get_repo(config) -> tuple[TransactionRepository, object]:
    """Return a repository and its underlying connection.

    Opens a fresh connection on each Streamlit run so that accounts linked
    via the Flask server (a separate process) are immediately visible.
    """
    import sqlite3
    conn = sqlite3.connect(config.database_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    initialize_db(conn)
    return TransactionRepository(conn), conn


def main():
    try:
        config = get_config()
    except EnvironmentError as exc:
        st.error(f"**Configuration error:** {exc}\n\nCopy `.env.example` to `.env` and fill in your Plaid credentials.")
        st.stop()

    repo, _conn = get_repo(config)
    accounts = repo.get_accounts()

    # --- Sidebar ---
    with st.sidebar:
        st.title("💳 Financial Dashboard")
        st.divider()

        page = st.radio(
            "Navigate",
            options=["Overview", "Categories", "Merchants", "Timeline", "Accounts"],
            label_visibility="collapsed",
        )

        st.divider()
        st.subheader("Filters")

        # Account filter
        account_options = {f"{a.institution_name} — {a.account_name}": a.id for a in accounts}
        selected_labels = st.multiselect(
            "Accounts",
            options=list(account_options.keys()),
            default=list(account_options.keys()),
            key="global_accounts",
        )
        account_ids = [account_options[label] for label in selected_labels]

        # Date range filter
        today = date.today()
        start = st.date_input("From", value=today - timedelta(days=30), key="global_start")
        end = st.date_input("To", value=today, key="global_end")

        st.divider()
        if st.button("🔄 Sync All Accounts", width="stretch"):
            plaid_service = PlaidService(config)
            syncer = TransactionSyncer(plaid_service=plaid_service, repository=repo)
            with st.spinner("Syncing all accounts..."):
                results = syncer.sync_all_accounts()
            if not results:
                st.info("No accounts linked yet.")
            else:
                total_added = sum(r.added for r in results)
                errors = [e for r in results for e in r.errors]
                if errors:
                    st.error(f"Errors: {'; '.join(errors)}")
                else:
                    st.success(f"Synced! +{total_added} new transactions")

    # --- Page routing ---
    if page == "Overview":
        overview.render(repo, account_ids, start, end)
    elif page == "Categories":
        categories.render(repo, account_ids, start, end)
    elif page == "Merchants":
        merchants.render(repo, account_ids, start, end)
    elif page == "Timeline":
        timeline.render(repo, account_ids, start, end)
    elif page == "Accounts":
        accounts_page.render(repo, config)


if __name__ == "__main__":
    main()
