"""Accounts page — manage linked accounts and trigger syncs."""
from __future__ import annotations

import webbrowser

import streamlit as st

from src.config import Config
from src.db.repository import TransactionRepository
from src.plaid_client import PlaidService
from src.sync.transaction_sync import TransactionSyncer


def render(repo: TransactionRepository, config: Config) -> None:
    st.title("Accounts")

    col1, col2 = st.columns([3, 1])
    with col2:
        if st.button("+ Connect Account", type="primary"):
            url = f"http://localhost:{config.link_server_port}"
            webbrowser.open(url)
            st.info(f"Opened Plaid Link in your browser ({url}).\nAfter connecting, click **Sync Now** in the sidebar.")

    accounts = repo.get_accounts()

    if not accounts:
        st.info("No accounts linked yet. Click **+ Connect Account** to get started.")
        return

    st.subheader(f"{len(accounts)} linked account{'s' if len(accounts) != 1 else ''}")

    plaid_service = PlaidService(config)
    syncer = TransactionSyncer(plaid_service=plaid_service, repository=repo)

    for account in accounts:
        with st.expander(f"{account.institution_name} — {account.account_name}", expanded=True):
            c1, c2, c3 = st.columns([2, 1, 1])
            c1.write(f"**Type:** {account.account_type.title()}")

            last_synced = repo.get_last_synced(account.id)
            c1.write(f"**Last synced:** {last_synced or 'Never'}")

            with c2:
                if st.button("Sync", key=f"sync_{account.id}"):
                    with st.spinner("Syncing..."):
                        result = syncer.sync_account(account)
                    if result.errors:
                        st.error(f"Sync failed: {result.errors[0]}")
                    else:
                        st.success(f"+{result.added} new, {result.modified} updated, {result.removed} removed")

            with c3:
                if st.button("Remove", key=f"remove_{account.id}", type="secondary"):
                    st.session_state[f"confirm_remove_{account.id}"] = True

            if st.session_state.get(f"confirm_remove_{account.id}"):
                st.warning(f"Remove **{account.institution_name}**? This deletes all its transactions.")
                rc1, rc2 = st.columns(2)
                with rc1:
                    if st.button("Yes, remove", key=f"confirm_yes_{account.id}"):
                        # Delete transactions then the account
                        txs = repo.get_transactions({"account_ids": [account.id]})
                        plaid_ids = [tx.plaid_transaction_id for tx in txs]
                        if plaid_ids:
                            repo.delete_transactions(plaid_ids)
                        repo._conn.execute("DELETE FROM sync_cursors WHERE account_id = ?", (account.id,))
                        repo._conn.execute("DELETE FROM accounts WHERE id = ?", (account.id,))
                        repo._conn.commit()
                        st.session_state.pop(f"confirm_remove_{account.id}", None)
                        st.rerun()
                with rc2:
                    if st.button("Cancel", key=f"confirm_no_{account.id}"):
                        st.session_state.pop(f"confirm_remove_{account.id}", None)
                        st.rerun()
