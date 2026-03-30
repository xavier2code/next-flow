"""Unit test conftest.

Overrides the session-scoped database fixture from the parent conftest
with a no-op version, so unit tests do not require a running database.
"""
import pytest_asyncio


@pytest_asyncio.fixture(scope="session", autouse=True)
async def _setup_database():
    """No-op database setup for unit tests."""
    yield
