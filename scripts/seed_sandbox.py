"""Seed sandbox data for development without running the Plaid Link UI flow.

Creates sandbox access tokens for two test institutions and stores them in the DB,
then triggers an initial transaction sync.

Usage:
    python scripts/seed_sandbox.py
"""
from __future__ import annotations

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from datetime import datetime, timezone

import plaid
from plaid.api import plaid_api
from plaid.model.sandbox_public_token_create_request import SandboxPublicTokenCreateRequest
from plaid.model.products import Products

from src.config import load_config
from src.db.connection import get_connection
from src.db.models import Account
from src.db.repository import TransactionRepository
from src.db.schema import initialize_db
from src.plaid_client import PlaidService
from src.sync.transaction_sync import TransactionSyncer

# Plaid sandbox institution IDs
SANDBOX_INSTITUTIONS = [
    {"institution_id": "ins_109508", "name": "Chase", "account_name": "Checking"},
    {"institution_id": "ins_109512", "name": "Bank of America", "account_name": "Credit Card"},
]


def seed():
    config = load_config()

    if config.plaid_env != "sandbox":
        print("ERROR: This script only works in sandbox mode.")
        sys.exit(1)

    plaid_config = plaid.Configuration(
        host=plaid.Environment.Sandbox,
        api_key={
            "clientId": config.plaid_client_id,
            "secret": config.plaid_secret,
        },
    )
    api_client = plaid.ApiClient(plaid_config)
    api = plaid_api.PlaidApi(api_client)

    plaid_service = PlaidService(config)

    with get_connection(config.database_path) as conn:
        initialize_db(conn)
        repo = TransactionRepository(conn)
        syncer = TransactionSyncer(plaid_service=plaid_service, repository=repo)

        for inst in SANDBOX_INSTITUTIONS:
            print(f"Creating sandbox token for {inst['name']}...")
            try:
                request = SandboxPublicTokenCreateRequest(
                    institution_id=inst["institution_id"],
                    initial_products=[Products("transactions")],
                )
                response = api.sandbox_public_token_create(request)
                public_token = response.public_token

                access_token, item_id = plaid_service.exchange_public_token(public_token)

                now = datetime.now(timezone.utc).isoformat()
                account = Account(
                    id=None,
                    plaid_item_id=item_id,
                    plaid_access_token=access_token,
                    institution_name=inst["name"],
                    account_name=inst["account_name"],
                    account_type="credit",
                    created_at=now,
                )
                saved = repo.upsert_account(account)
                print(f"  Linked account: {saved.institution_name} (id={saved.id})")

                result = syncer.sync_account(saved)
                print(f"  Synced: +{result.added} transactions, errors={result.errors}")

            except Exception as exc:
                print(f"  ERROR for {inst['name']}: {exc}")

    print("\nDone! Start the dashboard with:")
    print("  streamlit run src/dashboard/app.py")


if __name__ == "__main__":
    seed()
