"""Gate-certificate parents on payment-decision@1 records (issue #82).

Certificates are issued here by ikigov-assess itself (``build_certificate`` +
``sign``, the ``[gate]`` extra) with the family Ed25519 test key, so the
verifier under test is the real one. Coverage:

- identity: the presidio-evidence ``gate-certificate/valid-certificate.json``
  vector hashes to its pinned ADR-0006 identity and verifies at its instant;
- accept: every record carries the verified identity as top-level ``parents``
  and still verifies with the parent's ``verify_decision_ref``;
- refuse to start: one variable without the other, tampered, expired,
  untrusted issuer, a decision other than OPEN, unreadable / oversized /
  non-JSON files, the extra not installed;
- expiry while running: records are still emitted, without the gate, and the
  gate's answer does not change;
- lineage comes from the operator only: no tool takes a ``parents`` argument.
"""

from __future__ import annotations

import builtins
import copy
import inspect
import json
import logging
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from presidio_x402 import PolicyConfig, PolicyEngine, ReplayGuard, verify_decision_ref
from presidio_x402.exceptions import ConfigurationError

from presidio_x402_mcp import server as srv
from presidio_x402_mcp.gate import (
    MAX_FILE_BYTES,
    GateCertificateError,
    GateParents,
    load_gate_parents,
)
from presidio_x402_mcp.server import (
    check_payment_policy,
    check_payment_replay,
    screen_payment_metadata,
)

ikigov_cert = pytest.importorskip("presidio_ikigov_assess.certificate")

VECTOR_PATH = Path(__file__).parent / "fixtures" / "gate-certificate-valid.json"
VECTOR_IDENTITY = "dbb7c6a36f0aea55bbe5dead3daf8f4f3d59116966e79bd4b78ecfe2a83ebd4a"
VECTOR_AT = datetime(2026, 7, 3, tzinfo=timezone.utc)

ISSUER = "presidio-hardened-ikigov-assess"
SEED = "01" * 32  # family test key (private seed)
PUBLIC_KEY = "8a88e3dd7409f195fd52db2d3cba5d72ca6709bf1d94121bf3748801b40f6f5c"
OTHER_SEED = "02" * 32
G0_ITEMS = frozenset({"S1", "S2", "S3"})
GATE_ENV = ("PRESIDIO_X402_MCP_GATE_CERTIFICATE", "PRESIDIO_X402_MCP_GATE_TRUST")


def _utc(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _issue(
    *,
    affirmed: frozenset[str] = G0_ITEMS,
    issued: datetime | None = None,
    valid_days: int = 30,
    seed: str = SEED,
    use_case: str = "payment-gate",
) -> dict:
    issued = issued or datetime.now(timezone.utc) - timedelta(days=1)
    doc = ikigov_cert.build_certificate(
        use_case=use_case,
        gate="G0",
        risk_class="medium",
        affirmed=affirmed,
        skipped=G0_ITEMS - affirmed,
        issuer=ISSUER,
        assessed_at=_utc(issued),
        not_after=_utc(issued + timedelta(days=valid_days)),
    )
    return ikigov_cert.sign(doc, alg="ed25519", key_hex_or_secret=seed, signer=ISSUER)


def _write(tmp_path: Path, name: str, payload: object) -> Path:
    path = tmp_path / name
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


@pytest.fixture
def trust(tmp_path: Path) -> Path:
    return _write(tmp_path, "trust.json", {ISSUER: {"alg": "ed25519", "public_key": PUBLIC_KEY}})


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    for name in GATE_ENV:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(srv, "_POLICY", PolicyEngine(PolicyConfig(max_per_call_usd=5.0)))
    monkeypatch.setattr(srv, "_REPLAY", ReplayGuard(ttl=300))
    monkeypatch.setattr(srv, "_GATE", None)
    monkeypatch.setattr(srv, "_GATE_EXPIRY_LOGGED", False)


@pytest.fixture
def signed(tmp_path, monkeypatch):
    sk = Ed25519PrivateKey.generate()
    public_hex = sk.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw).hex()
    path = tmp_path / "decisions.jsonl"
    monkeypatch.setenv("PRESIDIO_X402_EVIDENCE_KEY", sk.private_bytes_raw().hex())
    monkeypatch.setenv("PRESIDIO_X402_MCP_DECISION_PATH", str(path))
    monkeypatch.setattr(srv, "_EVIDENCE", srv._evidence_from_env())
    assert srv._EVIDENCE is not None

    def records() -> list[dict]:
        if not path.exists():
            return []
        return [json.loads(line) for line in path.read_text().splitlines()]

    return {
        "trust": {srv.DEFAULT_EVIDENCE_SIGNER: {"alg": "ed25519", "public_key": public_hex}},
        "records": records,
    }


def _configure(monkeypatch, certificates: list[Path], trust: Path) -> GateParents | None:
    monkeypatch.setenv(GATE_ENV[0], os.pathsep.join(str(p) for p in certificates))
    monkeypatch.setenv(GATE_ENV[1], str(trust))
    gate = srv._gate_from_env()
    monkeypatch.setattr(srv, "_GATE", gate)
    return gate


class TestIdentity:
    @pytest.fixture
    def vector_trust(self, tmp_path):
        # The vector's embedded evidence-refs are signed as presidio-hardened-ai
        # with the same family key (vector notes, trust_store).
        key = {"alg": "ed25519", "public_key": PUBLIC_KEY}
        return _write(tmp_path, "vt.json", {ISSUER: key, "presidio-hardened-ai": key})

    def test_family_vector_identity_and_bound(self, vector_trust):
        gate = load_gate_parents([VECTOR_PATH], vector_trust, now=VECTOR_AT)
        assert gate.identities == (VECTOR_IDENTITY,)
        assert gate.not_after == datetime(2027, 7, 2, tzinfo=timezone.utc)

    def test_vector_refused_once_expired(self, vector_trust):
        with pytest.raises(GateCertificateError, match="expired"):
            load_gate_parents(
                [VECTOR_PATH], vector_trust, now=datetime(2028, 1, 1, tzinfo=timezone.utc)
            )

    def test_duplicate_certificate_named_once(self, tmp_path, trust):
        cert = _write(tmp_path, "c.json", _issue())
        other = _write(tmp_path, "d.json", _issue(use_case="other-gate", valid_days=10))
        gate = load_gate_parents([cert, other, cert], trust)
        assert len(gate.identities) == 2
        assert gate.identities[0] == ikigov_cert.certificate_content_hash(_issue_doc(cert))
        # The earliest bound governs.
        assert gate.not_after == ikigov_cert.parse_timestamp(_issue_doc(other)["not_after"])

    def test_current_drops_parents_at_not_after(self):
        bound = datetime(2026, 1, 1, tzinfo=timezone.utc)
        gate = GateParents(("a" * 64,), bound)
        assert gate.current(bound) == ["a" * 64]
        assert gate.current(bound + timedelta(seconds=1)) == []
        assert GateParents(("a" * 64,), None).current(bound) == ["a" * 64]


def _issue_doc(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


class TestRecordsCarryTheGate:
    @pytest.mark.anyio
    async def test_every_tool_record_names_the_gate(self, tmp_path, trust, signed, monkeypatch):
        cert = _write(tmp_path, "cert.json", _issue())
        _configure(monkeypatch, [cert], trust)
        identity = ikigov_cert.certificate_content_hash(_issue_doc(cert))

        await screen_payment_metadata(resource_url="https://x.test/a")
        await check_payment_policy(resource_url="https://x.test/a", amount_usd=1.0)
        await check_payment_replay(
            resource_url="https://x.test/r",
            pay_to="0xabc",
            amount="1.00",
            currency="USDC",
            deadline_seconds=1_800_000_000,
        )
        envs = signed["records"]()
        assert len(envs) == 3
        for env in envs:
            check = verify_decision_ref(env, signed["trust"])
            assert check.ok, check.reason
            assert env["payment_decision"]["parents"] == [identity]
            assert env["payment_decision"]["provenance"]["parents"] == [identity]

    def test_unset_means_no_gate(self):
        assert srv._gate_from_env() is None

    def test_gate_without_evidence_refuses(self, tmp_path, trust, monkeypatch):
        monkeypatch.setattr(srv, "_EVIDENCE", None)
        cert = _write(tmp_path, "cert.json", _issue())
        with pytest.raises(ConfigurationError, match="evidence is disabled"):
            _configure(monkeypatch, [cert], trust)

    def test_tools_take_no_parents_argument(self):
        for tool in (screen_payment_metadata, check_payment_policy, check_payment_replay):
            assert "parents" not in inspect.signature(tool).parameters


class TestExpiryWhileRunning:
    @pytest.mark.anyio
    async def test_expired_gate_is_dropped_and_the_answer_stands(
        self, tmp_path, trust, signed, monkeypatch, caplog
    ):
        cert = _write(tmp_path, "cert.json", _issue(valid_days=2))
        other = _write(tmp_path, "other.json", _issue(use_case="other-gate", valid_days=30))
        gate = _configure(monkeypatch, [cert, other], trust)
        assert gate is not None and gate.not_after is not None
        later = gate.not_after + timedelta(minutes=1)
        monkeypatch.setattr(srv, "_utcnow", lambda: later)

        with caplog.at_level(logging.WARNING, logger="presidio_x402_mcp"):
            allowed = await check_payment_policy(resource_url="https://x.test/a", amount_usd=1.0)
            blocked = await check_payment_policy(resource_url="https://x.test/a", amount_usd=50.0)
        assert allowed["allowed"] is True and blocked["allowed"] is False
        # The earliest bound governs: the still-valid certificate is dropped too.
        for env in signed["records"]():
            assert verify_decision_ref(env, signed["trust"]).ok
            assert "parents" not in env["payment_decision"]
        expired = [r for r in caplog.records if "expired" in r.getMessage()]
        assert len(expired) == 1


class TestRefusesToStart:
    @pytest.mark.parametrize("which", [0, 1])
    def test_one_variable_without_the_other(self, monkeypatch, which):
        monkeypatch.setenv(GATE_ENV[which], "/nonexistent")
        with pytest.raises(ConfigurationError, match="set together"):
            srv._gate_from_env()

    def _refused(self, monkeypatch, cert: Path, trust: Path, match: str) -> None:
        monkeypatch.setenv(GATE_ENV[0], str(cert))
        monkeypatch.setenv(GATE_ENV[1], str(trust))
        with pytest.raises(ConfigurationError, match=match):
            srv._gate_from_env()

    def test_tampered(self, tmp_path, trust, monkeypatch):
        doc = copy.deepcopy(_issue())
        doc["use_case"] = "something-else"
        self._refused(monkeypatch, _write(tmp_path, "c.json", doc), trust, "does not verify")

    def test_expired(self, tmp_path, trust, monkeypatch):
        old = _issue(issued=datetime.now(timezone.utc) - timedelta(days=40), valid_days=30)
        self._refused(monkeypatch, _write(tmp_path, "c.json", old), trust, "expired")

    def test_untrusted_issuer(self, tmp_path, trust, monkeypatch):
        cert = _write(tmp_path, "c.json", _issue(seed=OTHER_SEED))
        self._refused(monkeypatch, cert, trust, "does not verify")

    def test_gate_not_open(self, tmp_path, trust, monkeypatch):
        cert = _write(tmp_path, "c.json", _issue(affirmed=frozenset()))
        self._refused(monkeypatch, cert, trust, "only an open gate")

    def test_missing_file(self, tmp_path, trust, monkeypatch):
        self._refused(monkeypatch, tmp_path / "absent.json", trust, "cannot read")

    def test_oversized_file(self, tmp_path, trust, monkeypatch):
        big = tmp_path / "big.json"
        big.write_bytes(b" " * (MAX_FILE_BYTES + 1))
        self._refused(monkeypatch, big, trust, "exceeds")

    def test_not_json(self, tmp_path, trust, monkeypatch):
        bad = tmp_path / "bad.json"
        bad.write_text("{not json", encoding="utf-8")
        self._refused(monkeypatch, bad, trust, "not valid JSON")

    def test_bad_trust_store(self, tmp_path, monkeypatch):
        cert = _write(tmp_path, "c.json", _issue())
        self._refused(monkeypatch, cert, _write(tmp_path, "t.json", []), "trust store")

    def test_extra_not_installed(self, tmp_path, trust, monkeypatch):
        cert = _write(tmp_path, "c.json", _issue())
        real_import = builtins.__import__

        def no_ikigov(name, *args, **kwargs):
            if name.startswith("presidio_ikigov_assess"):
                raise ImportError(name)
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", no_ikigov)
        self._refused(monkeypatch, cert, trust, r"\[gate\] extra")
