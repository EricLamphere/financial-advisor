"""Transaction sync engine — cursor-based, incremental, idempotent."""
from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone

from src.db.models import Account, SyncResult, Transaction
from src.db.repository import TransactionRepository
from src.plaid_client import PlaidError, PlaidService


class TransactionSyncer:
    def __init__(self, plaid_service: PlaidService, repository: TransactionRepository) -> None:
        self._plaid = plaid_service
        self._repo = repository

    def sync_account(self, account: Account) -> SyncResult:
        """Fetch and persist new/modified/deleted transactions for one account.

        Uses the stored cursor for incremental sync. Saves the updated cursor
        only on success. Returns a SyncResult even if an error occurs.
        """
        cursor = self._repo.get_sync_cursor(account.id)

        try:
            added, modified, removed_ids, next_cursor = self._plaid.sync_transactions(
                account.plaid_access_token, cursor=cursor
            )
        except PlaidError as exc:
            return SyncResult(
                account_id=account.id,
                added=0,
                modified=0,
                removed=0,
                errors=[str(exc)],
            )

        # Stamp account_id onto transactions returned by Plaid (which don't know it)
        added_stamped = [_stamp_account_id(tx, account.id) for tx in added]
        modified_stamped = [_stamp_account_id(tx, account.id) for tx in modified]

        if added_stamped or modified_stamped:
            self._repo.upsert_transactions(added_stamped + modified_stamped)

        if removed_ids:
            self._repo.delete_transactions(removed_ids)

        now = datetime.now(timezone.utc).isoformat()
        self._repo.update_sync_cursor(account.id, next_cursor, now)

        # Snapshot current balance — failure is non-fatal
        try:
            for bal in self._plaid.get_account_balances(account.plaid_access_token):
                self._repo.upsert_balance(replace(bal, account_id=account.id))
        except PlaidError:
            pass

        return SyncResult(
            account_id=account.id,
            added=len(added_stamped),
            modified=len(modified_stamped),
            removed=len(removed_ids),
            errors=[],
        )

    def sync_all_accounts(self) -> list[SyncResult]:
        """Sync all linked accounts. Continues if one account fails."""
        accounts = self._repo.get_accounts()
        return [self.sync_account(account) for account in accounts]


def _stamp_account_id(tx: Transaction, account_id: int) -> Transaction:
    """Return a new Transaction with account_id set."""
    return replace(tx, account_id=account_id)
