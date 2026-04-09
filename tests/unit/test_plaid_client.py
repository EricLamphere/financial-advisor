"""Unit tests for PlaidService using mocked SDK."""
import pytest
from unittest.mock import MagicMock, patch, PropertyMock

from src.config import Config
from src.plaid_client import PlaidService, PlaidError


@pytest.fixture
def config():
    return Config(
        plaid_client_id="test_client_id",
        plaid_secret="test_secret",
        plaid_env="sandbox",
        plaid_products="transactions",
        plaid_country_codes="US",
        database_path=":memory:",
        link_server_port=5001,
    )


@pytest.fixture
def mock_plaid_api():
    """Patch the plaid ApiClient and PlaidApi at import time."""
    with patch("src.plaid_client.plaid.ApiClient") as mock_client_cls, \
         patch("src.plaid_client.plaid_api.PlaidApi") as mock_api_cls:
        mock_client = MagicMock()
        mock_api = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_api_cls.return_value = mock_api
        yield mock_api


class TestPlaidServiceInit:
    def test_creates_service_for_sandbox(self, config):
        with patch("src.plaid_client.plaid.ApiClient"), \
             patch("src.plaid_client.plaid_api.PlaidApi"):
            service = PlaidService(config)
            assert service is not None

    def test_creates_service_for_production(self, config):
        prod_config = Config(
            plaid_client_id="test_client_id",
            plaid_secret="test_secret",
            plaid_env="production",
            plaid_products="transactions",
            plaid_country_codes="US",
            database_path=":memory:",
            link_server_port=5001,
        )
        with patch("src.plaid_client.plaid.ApiClient"), \
             patch("src.plaid_client.plaid_api.PlaidApi"):
            service = PlaidService(prod_config)
            assert service is not None


class TestCreateLinkToken:
    def test_returns_link_token_string(self, config, mock_plaid_api):
        mock_response = MagicMock()
        mock_response.link_token = "link-sandbox-abc123"
        mock_plaid_api.link_token_create.return_value = mock_response

        service = PlaidService(config)
        token = service.create_link_token("user_001")

        assert token == "link-sandbox-abc123"
        mock_plaid_api.link_token_create.assert_called_once()

    def test_raises_plaid_error_on_api_failure(self, config, mock_plaid_api):
        mock_plaid_api.link_token_create.side_effect = Exception("API error")

        service = PlaidService(config)
        with pytest.raises(PlaidError, match="Failed to create link token"):
            service.create_link_token("user_001")


class TestExchangePublicToken:
    def test_returns_access_token_and_item_id(self, config, mock_plaid_api):
        mock_response = MagicMock()
        mock_response.access_token = "access-sandbox-xyz"
        mock_response.item_id = "item_abc"
        mock_plaid_api.item_public_token_exchange.return_value = mock_response

        service = PlaidService(config)
        access_token, item_id = service.exchange_public_token("public-sandbox-token")

        assert access_token == "access-sandbox-xyz"
        assert item_id == "item_abc"

    def test_raises_plaid_error_on_failure(self, config, mock_plaid_api):
        mock_plaid_api.item_public_token_exchange.side_effect = Exception("Exchange failed")

        service = PlaidService(config)
        with pytest.raises(PlaidError, match="Failed to exchange public token"):
            service.exchange_public_token("bad-token")


class TestSyncTransactions:
    def _make_added_tx(self, tx_id="txn_001", amount=50.0, category="FOOD_AND_DRINK"):
        tx = MagicMock()
        tx.transaction_id = tx_id
        tx.date = MagicMock()
        tx.date.isoformat.return_value = "2024-03-15"
        tx.name = "Whole Foods"
        tx.merchant_name = "Whole Foods"
        tx.amount = amount
        tx.pending = False

        # personal_finance_category
        pfc = MagicMock()
        pfc.primary = category
        pfc.detailed = f"{category}_GROCERIES"
        tx.personal_finance_category = pfc
        return tx

    def test_returns_transactions_and_cursor(self, config, mock_plaid_api):
        mock_response = MagicMock()
        mock_response.added = [self._make_added_tx()]
        mock_response.modified = []
        mock_response.removed = []
        mock_response.next_cursor = "cursor_v2"
        mock_response.has_more = False
        mock_plaid_api.transactions_sync.return_value = mock_response

        service = PlaidService(config)
        added, modified, removed, cursor = service.sync_transactions("access-sandbox-abc")

        assert len(added) == 1
        assert added[0].plaid_transaction_id == "txn_001"
        assert added[0].amount == 50.0
        assert cursor == "cursor_v2"

    def test_passes_cursor_on_incremental_sync(self, config, mock_plaid_api):
        mock_response = MagicMock()
        mock_response.added = []
        mock_response.modified = []
        mock_response.removed = []
        mock_response.next_cursor = "cursor_v3"
        mock_response.has_more = False
        mock_plaid_api.transactions_sync.return_value = mock_response

        service = PlaidService(config)
        service.sync_transactions("access-token", cursor="cursor_v2")

        call_args = mock_plaid_api.transactions_sync.call_args
        request = call_args[0][0]
        assert request.cursor == "cursor_v2"

    def test_handles_pagination(self, config, mock_plaid_api):
        page1 = MagicMock()
        page1.added = [self._make_added_tx("txn_001")]
        page1.modified = []
        page1.removed = []
        page1.next_cursor = "cursor_page2"
        page1.has_more = True

        page2 = MagicMock()
        page2.added = [self._make_added_tx("txn_002")]
        page2.modified = []
        page2.removed = []
        page2.next_cursor = "cursor_final"
        page2.has_more = False

        mock_plaid_api.transactions_sync.side_effect = [page1, page2]

        service = PlaidService(config)
        added, modified, removed, cursor = service.sync_transactions("access-token")

        assert len(added) == 2
        assert cursor == "cursor_final"
        assert mock_plaid_api.transactions_sync.call_count == 2

    def test_returns_removed_transaction_ids(self, config, mock_plaid_api):
        removed_tx = MagicMock()
        removed_tx.transaction_id = "txn_deleted"

        mock_response = MagicMock()
        mock_response.added = []
        mock_response.modified = []
        mock_response.removed = [removed_tx]
        mock_response.next_cursor = "cursor_v2"
        mock_response.has_more = False
        mock_plaid_api.transactions_sync.return_value = mock_response

        service = PlaidService(config)
        added, modified, removed, cursor = service.sync_transactions("access-token")

        assert removed == ["txn_deleted"]

    def test_raises_plaid_error_on_failure(self, config, mock_plaid_api):
        mock_plaid_api.transactions_sync.side_effect = Exception("Rate limited")

        service = PlaidService(config)
        with pytest.raises(PlaidError, match="Failed to sync transactions"):
            service.sync_transactions("access-token")
