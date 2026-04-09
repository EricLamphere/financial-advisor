"""Plaid API wrapper — link tokens, token exchange, and transaction sync."""
from __future__ import annotations

from datetime import datetime, timezone

import plaid
from plaid.api import plaid_api
from plaid.model.link_token_create_request import LinkTokenCreateRequest
from plaid.model.link_token_create_request_user import LinkTokenCreateRequestUser
from plaid.model.item_public_token_exchange_request import ItemPublicTokenExchangeRequest
from plaid.model.transactions_sync_request import TransactionsSyncRequest
from plaid.model.country_code import CountryCode
from plaid.model.products import Products

from src.config import Config
from src.db.models import Transaction

_PLAID_ENV_MAP = {
    "sandbox": plaid.Environment.Sandbox,
    "development": plaid.Environment.Sandbox,  # v39+ removed Development tier
    "production": plaid.Environment.Production,
}


class PlaidError(Exception):
    """Raised when a Plaid API call fails."""


class PlaidService:
    def __init__(self, config: Config) -> None:
        plaid_config = plaid.Configuration(
            host=_PLAID_ENV_MAP[config.plaid_env],
            api_key={
                "clientId": config.plaid_client_id,
                "secret": config.plaid_secret,
            },
        )
        api_client = plaid.ApiClient(plaid_config)
        self._api = plaid_api.PlaidApi(api_client)
        self._config = config

    def create_link_token(self, user_id: str) -> str:
        """Create a Plaid Link token to initialize the Link flow."""
        try:
            request = LinkTokenCreateRequest(
                user=LinkTokenCreateRequestUser(client_user_id=user_id),
                client_name="Financial Advisor",
                products=[Products("transactions")],
                country_codes=[CountryCode("US")],
                language="en",
            )
            response = self._api.link_token_create(request)
            return response.link_token
        except Exception as exc:
            raise PlaidError(f"Failed to create link token: {exc}") from exc

    def exchange_public_token(self, public_token: str) -> tuple[str, str]:
        """Exchange a public token from Link for a permanent access token.

        Returns (access_token, item_id).
        """
        try:
            request = ItemPublicTokenExchangeRequest(public_token=public_token)
            response = self._api.item_public_token_exchange(request)
            return response.access_token, response.item_id
        except Exception as exc:
            raise PlaidError(f"Failed to exchange public token: {exc}") from exc

    def sync_transactions(
        self,
        access_token: str,
        cursor: str | None = None,
    ) -> tuple[list[Transaction], list[Transaction], list[str], str]:
        """Fetch new, modified, and deleted transactions since the last cursor.

        Handles pagination automatically.

        Returns (added, modified, removed_ids, next_cursor).
        """
        all_added: list[Transaction] = []
        all_modified: list[Transaction] = []
        all_removed: list[str] = []
        next_cursor = cursor or ""
        has_more = True

        try:
            while has_more:
                kwargs = {"access_token": access_token}
                if next_cursor:
                    kwargs["cursor"] = next_cursor

                request = TransactionsSyncRequest(**kwargs)
                response = self._api.transactions_sync(request)

                all_added.extend(_plaid_tx_to_model(tx) for tx in response.added)
                all_modified.extend(_plaid_tx_to_model(tx) for tx in response.modified)
                all_removed.extend(tx.transaction_id for tx in response.removed)
                next_cursor = response.next_cursor
                has_more = response.has_more

        except PlaidError:
            raise
        except Exception as exc:
            raise PlaidError(f"Failed to sync transactions: {exc}") from exc

        return all_added, all_modified, all_removed, next_cursor


def _plaid_tx_to_model(tx) -> Transaction:
    """Convert a Plaid transaction object to our domain Transaction."""
    now = datetime.now(timezone.utc).isoformat()

    category = None
    subcategory = None
    if hasattr(tx, "personal_finance_category") and tx.personal_finance_category:
        category = tx.personal_finance_category.primary
        subcategory = tx.personal_finance_category.detailed

    return Transaction(
        id=None,
        account_id=0,  # Will be set by the sync engine when persisting
        plaid_transaction_id=tx.transaction_id,
        date=tx.date.isoformat() if hasattr(tx.date, "isoformat") else str(tx.date),
        name=tx.name,
        merchant_name=tx.merchant_name if tx.merchant_name else None,
        amount=tx.amount,
        category=category,
        subcategory=subcategory,
        pending=tx.pending,
        created_at=now,
    )
