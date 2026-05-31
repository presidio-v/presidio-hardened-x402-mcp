"""Tests for check_payment_policy tool — spending policy gate."""

from __future__ import annotations

import pytest
from presidio_x402 import PolicyConfig, PolicyEngine

from presidio_x402_mcp import server as srv
from presidio_x402_mcp.server import check_payment_policy


class TestPolicy:
    def setup_method(self):
        # Fresh engine per test avoids spend-window pollution across tests.
        srv._POLICY = PolicyEngine(PolicyConfig(max_per_call_usd=5.0, daily_limit_usd=10.0))

    @pytest.mark.anyio
    async def test_under_per_call_limit_allowed(self):
        result = await check_payment_policy(resource_url="https://api.foo.com/x", amount_usd=1.00)
        assert result == {"allowed": True}

    @pytest.mark.anyio
    async def test_over_per_call_limit_denied(self):
        result = await check_payment_policy(resource_url="https://api.foo.com/x", amount_usd=6.00)
        assert result["allowed"] is False
        assert result["limit_usd"] == 5.0
        assert result["amount_usd"] == 6.00

    @pytest.mark.anyio
    async def test_daily_limit_denied_after_accumulation(self):
        # Three calls of 4.00 each — first two pass, third pushes total over daily cap of 10.
        a = await check_payment_policy(resource_url="https://api.foo.com/x", amount_usd=4.00)
        b = await check_payment_policy(resource_url="https://api.foo.com/x", amount_usd=4.00)
        c = await check_payment_policy(resource_url="https://api.foo.com/x", amount_usd=4.00)
        assert a == {"allowed": True}
        assert b == {"allowed": True}
        assert c["allowed"] is False
        assert c["limit_usd"] == 10.0

    @pytest.mark.anyio
    async def test_per_endpoint_override_tighter_than_per_call(self):
        srv._POLICY = PolicyEngine(
            PolicyConfig(
                max_per_call_usd=100.0,
                per_endpoint={"https://api.tight.com/x": 1.00},
            )
        )
        loose = await check_payment_policy(
            resource_url="https://api.loose.com/x", amount_usd=50.00
        )
        tight = await check_payment_policy(resource_url="https://api.tight.com/x", amount_usd=2.00)
        assert loose == {"allowed": True}
        assert tight["allowed"] is False
