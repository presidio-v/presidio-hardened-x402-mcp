"""Pytest configuration for presidio-hardened-x402-mcp tests.

The MCP Python SDK uses anyio internally; tests use `@pytest.mark.anyio`
and this fixture pins the backend to asyncio.
"""

import pytest


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"
