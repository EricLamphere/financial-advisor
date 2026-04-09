"""Tests for TransactionSyncer using mocked Plaid and repository."""
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone

from src.db.models import Account, Transaction, SyncResult
from src.sync.transaction_sync import TransactionSyncer


def make_account(account_id: int = 1) -> Account:
    return Account(
        id=account_id,
        plaid_item_id=f"item_{account_id:03d}",
        plaid_access_token=f"access-sandbox-{account_id:03d}",
        institution_name="Capital One",
        account_name="Venture X",
        account_type="credit",
        created_at="2024-01-01T00:00:00",
    )


def make_transaction(tx_id: str = "txn_001", account_id: int = 0) -> Transaction:
    return Transaction(
        id=None,
        account_id=account_id,
        plaid_transaction_id=tx_id,
        date="2024-03-15",
        name="Whole Foods",
        merchant_name="Whole Foods",
        amount=50.0,
        category="FOOD_AND_DRINK",
        subcategory="FOOD_AND_DRINK_GROCERIES",
        pending=False,
        created_at="2024-03-15T10:00:00",
    )


@pytest.fixture
def plaid_service():
    return MagicMock()


@pytest.fixture
def repo():
    return MagicMock()


@pytest.fixture
def syncer(plaid_service, repo):
    return TransactionSyncer(plaid_service=plaid_service, repository=repo)


class TestSyncAccount:
    def test_initial_sync_no_cursor(self, syncer, plaid_service, repo):
        account = make_account()
        repo.get_sync_cursor.return_value = None
        plaid_service.sync_transactions.return_value = (
            [make_transaction("txn_001")],
            [],
            [],
            "cursor_v1",
        )

        result = syncer.sync_account(account)

        plaid_service.sync_transactions.assert_called_once_with(
            account.plaid_access_token, cursor=None
        )
        assert result.added == 1
        assert result.modified == 0
        assert result.removed == 0
        assert result.errors == []

    def test_incremental_sync_uses_existing_cursor(self, syncer, plaid_service, repo):
        account = make_account()
        repo.get_sync_cursor.return_value = "cursor_existing"
        plaid_service.sync_transactions.return_value = ([], [], [], "cursor_v2")

        syncer.sync_account(account)

        plaid_service.sync_transactions.assert_called_once_with(
            account.plaid_access_token, cursor="cursor_existing"
        )

    def test_upserts_added_transactions_with_correct_account_id(self, syncer, plaid_service, repo):
        account = make_account(account_id=42)
        repo.get_sync_cursor.return_value = None
        added = [make_transaction("txn_001", account_id=0)]  # account_id=0 from plaid
        plaid_service.sync_transactions.return_value = (added, [], [], "cursor_v1")

        syncer.sync_account(account)

        call_args = repo.upsert_transactions.call_args[0][0]
        assert all(tx.account_id == 42 for tx in call_args)

    def test_upserts_modified_transactions(self, syncer, plaid_service, repo):
        account = make_account()
        repo.get_sync_cursor.return_value = None
        modified = [make_transaction("txn_002")]
        plaid_service.sync_transactions.return_value = ([], modified, [], "cursor_v1")

        result = syncer.sync_account(account)

        repo.upsert_transactions.assert_called()
        assert result.modified == 1

    def test_deletes_removed_transactions(self, syncer, plaid_service, repo):
        account = make_account()
        repo.get_sync_cursor.return_value = None
        plaid_service.sync_transactions.return_value = ([], [], ["txn_deleted"], "cursor_v1")

        result = syncer.sync_account(account)

        repo.delete_transactions.assert_called_once_with(["txn_deleted"])
        assert result.removed == 1

    def test_saves_cursor_after_sync(self, syncer, plaid_service, repo):
        account = make_account()
        repo.get_sync_cursor.return_value = None
        plaid_service.sync_transactions.return_value = ([], [], [], "cursor_new")

        syncer.sync_account(account)

        repo.update_sync_cursor.assert_called_once()
        call_args = repo.update_sync_cursor.call_args[0]
        assert call_args[0] == account.id
        assert call_args[1] == "cursor_new"

    def test_does_not_save_cursor_on_plaid_error(self, syncer, plaid_service, repo):
        from src.plaid_client import PlaidError
        account = make_account()
        repo.get_sync_cursor.return_value = None
        plaid_service.sync_transactions.side_effect = PlaidError("API down")

        result = syncer.sync_account(account)

        repo.update_sync_cursor.assert_not_called()
        assert len(result.errors) == 1
        assert "API down" in result.errors[0]

    def test_returns_error_on_sync_failure_without_raising(self, syncer, plaid_service, repo):
        from src.plaid_client import PlaidError
        account = make_account()
        repo.get_sync_cursor.return_value = None
        plaid_service.sync_transactions.side_effect = PlaidError("Rate limited")

        result = syncer.sync_account(account)

        assert isinstance(result, SyncResult)
        assert result.added == 0
        assert len(result.errors) > 0


class TestSyncAllAccounts:
    def test_syncs_all_accounts(self, syncer, plaid_service, repo):
        accounts = [make_account(1), make_account(2)]
        repo.get_accounts.return_value = accounts
        repo.get_sync_cursor.return_value = None
        plaid_service.sync_transactions.return_value = ([], [], [], "cursor_v1")

        results = syncer.sync_all_accounts()

        assert len(results) == 2
        assert plaid_service.sync_transactions.call_count == 2

    def test_returns_empty_list_when_no_accounts(self, syncer, repo):
        repo.get_accounts.return_value = []

        results = syncer.sync_all_accounts()

        assert results == []

    def test_continues_on_per_account_error(self, syncer, plaid_service, repo):
        from src.plaid_client import PlaidError
        accounts = [make_account(1), make_account(2)]
        repo.get_accounts.return_value = accounts
        repo.get_sync_cursor.return_value = None
        plaid_service.sync_transactions.side_effect = [
            PlaidError("Account 1 failed"),
            ([], [], [], "cursor_v1"),
        ]

        results = syncer.sync_all_accounts()

        assert len(results) == 2
        assert len(results[0].errors) > 0  # first account errored
        assert results[1].errors == []     # second account succeeded
