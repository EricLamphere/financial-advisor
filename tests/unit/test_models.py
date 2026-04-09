"""Tests for domain model dataclasses."""
import pytest
from datetime import date, datetime
from src.db.models import Account, Transaction


class TestAccountModel:
    def test_creates_account(self):
        account = Account(
            id=1,
            plaid_item_id="item_123",
            plaid_access_token="access-sandbox-abc",
            institution_name="Capital One",
            account_name="Venture X",
            account_type="credit",
            created_at="2024-01-01T00:00:00",
        )
        assert account.id == 1
        assert account.institution_name == "Capital One"

    def test_account_is_frozen(self):
        account = Account(
            id=1,
            plaid_item_id="item_123",
            plaid_access_token="access-sandbox-abc",
            institution_name="Capital One",
            account_name="Venture X",
            account_type="credit",
            created_at="2024-01-01T00:00:00",
        )
        with pytest.raises(Exception):
            account.institution_name = "Hacked"  # type: ignore

    def test_account_equality(self):
        kwargs = dict(
            id=1,
            plaid_item_id="item_123",
            plaid_access_token="access-sandbox-abc",
            institution_name="Capital One",
            account_name="Venture X",
            account_type="credit",
            created_at="2024-01-01T00:00:00",
        )
        assert Account(**kwargs) == Account(**kwargs)

    def test_different_accounts_not_equal(self):
        kwargs = dict(
            id=1,
            plaid_item_id="item_123",
            plaid_access_token="access-sandbox-abc",
            institution_name="Capital One",
            account_name="Venture X",
            account_type="credit",
            created_at="2024-01-01T00:00:00",
        )
        a1 = Account(**kwargs)
        a2 = Account(**{**kwargs, "id": 2})
        assert a1 != a2


class TestTransactionModel:
    def test_creates_transaction(self):
        tx = Transaction(
            id=1,
            account_id=1,
            plaid_transaction_id="txn_abc123",
            date="2024-03-15",
            name="Whole Foods Market",
            merchant_name="Whole Foods",
            amount=87.43,
            category="FOOD_AND_DRINK",
            subcategory="Groceries",
            pending=False,
            created_at="2024-03-15T10:00:00",
        )
        assert tx.plaid_transaction_id == "txn_abc123"
        assert tx.amount == 87.43
        assert tx.pending is False

    def test_transaction_is_frozen(self):
        tx = Transaction(
            id=1,
            account_id=1,
            plaid_transaction_id="txn_abc123",
            date="2024-03-15",
            name="Whole Foods Market",
            merchant_name="Whole Foods",
            amount=87.43,
            category="FOOD_AND_DRINK",
            subcategory="Groceries",
            pending=False,
            created_at="2024-03-15T10:00:00",
        )
        with pytest.raises(Exception):
            tx.amount = 999.99  # type: ignore

    def test_transaction_nullable_fields(self):
        tx = Transaction(
            id=None,
            account_id=1,
            plaid_transaction_id="txn_abc123",
            date="2024-03-15",
            name="Unknown Merchant",
            merchant_name=None,
            amount=12.00,
            category=None,
            subcategory=None,
            pending=True,
            created_at="2024-03-15T10:00:00",
        )
        assert tx.merchant_name is None
        assert tx.category is None
        assert tx.id is None
