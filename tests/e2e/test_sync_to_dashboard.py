"""E2E tests: full pipeline from simulated Plaid sync to dashboard queries."""
import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock

from src.db.connection import get_connection
from src.db.models import Account, Transaction
from src.db.repository import TransactionRepository
from src.db.schema import initialize_db
from src.sync.transaction_sync import TransactionSyncer

pytestmark = pytest.mark.e2e


def make_plaid_transaction(tx_id: str, amount: float, category: str, date: str) -> Transaction:
    now = datetime.now(timezone.utc).isoformat()
    return Transaction(
        id=None,
        account_id=0,
        plaid_transaction_id=tx_id,
        date=date,
        name=f"Merchant for {tx_id}",
        merchant_name=f"Merchant {tx_id}",
        amount=amount,
        category=category,
        subcategory=f"{category}_DETAIL",
        pending=False,
        created_at=now,
    )


@pytest.fixture
def pipeline():
    """Full pipeline: real in-memory DB + mocked Plaid service."""
    with get_connection(":memory:") as conn:
        initialize_db(conn)
        repo = TransactionRepository(conn)

        plaid_service = MagicMock()
        syncer = TransactionSyncer(plaid_service=plaid_service, repository=repo)

        yield repo, plaid_service, syncer


class TestSyncToDashboardPipeline:
    def test_synced_transactions_appear_in_category_query(self, pipeline):
        repo, plaid_service, syncer = pipeline

        account = repo.upsert_account(Account(
            id=None,
            plaid_item_id="item_001",
            plaid_access_token="access-sandbox-abc",
            institution_name="Capital One",
            account_name="Venture X",
            account_type="credit",
            created_at="2024-01-01T00:00:00",
        ))

        added = [
            make_plaid_transaction("txn_001", 50.0, "FOOD_AND_DRINK", "2024-03-01"),
            make_plaid_transaction("txn_002", 120.0, "TRAVEL", "2024-03-10"),
            make_plaid_transaction("txn_003", 30.0, "FOOD_AND_DRINK", "2024-03-15"),
        ]
        plaid_service.sync_transactions.return_value = (added, [], [], "cursor_v1")
        plaid_service.sync_transactions.__name__ = "sync_transactions"

        result = syncer.sync_account(account)
        assert result.added == 3
        assert result.errors == []

        cat_data = repo.get_spending_by_category("2024-03-01", "2024-03-31", [account.id])
        categories = {r["category"]: r["total"] for r in cat_data}
        assert categories["FOOD_AND_DRINK"] == pytest.approx(80.0)
        assert categories["TRAVEL"] == pytest.approx(120.0)

    def test_incremental_sync_adds_only_new_transactions(self, pipeline):
        repo, plaid_service, syncer = pipeline

        account = repo.upsert_account(Account(
            id=None,
            plaid_item_id="item_001",
            plaid_access_token="access-sandbox-abc",
            institution_name="Capital One",
            account_name="Venture X",
            account_type="credit",
            created_at="2024-01-01T00:00:00",
        ))

        # First sync
        plaid_service.sync_transactions.return_value = (
            [make_plaid_transaction("txn_001", 50.0, "FOOD_AND_DRINK", "2024-03-01")],
            [], [], "cursor_v1",
        )
        syncer.sync_account(account)

        # Second sync (cursor-based, one new transaction)
        plaid_service.sync_transactions.return_value = (
            [make_plaid_transaction("txn_002", 75.0, "SHOPPING", "2024-03-20")],
            [], [], "cursor_v2",
        )
        result2 = syncer.sync_account(account)

        # Cursor was passed from first sync
        call_args = plaid_service.sync_transactions.call_args_list[1][1]
        assert call_args["cursor"] == "cursor_v1"

        all_txs = repo.get_transactions({})
        assert len(all_txs) == 2
        assert result2.added == 1

    def test_deletion_removes_transaction_from_queries(self, pipeline):
        repo, plaid_service, syncer = pipeline

        account = repo.upsert_account(Account(
            id=None,
            plaid_item_id="item_001",
            plaid_access_token="access-sandbox-abc",
            institution_name="Capital One",
            account_name="Venture X",
            account_type="credit",
            created_at="2024-01-01T00:00:00",
        ))

        plaid_service.sync_transactions.return_value = (
            [
                make_plaid_transaction("txn_keep", 50.0, "FOOD_AND_DRINK", "2024-03-01"),
                make_plaid_transaction("txn_delete", 200.0, "SHOPPING", "2024-03-05"),
            ],
            [], [], "cursor_v1",
        )
        syncer.sync_account(account)
        assert len(repo.get_transactions({})) == 2

        # Second sync removes one
        plaid_service.sync_transactions.return_value = ([], [], ["txn_delete"], "cursor_v2")
        syncer.sync_account(account)

        remaining = repo.get_transactions({})
        assert len(remaining) == 1
        assert remaining[0].plaid_transaction_id == "txn_keep"

    def test_monthly_totals_reflect_synced_data(self, pipeline):
        repo, plaid_service, syncer = pipeline

        account = repo.upsert_account(Account(
            id=None,
            plaid_item_id="item_001",
            plaid_access_token="access-sandbox-abc",
            institution_name="Capital One",
            account_name="Venture X",
            account_type="credit",
            created_at="2024-01-01T00:00:00",
        ))

        plaid_service.sync_transactions.return_value = (
            [
                make_plaid_transaction("txn_feb", 100.0, "FOOD_AND_DRINK", "2024-02-15"),
                make_plaid_transaction("txn_mar1", 200.0, "TRAVEL", "2024-03-01"),
                make_plaid_transaction("txn_mar2", 150.0, "SHOPPING", "2024-03-20"),
            ],
            [], [], "cursor_v1",
        )
        syncer.sync_account(account)

        monthly = repo.get_monthly_totals([account.id])
        by_month = {r["month"]: r["total"] for r in monthly}
        assert by_month["2024-02"] == pytest.approx(100.0)
        assert by_month["2024-03"] == pytest.approx(350.0)
