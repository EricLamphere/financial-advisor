"""Integration tests for database operations using a temp file-based SQLite DB."""
import os
import pytest
import tempfile

from src.db.connection import get_connection
from src.db.models import Account, Transaction
from src.db.repository import TransactionRepository
from src.db.schema import initialize_db

pytestmark = pytest.mark.integration


@pytest.fixture
def file_repo(tmp_path):
    """Repository backed by a real file-based SQLite database."""
    db_path = str(tmp_path / "test.db")
    with get_connection(db_path) as conn:
        initialize_db(conn)
        yield TransactionRepository(conn)


def make_account(**overrides) -> Account:
    defaults = dict(
        id=None,
        plaid_item_id="item_001",
        plaid_access_token="access-sandbox-abc",
        institution_name="Capital One",
        account_name="Venture X",
        account_type="credit",
        created_at="2024-01-01T00:00:00",
    )
    return Account(**{**defaults, **overrides})


def make_transaction(account_id: int, **overrides) -> Transaction:
    defaults = dict(
        id=None,
        account_id=account_id,
        plaid_transaction_id="txn_001",
        date="2024-03-15",
        name="Whole Foods",
        merchant_name="Whole Foods",
        amount=50.0,
        category="FOOD_AND_DRINK",
        subcategory="FOOD_AND_DRINK_GROCERIES",
        pending=False,
        created_at="2024-03-15T10:00:00",
    )
    return Transaction(**{**defaults, **overrides})


class TestFileDatabaseOperations:
    def test_full_account_transaction_cycle(self, file_repo):
        """Test creating account, inserting transactions, and querying."""
        account = file_repo.upsert_account(make_account())
        assert account.id is not None

        txs = [
            make_transaction(account.id, plaid_transaction_id=f"txn_{i}", amount=float(i * 10))
            for i in range(1, 6)
        ]
        count = file_repo.upsert_transactions(txs)
        assert count == 5

        all_txs = file_repo.get_transactions({})
        assert len(all_txs) == 5

    def test_cursor_persists_across_operations(self, file_repo):
        """Test that sync cursors survive commit/query cycles."""
        account = file_repo.upsert_account(make_account())
        file_repo.update_sync_cursor(account.id, "cursor_abc", "2024-03-15T00:00:00")
        retrieved = file_repo.get_sync_cursor(account.id)
        assert retrieved == "cursor_abc"

    def test_aggregations_on_real_data(self, file_repo):
        """Test aggregation queries return correct results."""
        acct = file_repo.upsert_account(make_account())
        file_repo.upsert_transactions([
            make_transaction(acct.id, plaid_transaction_id="t1", amount=100.0, category="FOOD_AND_DRINK"),
            make_transaction(acct.id, plaid_transaction_id="t2", amount=200.0, category="TRAVEL"),
            make_transaction(acct.id, plaid_transaction_id="t3", amount=50.0, category="FOOD_AND_DRINK"),
        ])
        results = file_repo.get_spending_by_category("2024-01-01", "2024-12-31", [acct.id])
        categories = {r["category"]: r["total"] for r in results}
        assert categories["FOOD_AND_DRINK"] == pytest.approx(150.0)
        assert categories["TRAVEL"] == pytest.approx(200.0)

    def test_upsert_idempotency_on_file_db(self, file_repo):
        """Test that repeated upserts don't create duplicates."""
        acct = file_repo.upsert_account(make_account())
        tx = make_transaction(acct.id)
        file_repo.upsert_transactions([tx])
        file_repo.upsert_transactions([tx])
        file_repo.upsert_transactions([tx])
        all_txs = file_repo.get_transactions({})
        assert len(all_txs) == 1
