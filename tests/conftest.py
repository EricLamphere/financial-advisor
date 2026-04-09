"""Shared fixtures for all tests."""
import pytest
import sqlite3

from src.db.connection import get_connection
from src.db.repository import TransactionRepository
from src.db.schema import initialize_db


@pytest.fixture
def in_memory_conn():
    """Yield a fresh in-memory SQLite connection, initialized with schema."""
    with get_connection(":memory:") as conn:
        initialize_db(conn)
        yield conn


@pytest.fixture
def in_memory_repo(in_memory_conn):
    """Yield a TransactionRepository backed by in-memory SQLite."""
    return TransactionRepository(in_memory_conn)
