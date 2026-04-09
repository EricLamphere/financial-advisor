"""Net Worth page — account balances, assets vs liabilities, history."""
from __future__ import annotations

from datetime import date

import streamlit as st

from src.dashboard.components.charts import balance_history_chart
from src.dashboard.components.theme import GREEN, RED, TEXT_PRIMARY, metric_tiles
from src.db.repository import TransactionRepository
from src.plaid_client import PlaidError, PlaidService
from src.sync.transaction_sync import TransactionSyncer
from src.config import Config


def render(repo: TransactionRepository, account_ids: list[int], config: Config) -> None:
    if not repo.get_accounts():
        st.info("No accounts linked yet. Go to the **Accounts** tab to connect your first account.")
        return

    if not account_ids:
        st.warning("Select at least one account in the sidebar.")
        return

    col_hdr, col_btn = st.columns([4, 1])
    with col_btn:
        if st.button("↻ Refresh Balances", width="stretch"):
            plaid = PlaidService(config)
            syncer = TransactionSyncer(plaid_service=plaid, repository=repo)
            with st.spinner("Fetching balances…"):
                from dataclasses import replace
                accounts = repo.get_accounts()
                errors = []
                for acct in accounts:
                    if acct.id not in account_ids:
                        continue
                    try:
                        for bal in plaid.get_account_balances(acct.plaid_access_token):
                            repo.upsert_balance(replace(bal, account_id=acct.id))
                    except PlaidError as e:
                        errors.append(str(e))
            if errors:
                st.error(f"Some balances failed: {'; '.join(errors)}")
            else:
                st.success("Balances updated")
            st.rerun()

    latest = repo.get_latest_balances(account_ids)

    if not latest:
        st.info("No balance data yet. Click **↻ Refresh Balances** or sync your accounts.")
        return

    assets = sum(r["current"] or 0 for r in latest if r["account_type"] in ("depository", "investment", "brokerage"))
    liabilities = sum(r["current"] or 0 for r in latest if r["account_type"] in ("credit", "loan"))
    net_worth = assets - liabilities

    metric_tiles([
        {"label": "Net Worth", "value": f"${net_worth:,.2f}", "value_color": GREEN if net_worth >= 0 else RED},
        {"label": "Assets", "value": f"${assets:,.2f}", "value_color": GREEN},
        {"label": "Liabilities", "value": f"${liabilities:,.2f}"},
        {"label": "Accounts", "value": str(len(latest))},
    ])

    # ── Per-account breakdown ─────────────────────────────────────────────────
    st.markdown('<p class="section-header">Account Breakdown</p>', unsafe_allow_html=True)

    for row in sorted(latest, key=lambda r: r["account_type"]):
        current = row["current"] or 0
        available = row["available"]
        limit_amt = row["limit_amt"]
        acct_type = row["account_type"].title()

        with st.container():
            c1, c2, c3, c4 = st.columns([3, 1, 1, 1])
            c1.markdown(
                f"**{row['institution_name']}** — {row['account_name']}  \n"
                f"<span style='font-size:11px;color:#64748b'>{acct_type}</span>",
                unsafe_allow_html=True,
            )
            c2.metric("Balance", f"${current:,.2f}")
            if available is not None:
                c3.metric("Available", f"${available:,.2f}")
            if limit_amt is not None:
                utilization = (current / limit_amt * 100) if limit_amt else 0
                c4.metric("Utilization", f"{utilization:.0f}%")

    st.divider()

    # ── Balance history chart ─────────────────────────────────────────────────
    history = repo.get_balance_history(account_ids)
    st.plotly_chart(balance_history_chart(history), width="stretch", key="net_worth_history")
