"""The audit log must actually be written, and must never carry raw PII.

CodeQL alert #1 (`py/unused-global-variable`) flagged `_AUDIT` as constructed but
never used. It was a `note`-severity finding, but the consequence was not
cosmetic: `PRESIDIO_X402_MCP_AUDIT_PATH` is documented as a feature, so an
operator could configure an audit trail, see the file created, and receive
nothing in it.
"""

from __future__ import annotations

import json

import pytest

from presidio_x402_mcp import server as srv
from presidio_x402_mcp.server import (
    check_payment_policy,
    check_payment_replay,
    screen_payment_metadata,
)


@pytest.fixture
def captured(monkeypatch):
    """Collect emitted audit events instead of writing them to disk."""
    events: list[dict] = []

    class Recorder:
        def emit(self, event_type, **fields):
            events.append({"event_type": event_type, **fields})
            return None

    monkeypatch.setattr(srv, "_AUDIT", Recorder())
    return events


class TestEventsAreEmitted:
    @pytest.mark.anyio
    async def test_screening_emits_an_event(self, captured):
        await screen_payment_metadata(resource_url="https://api.example.com/v1/data")
        assert len(captured) == 1
        assert captured[0]["outcome"] == "allowed"

    @pytest.mark.anyio
    async def test_screening_records_the_entity_types_found(self, captured):
        await screen_payment_metadata(resource_url="https://x.test/u/alice@example.com")
        (event,) = captured
        assert event["event_type"] == "PII_REDACTED"
        assert "EMAIL_ADDRESS" in event["pii_entities_found"]

    @pytest.mark.anyio
    async def test_policy_allow_and_block_are_both_recorded(self, captured, monkeypatch):
        monkeypatch.setattr(srv._POLICY.config, "max_per_call_usd", 1.0, raising=False)
        await check_payment_policy(resource_url="https://x.test/a", amount_usd=0.01)
        assert captured[-1]["event_type"] == "PAYMENT_ALLOWED"
        result = await check_payment_policy(resource_url="https://x.test/a", amount_usd=10_000.0)
        if not result["allowed"]:
            assert captured[-1]["event_type"] == "POLICY_BLOCKED"
            assert captured[-1]["outcome"] == "blocked"

    @pytest.mark.anyio
    async def test_replay_first_and_duplicate_are_both_recorded(self, captured):
        args = {
            "resource_url": "https://x.test/replay-audit",
            "pay_to": "0xabc",
            "amount": "1.00",
            "currency": "USDC",
            "deadline_seconds": 1_800_000_000,
        }
        first = await check_payment_replay(**args)
        assert first["is_replay"] is False
        assert captured[-1]["event_type"] == "PAYMENT_ALLOWED"
        assert captured[-1]["replay_fingerprint"] == first["fingerprint"]

        second = await check_payment_replay(**args)
        assert second["is_replay"] is True
        assert captured[-1]["event_type"] == "REPLAY_BLOCKED"


class TestAuditNeverCarriesRawPII:
    """The gate tools receive an unscreened URL — auditing it verbatim would put
    the very PII this server exists to catch into a file that outlives the run."""

    PII_URL = "https://x.test/users/alice.martin@example.com/exports"
    ENCODED_URL = "https://x.test/users/alice.martin%40example.com/exports"

    @pytest.mark.anyio
    async def test_policy_audit_url_is_redacted(self, captured):
        await check_payment_policy(resource_url=self.PII_URL, amount_usd=0.01)
        recorded = json.dumps(captured[-1])
        assert "alice.martin@example.com" not in recorded
        assert "<EMAIL_ADDRESS>" in captured[-1]["resource_url"]

    @pytest.mark.anyio
    async def test_replay_audit_url_is_redacted(self, captured):
        await check_payment_replay(
            resource_url=self.PII_URL,
            pay_to="0xabc",
            amount="2.00",
            currency="USDC",
            deadline_seconds=1_800_000_001,
        )
        assert "alice.martin@example.com" not in json.dumps(captured[-1])

    @pytest.mark.anyio
    async def test_percent_encoded_pii_is_also_redacted_in_the_audit_record(self, captured):
        """Relies on the parent >=0.11.1 floor: an earlier parent would write this
        address to the audit log unredacted."""
        await check_payment_policy(resource_url=self.ENCODED_URL, amount_usd=0.01)
        assert "alice.martin" not in json.dumps(captured[-1])

    @pytest.mark.anyio
    async def test_redaction_failure_never_falls_back_to_the_raw_url(self, monkeypatch):
        def boom(*_a, **_k):
            raise RuntimeError("filter exploded")

        monkeypatch.setattr(srv, "PIIFilter", boom)
        assert srv._audit_safe_url(self.PII_URL) == "<REDACTION_FAILED>"
