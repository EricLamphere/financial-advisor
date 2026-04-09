"""Configuration loading and validation from environment variables."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

_VALID_PLAID_ENVS = {"sandbox", "development", "production"}


@dataclass(frozen=True)
class Config:
    plaid_client_id: str
    plaid_secret: str
    plaid_env: str
    plaid_products: str
    plaid_country_codes: str
    database_path: str
    link_server_port: int


def load_config(env_file: str | None = None) -> Config:
    """Load and validate configuration from environment variables.

    Loads a .env file if present (does not override existing env vars).
    Raises EnvironmentError for missing required vars.
    Raises ValueError for invalid values.
    """
    if env_file:
        load_dotenv(env_file, override=False)
    else:
        load_dotenv(override=False)

    # Required variables — fail fast with clear messages
    client_id = os.environ.get("PLAID_CLIENT_ID")
    if not client_id:
        raise EnvironmentError(
            "PLAID_CLIENT_ID is required. Set it in your .env file or environment."
        )

    secret = os.environ.get("PLAID_SECRET")
    if not secret:
        raise EnvironmentError(
            "PLAID_SECRET is required. Set it in your .env file or environment."
        )

    # Optional variables with defaults
    plaid_env = os.environ.get("PLAID_ENV", "sandbox")
    if plaid_env not in _VALID_PLAID_ENVS:
        raise ValueError(
            f"PLAID_ENV must be one of {sorted(_VALID_PLAID_ENVS)}, got: {plaid_env!r}"
        )

    database_path = os.environ.get("DATABASE_PATH", "./db/financial_advisor.db")
    plaid_products = os.environ.get("PLAID_PRODUCTS", "transactions")
    plaid_country_codes = os.environ.get("PLAID_COUNTRY_CODES", "US")

    raw_port = os.environ.get("LINK_SERVER_PORT", "5001")
    try:
        link_server_port = int(raw_port)
    except ValueError:
        raise ValueError(
            f"LINK_SERVER_PORT must be an integer, got: {raw_port!r}"
        )

    return Config(
        plaid_client_id=client_id,
        plaid_secret=secret,
        plaid_env=plaid_env,
        plaid_products=plaid_products,
        plaid_country_codes=plaid_country_codes,
        database_path=database_path,
        link_server_port=link_server_port,
    )
