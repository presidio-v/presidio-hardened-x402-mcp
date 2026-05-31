"""Tests for check_payment_replay tool — fingerprint-based replay detection."""

from __future__ import annotations

import pytest
from presidio_x402 import ReplayGuard

from presidio_x402_mcp import server as srv
from presidio_x402_mcp.server import check_payment_replay


class TestReplay:
    def setup_method(self):
        srv._REPLAY = ReplayGuard(ttl=300)

    @pytest.mark.anyio
    async def test_first_call_not_a_replay(self):
        result = await check_payment_replay(
            resource_url="https://api.example.com/x",
            pay_to="0xabc",
            amount="1.50",
            currency="USDC",
            deadline_seconds=1700000000,
        )
        assert result["is_replay"] is False
        assert isinstance(result["fingerprint"], str)
        assert len(result["fingerprint"]) == 64  # HMAC-SHA256 hex

    @pytest.mark.anyio
    async def test_identical_call_detected_as_replay(self):
        kwargs = {
            "resource_url": "https://api.example.com/x",
            "pay_to": "0xabc",
            "amount": "1.50",
            "currency": "USDC",
            "deadline_seconds": 1700000000,
        }
        first = await check_payment_replay(**kwargs)
        second = await check_payment_replay(**kwargs)
        assert first["is_replay"] is False
        assert second["is_replay"] is True
        assert first["fingerprint"] == second["fingerprint"]

    @pytest.mark.anyio
    async def test_different_amount_yields_different_fingerprint(self):
        r1 = await check_payment_replay(
            resource_url="https://api.example.com/x",
            pay_to="0xabc",
            amount="1.50",
            currency="USDC",
            deadline_seconds=1700000000,
        )
        r2 = await check_payment_replay(
            resource_url="https://api.example.com/x",
            pay_to="0xabc",
            amount="2.50",
            currency="USDC",
            deadline_seconds=1700000000,
        )
        assert r1["fingerprint"] != r2["fingerprint"]
        assert r1["is_replay"] is False
        assert r2["is_replay"] is False

    @pytest.mark.anyio
    async def test_different_recipient_yields_different_fingerprint(self):
        r1 = await check_payment_replay(
            resource_url="https://x.com/x",
            pay_to="0xaaa",
            amount="1.00",
            currency="USDC",
            deadline_seconds=1700000000,
        )
        r2 = await check_payment_replay(
            resource_url="https://x.com/x",
            pay_to="0xbbb",
            amount="1.00",
            currency="USDC",
            deadline_seconds=1700000000,
        )
        assert r1["fingerprint"] != r2["fingerprint"]
        assert r1["is_replay"] is False
        assert r2["is_replay"] is False
