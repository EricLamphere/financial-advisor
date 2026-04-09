"""Tests for TransactionRepository using in-memory SQLite."""
import pytest
from datetime import datetime, timezone

from src.db.connection import get_connection
from src.db.models import Account, Transaction
from src.db.repository import TransactionRepository
from src.db.schema import initialize_db


@pytest.fixture
def repo():
    """Provide a fresh in-memory repository for each test."""
    with get_connection(":memory:") as conn:
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
        name="Whole Foods Market",
        merchant_name="Whole Foods",
        amount=87.43,
        category="FOOD_AND_DRINK",
        subcategory="Groceries",
        pending=False,
        created_at="2024-03-15T10:00:00",
    )
    return Transaction(**{**defaults, **overrides})


class TestAccountOperations:
    def test_upsert_account_creates_new(self, repo):
        account = make_account()
        saved = repo.upsert_account(account)
        assert saved.id is not None
        assert saved.institution_name == "Capital One"

    def test_upsert_account_is_idempotent(self, repo):
        account = make_account()
        first = repo.upsert_account(account)
        second = repo.upsert_account(account)
        assert first.id == second.id

    def test_upsert_account_updates_existing(self, repo):
        account = make_account()
        saved = repo.upsert_account(account)
        updated = make_account(
            plaid_item_id="item_001",
            account_name="Updated Name",
        )
        result = repo.upsert_account(updated)
        assert result.id == saved.id
        assert result.account_name == "Updated Name"

    def test_get_accounts_empty(self, repo):
        assert repo.get_accounts() == []

    def test_get_accounts_returns_all(self, repo):
        repo.upsert_account(make_account(plaid_item_id="item_001"))
        repo.upsert_account(make_account(plaid_item_id="item_002"))
        accounts = repo.get_accounts()
        assert len(accounts) == 2


class TestTransactionOperations:
    def test_upsert_transactions_creates_new(self, repo):
        account = repo.upsert_account(make_account())
        tx = make_transaction(account.id)
        count = repo.upsert_transactions([tx])
        assert count == 1

    def test_upsert_transactions_is_idempotent(self, repo):
        account = repo.upsert_account(make_account())
        tx = make_transaction(account.id)
        repo.upsert_transactions([tx])
        count = repo.upsert_transactions([tx])
        assert count == 1  # replaced, not doubled

        txs = repo.get_transactions({})
        assert len(txs) == 1

    def test_upsert_multiple_transactions(self, repo):
        account = repo.upsert_account(make_account())
        txs = [
            make_transaction(account.id, plaid_transaction_id=f"txn_{i}", amount=float(i * 10))
            for i in range(5)
        ]
        count = repo.upsert_transactions(txs)
        assert count == 5

    def test_get_transactions_empty(self, repo):
        assert repo.get_transactions({}) == []

    def test_get_transactions_with_date_filter(self, repo):
        account = repo.upsert_account(make_account())
        repo.upsert_transactions([
            make_transaction(account.id, plaid_transaction_id="txn_jan", date="2024-01-15", amount=10.0),
            make_transaction(account.id, plaid_transaction_id="txn_mar", date="2024-03-15", amount=20.0),
        ])
        results = repo.get_transactions({"start_date": "2024-02-01", "end_date": "2024-12-31"})
        assert len(results) == 1
        assert results[0].date == "2024-03-15"

    def test_get_transactions_with_account_filter(self, repo):
        acct1 = repo.upsert_account(make_account(plaid_item_id="item_001"))
        acct2 = repo.upsert_account(make_account(plaid_item_id="item_002"))
        repo.upsert_transactions([make_transaction(acct1.id, plaid_transaction_id="txn_1")])
        repo.upsert_transactions([make_transaction(acct2.id, plaid_transaction_id="txn_2")])

        results = repo.get_transactions({"account_ids": [acct1.id]})
        assert len(results) == 1
        assert results[0].account_id == acct1.id

    def test_delete_transactions_by_plaid_id(self, repo):
        account = repo.upsert_account(make_account())
        repo.upsert_transactions([
            make_transaction(account.id, plaid_transaction_id="txn_keep"),
            make_transaction(account.id, plaid_transaction_id="txn_delete"),
        ])
        repo.delete_transactions(["txn_delete"])
        remaining = repo.get_transactions({})
        assert len(remaining) == 1
        assert remaining[0].plaid_transaction_id == "txn_keep"


class TestAggregationQueries:
    @pytest.fixture
    def seeded_repo(self, repo):
        """Repo with two accounts and several transactions."""
        acct1 = repo.upsert_account(make_account(plaid_item_id="item_001", institution_name="Capital One"))
        acct2 = repo.upsert_account(make_account(plaid_item_id="item_002", institution_name="Fidelity"))
        repo.upsert_transactions([
            make_transaction(acct1.id, plaid_transaction_id="t1", date="2024-03-01", amount=50.0, category="FOOD_AND_DRINK", merchant_name="Chipotle"),
            make_transaction(acct1.id, plaid_transaction_id="t2", date="2024-03-10", amount=120.0, category="TRAVEL", merchant_name="Delta"),
            make_transaction(acct1.id, plaid_transaction_id="t3", date="2024-03-15", amount=30.0, category="FOOD_AND_DRINK", merchant_name="Chipotle"),
            make_transaction(acct2.id, plaid_transaction_id="t4", date="2024-03-20", amount=200.0, category="SHOPPING", merchant_name="Amazon"),
            make_transaction(acct1.id, plaid_transaction_id="t5", date="2024-02-15", amount=75.0, category="FOOD_AND_DRINK", merchant_name="Chipotle"),
        ])
        return repo, acct1.id, acct2.id

    def test_spending_by_category(self, seeded_repo):
        repo, acct1_id, acct2_id = seeded_repo
        results = repo.get_spending_by_category("2024-03-01", "2024-03-31", [acct1_id, acct2_id])
        categories = {r["category"]: r["total"] for r in results}
        assert categories["FOOD_AND_DRINK"] == pytest.approx(80.0)
        assert categories["TRAVEL"] == pytest.approx(120.0)
        assert categories["SHOPPING"] == pytest.approx(200.0)

    def test_spending_by_category_filters_by_account(self, seeded_repo):
        repo, acct1_id, acct2_id = seeded_repo
        results = repo.get_spending_by_category("2024-03-01", "2024-03-31", [acct1_id])
        categories = {r["category"]: r["total"] for r in results}
        assert "SHOPPING" not in categories  # acct2 only

    def test_spending_by_merchant(self, seeded_repo):
        repo, acct1_id, acct2_id = seeded_repo
        results = repo.get_spending_by_merchant("2024-03-01", "2024-03-31", [acct1_id, acct2_id])
        merchants = {r["merchant_name"]: r["total"] for r in results}
        assert merchants["Chipotle"] == pytest.approx(80.0)
        assert merchants["Amazon"] == pytest.approx(200.0)

    def test_spending_over_time_monthly(self, seeded_repo):
        repo, acct1_id, acct2_id = seeded_repo
        results = repo.get_spending_over_time("2024-01-01", "2024-12-31", [acct1_id, acct2_id], "month")
        periods = {r["period"]: r["total"] for r in results}
        assert periods["2024-02"] == pytest.approx(75.0)
        assert periods["2024-03"] == pytest.approx(400.0)

    def test_monthly_totals(self, seeded_repo):
        repo, acct1_id, _ = seeded_repo
        results = repo.get_monthly_totals([acct1_id])
        periods = {r["month"]: r["total"] for r in results}
        assert "2024-03" in periods
        assert "2024-02" in periods


class TestSyncCursor:
    def test_get_cursor_returns_none_when_absent(self, repo):
        account = repo.upsert_account(make_account())
        assert repo.get_sync_cursor(account.id) is None

    def test_update_and_get_cursor(self, repo):
        account = repo.upsert_account(make_account())
        repo.update_sync_cursor(account.id, "cursor_abc123", "2024-03-15T10:00:00")
        assert repo.get_sync_cursor(account.id) == "cursor_abc123"

    def test_update_cursor_replaces_existing(self, repo):
        account = repo.upsert_account(make_account())
        repo.update_sync_cursor(account.id, "cursor_v1", "2024-03-14T00:00:00")
        repo.update_sync_cursor(account.id, "cursor_v2", "2024-03-15T00:00:00")
        assert repo.get_sync_cursor(account.id) == "cursor_v2"
