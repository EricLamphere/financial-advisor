"""Tests for configuration loading and validation."""
import os
import pytest


def _load_config(env_vars: dict):
    """Helper: set env vars, import config fresh, return Config."""
    # Patch os.environ and force module reload
    import importlib
    import sys

    for key, value in env_vars.items():
        os.environ[key] = value

    # Remove cached module so we get a fresh load
    if "src.config" in sys.modules:
        del sys.modules["src.config"]

    from src.config import Config, load_config
    return load_config()


def _clear_env(*keys):
    for key in keys:
        os.environ.pop(key, None)


REQUIRED_VARS = {
    "PLAID_CLIENT_ID": "test_client_id",
    "PLAID_SECRET": "test_secret",
}

FULL_VARS = {
    **REQUIRED_VARS,
    "PLAID_ENV": "sandbox",
    "DATABASE_PATH": "./test.db",
    "PLAID_PRODUCTS": "transactions",
    "PLAID_COUNTRY_CODES": "US",
    "LINK_SERVER_PORT": "5001",
}


@pytest.fixture(autouse=True)
def clean_env():
    """Remove any leftover env vars before and after each test."""
    all_keys = list(FULL_VARS.keys())
    _clear_env(*all_keys)
    yield
    _clear_env(*all_keys)


class TestConfigLoading:
    def test_loads_all_required_vars(self):
        config = _load_config(FULL_VARS)
        assert config.plaid_client_id == "test_client_id"
        assert config.plaid_secret == "test_secret"

    def test_defaults_plaid_env_to_sandbox(self):
        config = _load_config(REQUIRED_VARS)
        assert config.plaid_env == "sandbox"

    def test_defaults_database_path(self):
        config = _load_config(REQUIRED_VARS)
        assert config.database_path == "./db/financial_advisor.db"

    def test_defaults_link_server_port(self):
        config = _load_config(REQUIRED_VARS)
        assert config.link_server_port == 5001

    def test_custom_plaid_env(self):
        config = _load_config({**REQUIRED_VARS, "PLAID_ENV": "production"})
        assert config.plaid_env == "production"

    def test_custom_database_path(self):
        config = _load_config({**REQUIRED_VARS, "DATABASE_PATH": "/tmp/test.db"})
        assert config.database_path == "/tmp/test.db"

    def test_custom_link_server_port(self):
        config = _load_config({**REQUIRED_VARS, "LINK_SERVER_PORT": "8080"})
        assert config.link_server_port == 8080


class TestConfigValidation:
    def test_missing_client_id_raises(self):
        import sys
        if "src.config" in sys.modules:
            del sys.modules["src.config"]
        os.environ["PLAID_SECRET"] = "test_secret"
        with pytest.raises(EnvironmentError, match="PLAID_CLIENT_ID"):
            from src.config import load_config
            load_config()

    def test_missing_secret_raises(self):
        import sys
        if "src.config" in sys.modules:
            del sys.modules["src.config"]
        os.environ["PLAID_CLIENT_ID"] = "test_client_id"
        with pytest.raises(EnvironmentError, match="PLAID_SECRET"):
            from src.config import load_config
            load_config()

    def test_invalid_plaid_env_raises(self):
        with pytest.raises(ValueError, match="PLAID_ENV"):
            _load_config({**REQUIRED_VARS, "PLAID_ENV": "invalid_env"})

    def test_invalid_port_raises(self):
        with pytest.raises(ValueError, match="LINK_SERVER_PORT"):
            _load_config({**REQUIRED_VARS, "LINK_SERVER_PORT": "not_a_number"})


class TestConfigImmutability:
    def test_config_is_frozen(self):
        config = _load_config(REQUIRED_VARS)
        with pytest.raises(Exception):  # FrozenInstanceError or AttributeError
            config.plaid_client_id = "hacked"  # type: ignore
