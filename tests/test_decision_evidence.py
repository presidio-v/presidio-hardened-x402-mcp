"""Gate decisions emit signed payment-decision@1 records next to the audit log.

The HMAC audit log can only be checked by whoever holds the chain key. These
records are what a third party verifies offline, with the parent library's
``verify_decision_ref`` and a pinned trust store — so every test here verifies
through the parent, not through anything this package reimplements.
"""

from __future__ import annotations

import dataclasses
import json
import logging

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from presidio_x402 import (
    NOT_EVALUATED,
    PolicyConfig,
    PolicyEngine,
    ReplayGuard,
    verify_decision_ref,
)
from presidio_x402.exceptions import ConfigurationError

from presidio_x402_mcp import server as srv
from presidio_x402_mcp.server import (
    check_payment_policy,
    check_payment_replay,
    screen_payment_metadata,
)

EVIDENCE_ENV = (
    "PRESIDIO_X402_MCP_EVIDENCE_KEY_FILE",
    "PRESIDIO_X402_EVIDENCE_KEY",
    "PRESIDIO_X402_MCP_DECISION_PATH",
    "PRESIDIO_X402_MCP_EVIDENCE_ALGORITHM",
    "PRESIDIO_X402_MCP_EVIDENCE_SIGNER",
    "PRESIDIO_X402_MCP_EVIDENCE_KEY_ID",
    "PRESIDIO_X402_MCP_REQUIRE_EVIDENCE_KEY",
)
PII_URL = "https://x.test/users/alice.martin@example.com/exports"


def _ed25519_pair() -> tuple[str, str]:
    sk = Ed25519PrivateKey.generate()
    private_hex = sk.private_bytes_raw().hex()
    public_hex = sk.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw).hex()
    return private_hex, public_hex


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    for name in EVIDENCE_ENV:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(srv, "_POLICY", PolicyEngine(PolicyConfig(max_per_call_usd=5.0)))
    monkeypatch.setattr(srv, "_REPLAY", ReplayGuard(ttl=300))
    monkeypatch.setattr(srv, "_EVIDENCE", None)


@pytest.fixture
def signed(tmp_path, monkeypatch):
    """Enable evidence the way an operator would: env vars, then startup."""
    private_hex, public_hex = _ed25519_pair()
    path = tmp_path / "decisions.jsonl"
    monkeypatch.setenv("PRESIDIO_X402_EVIDENCE_KEY", private_hex)
    monkeypatch.setenv("PRESIDIO_X402_MCP_DECISION_PATH", str(path))
    monkeypatch.setattr(srv, "_EVIDENCE", srv._evidence_from_env())
    assert srv._EVIDENCE is not None
    trust = {srv.DEFAULT_EVIDENCE_SIGNER: {"alg": "ed25519", "public_key": public_hex}}

    def records() -> list[dict]:
        if not path.exists():
            return []
        return [json.loads(line) for line in path.read_text().splitlines()]

    return {"trust": trust, "records": records, "path": path, "key": private_hex}


class TestEveryDecisionIsSignedAndVerifies:
    @pytest.mark.anyio
    async def test_screening_record_carries_the_screening_outcome(self, signed):
        result = await screen_payment_metadata(resource_url=PII_URL)
        (env,) = signed["records"]()
        check = verify_decision_ref(env, signed["trust"])
        assert check.ok, check.reason
        assert result["decision_ref"] == env["decision_ref"]
        pii = env["payment_decision"]["controls"]["pii"]
        assert pii == {"verdict": "PII_REDACTED", "entities": ["EMAIL_ADDRESS"], "mutated": True}
        controls = env["payment_decision"]["controls"]
        for key in ("trusted_wallet", "policy", "replay", "mpa"):
            assert controls[key]["verdict"] == NOT_EVALUATED
        assert "policy_snapshot_hash" not in controls["policy"]

    @pytest.mark.anyio
    async def test_policy_allow_and_block_both_emit(self, signed):
        allowed = await check_payment_policy(resource_url="https://x.test/a", amount_usd=1.0)
        blocked = await check_payment_policy(resource_url="https://x.test/a", amount_usd=50.0)
        assert allowed["allowed"] is True and blocked["allowed"] is False
        first, second = signed["records"]()
        for env in (first, second):
            assert verify_decision_ref(env, signed["trust"]).ok
        assert first["payment_decision"]["verdict"] == "ALLOW"
        assert second["payment_decision"]["verdict"] == "DENY"
        controls = second["payment_decision"]["controls"]
        assert controls["policy"]["verdict"] == "VIOLATION"
        assert controls["policy"]["policy_snapshot_hash"].startswith("sha256:")
        for key in ("trusted_wallet", "replay", "mpa"):
            assert controls[key]["verdict"] == NOT_EVALUATED
        assert blocked["decision_ref"] == second["decision_ref"]

    @pytest.mark.anyio
    async def test_replay_fresh_and_duplicate_both_emit(self, signed):
        args = {
            "resource_url": "https://x.test/r",
            "pay_to": "0xabc",
            "amount": "1.00",
            "currency": "USDC",
            "deadline_seconds": 1_800_000_000,
        }
        first = await check_payment_replay(**args)
        second = await check_payment_replay(**args)
        fresh, dup = signed["records"]()
        assert verify_decision_ref(fresh, signed["trust"]).ok
        assert verify_decision_ref(dup, signed["trust"]).ok
        assert fresh["payment_decision"]["controls"]["replay"]["verdict"] == "FRESH"
        assert fresh["payment_decision"]["controls"]["policy"]["verdict"] == NOT_EVALUATED
        assert dup["payment_decision"]["verdict"] == "DENY"
        # Only a hash of the fingerprint enters the record.
        raw = signed["path"].read_text()
        assert first["fingerprint"] not in raw and second["fingerprint"] not in raw
        assert fresh["payment_decision"]["payment"]["pay_to"] == "0xabc"

    @pytest.mark.anyio
    async def test_gate_records_url_pii_as_warned_and_never_raw(self, signed):
        await check_payment_policy(resource_url=PII_URL, amount_usd=1.0)
        (env,) = signed["records"]()
        assert env["payment_decision"]["controls"]["pii"]["verdict"] == "PII_WARNED"
        assert env["payment_decision"]["payment"]["resource_origin"] == "https://x.test"
        assert "alice.martin" not in signed["path"].read_text()

    @pytest.mark.anyio
    async def test_audit_log_is_still_written(self, signed, monkeypatch):
        events: list[str] = []

        class Recorder:
            def emit(self, event_type, **_fields):
                events.append(event_type)

        monkeypatch.setattr(srv, "_AUDIT", Recorder())
        await check_payment_policy(resource_url="https://x.test/a", amount_usd=1.0)
        assert events == ["PAYMENT_ALLOWED"]
        assert len(signed["records"]()) == 1

    @pytest.mark.anyio
    async def test_no_capability_parents(self, signed):
        """The MCP has no capability chain, so ADR-0002 top-level ``parents``
        is never populated."""
        await check_payment_policy(resource_url="https://x.test/a", amount_usd=1.0)
        (env,) = signed["records"]()
        assert "parents" not in env["payment_decision"]
        assert env["payment_decision"]["provenance"]["parents"] == []


class TestPriorDecisionRefs:
    @pytest.mark.anyio
    async def test_screen_ref_links_into_the_gate_record(self, signed):
        screened = await screen_payment_metadata(resource_url="https://x.test/a")
        ref = screened["decision_ref"]
        await check_payment_policy(
            resource_url="https://x.test/a", amount_usd=1.0, prior_decision_refs=[ref]
        )
        _, gate = signed["records"]()
        assert gate["payment_decision"]["provenance"]["prior_decision_refs"] == [ref]
        assert verify_decision_ref(gate, signed["trust"]).ok

    @pytest.mark.anyio
    async def test_unissued_ref_is_refused_before_spend_is_recorded(self, signed):
        with pytest.raises(ValueError, match="did not issue"):
            await check_payment_policy(
                resource_url="https://x.test/a", amount_usd=4.0, prior_decision_refs=["a" * 64]
            )
        # The refused call consumed no budget: a 4.0 payment is still within 5.0.
        ok = await check_payment_policy(resource_url="https://x.test/a", amount_usd=4.0)
        assert ok["allowed"] is True

    @pytest.mark.anyio
    async def test_malformed_ref_is_refused(self):
        with pytest.raises(ValueError, match="lowercase hex"):
            await check_payment_replay(
                resource_url="https://x.test/a",
                pay_to="0xabc",
                amount="1",
                currency="USDC",
                deadline_seconds=1,
                prior_decision_refs=["not-a-ref"],
            )


class TestConfiguration:
    @pytest.mark.anyio
    async def test_no_key_means_no_record_and_one_warning(self, tmp_path, monkeypatch, caplog):
        monkeypatch.setenv("PRESIDIO_X402_MCP_DECISION_PATH", str(tmp_path / "d.jsonl"))
        with caplog.at_level(logging.WARNING, logger="presidio_x402_mcp"):
            cfg = srv._evidence_from_env()
        assert cfg is None
        warnings = [r for r in caplog.records if "DISABLED" in r.getMessage()]
        assert len(warnings) == 1 and warnings[0].levelno == logging.WARNING
        monkeypatch.setattr(srv, "_EVIDENCE", cfg)
        result = await check_payment_policy(resource_url="https://x.test/a", amount_usd=1.0)
        assert result == {"allowed": True}
        assert not (tmp_path / "d.jsonl").exists()

    def test_key_without_path_is_disabled(self, monkeypatch, caplog):
        monkeypatch.setenv("PRESIDIO_X402_EVIDENCE_KEY", _ed25519_pair()[0])
        with caplog.at_level(logging.WARNING, logger="presidio_x402_mcp"):
            assert srv._evidence_from_env() is None
        assert "PRESIDIO_X402_MCP_DECISION_PATH" in caplog.text

    def test_strict_mode_refuses_to_start_without_a_key(self, monkeypatch):
        monkeypatch.setenv("PRESIDIO_X402_MCP_REQUIRE_EVIDENCE_KEY", "1")
        with pytest.raises(ConfigurationError, match="Refusing to start"):
            srv._evidence_from_env()

    def test_strict_mode_refuses_an_invalid_key(self, tmp_path, monkeypatch):
        monkeypatch.setenv("PRESIDIO_X402_MCP_REQUIRE_EVIDENCE_KEY", "true")
        monkeypatch.setenv("PRESIDIO_X402_EVIDENCE_KEY", "zz-not-hex")
        monkeypatch.setenv("PRESIDIO_X402_MCP_DECISION_PATH", str(tmp_path / "d.jsonl"))
        with pytest.raises(ConfigurationError):
            srv._evidence_from_env()

    def test_strict_mode_starts_with_a_working_key(self, tmp_path, monkeypatch):
        monkeypatch.setenv("PRESIDIO_X402_MCP_REQUIRE_EVIDENCE_KEY", "1")
        monkeypatch.setenv("PRESIDIO_X402_EVIDENCE_KEY", _ed25519_pair()[0])
        monkeypatch.setenv("PRESIDIO_X402_MCP_DECISION_PATH", str(tmp_path / "d.jsonl"))
        assert srv._evidence_from_env() is not None

    def test_key_material_never_reaches_logs_or_repr(self, tmp_path, monkeypatch, caplog):
        bad_key = "ab" * 31  # right alphabet, wrong length: rejected at startup
        monkeypatch.setenv("PRESIDIO_X402_EVIDENCE_KEY", bad_key)
        monkeypatch.setenv("PRESIDIO_X402_MCP_DECISION_PATH", str(tmp_path / "d.jsonl"))
        with caplog.at_level(logging.DEBUG, logger="presidio_x402_mcp"):
            assert srv._evidence_from_env() is None
        assert bad_key not in caplog.text
        good_key = _ed25519_pair()[0]
        monkeypatch.setenv("PRESIDIO_X402_EVIDENCE_KEY", good_key)
        with caplog.at_level(logging.DEBUG, logger="presidio_x402_mcp"):
            cfg = srv._evidence_from_env()
        assert good_key not in caplog.text and good_key not in repr(cfg)

    @pytest.mark.anyio
    async def test_key_file_and_hmac_algorithm(self, tmp_path, monkeypatch):
        secret = "s" * 40
        key_file = tmp_path / "evidence.key"
        key_file.write_text(secret + "\n")
        key_file.chmod(0o600)
        path = tmp_path / "d.jsonl"
        monkeypatch.setenv("PRESIDIO_X402_MCP_EVIDENCE_KEY_FILE", str(key_file))
        monkeypatch.setenv("PRESIDIO_X402_EVIDENCE_KEY", "ignored-when-a-key-file-is-set")
        monkeypatch.setenv("PRESIDIO_X402_MCP_EVIDENCE_ALGORITHM", "hmac-sha256")
        monkeypatch.setenv("PRESIDIO_X402_MCP_EVIDENCE_SIGNER", "ops-policy")
        monkeypatch.setenv("PRESIDIO_X402_MCP_DECISION_PATH", str(path))
        monkeypatch.setattr(srv, "_EVIDENCE", srv._evidence_from_env())
        await check_payment_policy(resource_url="https://x.test/a", amount_usd=1.0)
        env = json.loads(path.read_text())
        trust = {"ops-policy": {"alg": "hmac-sha256", "key": secret}}
        assert verify_decision_ref(env, trust).ok

    def test_short_hmac_secret_is_rejected(self, tmp_path, monkeypatch):
        monkeypatch.setenv("PRESIDIO_X402_EVIDENCE_KEY", "short")
        monkeypatch.setenv("PRESIDIO_X402_MCP_EVIDENCE_ALGORITHM", "hmac-sha256")
        monkeypatch.setenv("PRESIDIO_X402_MCP_DECISION_PATH", str(tmp_path / "d.jsonl"))
        assert srv._evidence_from_env() is None

    @pytest.mark.anyio
    async def test_emission_failure_does_not_change_the_gate_outcome(
        self, signed, monkeypatch, caplog
    ):
        class Broken:
            def write(self, _envelope):
                raise OSError("disk full")

        monkeypatch.setattr(srv, "_EVIDENCE", dataclasses.replace(srv._EVIDENCE, writer=Broken()))
        with caplog.at_level(logging.ERROR, logger="presidio_x402_mcp"):
            result = await check_payment_policy(resource_url="https://x.test/a", amount_usd=1.0)
        assert result == {"allowed": True}
        assert "emission failed" in caplog.text
        assert signed["key"] not in caplog.text


class TestRawUrlNeverReachesALog:
    """The parent's contract is that callers hand it the redacted URL; its
    PolicyEngine logs the URL it is given on violations and at DEBUG."""

    @pytest.mark.anyio
    async def test_no_tool_logs_the_raw_url_at_any_level(self, signed, caplog, monkeypatch):
        monkeypatch.setattr(
            srv,
            "_POLICY",
            PolicyEngine(
                PolicyConfig(
                    max_per_call_usd=5.0,
                    daily_limit_usd=6.0,
                    per_endpoint={"https://x.test": 4.5},
                )
            ),
        )
        with caplog.at_level(logging.DEBUG):
            await screen_payment_metadata(resource_url=PII_URL, description="for " + PII_URL)
            await check_payment_policy(resource_url=PII_URL, amount_usd=1.0)  # allowed
            await check_payment_policy(resource_url=PII_URL, amount_usd=50.0)  # per-call
            await check_payment_policy(resource_url=PII_URL, amount_usd=4.0)  # per-endpoint
            args = {
                "resource_url": PII_URL,
                "pay_to": "0xabc",
                "amount": "1",
                "currency": "USDC",
                "deadline_seconds": 1_800_000_002,
            }
            await check_payment_replay(**args)
            await check_payment_replay(**args)
        assert caplog.records, "expected the parent to log something at DEBUG"
        assert "alice.martin" not in caplog.text
        assert "alice.martin" not in signed["path"].read_text()

    @pytest.mark.anyio
    async def test_policy_engine_receives_only_the_redacted_url(self, monkeypatch):
        seen: list[str] = []
        engine = srv._POLICY

        class Spy:
            config = engine.config

            def check_and_record(self, *, resource_url, amount_usd):
                seen.append(resource_url)
                return engine.check_and_record(resource_url=resource_url, amount_usd=amount_usd)

        monkeypatch.setattr(srv, "_POLICY", Spy())
        await check_payment_policy(resource_url=PII_URL, amount_usd=1.0)
        assert seen == ["https://x.test/users/<EMAIL_ADDRESS>/exports"]

    @pytest.mark.anyio
    async def test_policy_denies_without_spend_when_screening_fails(self, monkeypatch):
        def boom(*_a, **_k):
            raise RuntimeError("filter exploded: " + PII_URL)

        calls: list[str] = []
        monkeypatch.setattr(srv, "PIIFilter", boom)
        monkeypatch.setattr(
            srv._POLICY, "check_and_record", lambda **kw: calls.append(kw["resource_url"])
        )
        result = await check_payment_policy(resource_url=PII_URL, amount_usd=1.0)
        assert result["allowed"] is False and "screening failed" in result["reason"]
        assert calls == []
