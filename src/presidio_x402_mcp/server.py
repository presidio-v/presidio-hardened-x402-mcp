"""MCP server for presidio-hardened-x402 — PII screening for x402 agents.

Tools (default in-process mode):
  - screen_payment_metadata  — PII scan of payment metadata (no side effects)
  - check_payment_policy     — spending-policy gate (RECORDS spend on call)
  - check_payment_replay     — duplicate-payment gate (RECORDS fingerprint on call)

Environment variables (see README and `plan/mcp-server-plan.md` Phase 0):
  - PRESIDIO_X402_MCP_MODE                   regex | nlp           (default: regex)
  - PRESIDIO_X402_MCP_MAX_PER_CALL_USD       float                 (policy)
  - PRESIDIO_X402_MCP_DAILY_LIMIT_USD        float                 (policy)
  - PRESIDIO_X402_MCP_PER_ENDPOINT_JSON      JSON {url: usd}       (policy)
  - PRESIDIO_X402_MCP_WINDOW_SECONDS         int (default 86400)   (policy)
  - PRESIDIO_X402_MCP_AGENT_ID               str                   (policy)
  - PRESIDIO_X402_MCP_REPLAY_TTL             int (default 300)     (replay)
  - PRESIDIO_X402_MCP_REDIS_URL              redis://...           (replay, optional)
  - PRESIDIO_X402_MCP_AUDIT_PATH             path/to/audit.jsonl   (omit -> NullAuditWriter)
  - PRESIDIO_X402_MCP_LOG_LEVEL              DEBUG|INFO|...        (default INFO)
  - PRESIDIO_X402_MCP_REMOTE_BASE_URL        https://screen.…      (HTTP-proxy mode, tool 1 only)
  - PRESIDIO_X402_MCP_REMOTE_API_KEY         opaque                (HTTP-proxy mode, paired)

Signed decision evidence (payment-decision@1, written alongside the audit log):
  - PRESIDIO_X402_MCP_EVIDENCE_KEY_FILE      path to signing key   (preferred over the env key)
  - PRESIDIO_X402_EVIDENCE_KEY               signing key           (parent library's variable)
  - PRESIDIO_X402_MCP_DECISION_PATH          path/to/decisions.jsonl
  - PRESIDIO_X402_MCP_EVIDENCE_ALGORITHM     ed25519 | hmac-sha256 (default ed25519)
  - PRESIDIO_X402_MCP_EVIDENCE_SIGNER        trust-store identity  (default: package name)
  - PRESIDIO_X402_MCP_EVIDENCE_KEY_ID        optional key id
  - PRESIDIO_X402_MCP_REQUIRE_EVIDENCE_KEY   1 -> refuse to start without working evidence

Cross-process keys (read by the underlying lib):
  - PRESIDIO_X402_FINGERPRINT_KEY            32-byte hex           (replay HMAC)
  - PRESIDIO_X402_CHAIN_KEY                  32-byte hex           (audit HMAC chain)

Critical: stdio MCP servers must NEVER write to stdout (corrupts JSON-RPC frames).
All diagnostic output goes through `logging`, which defaults to stderr.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import stat
import threading
from collections import OrderedDict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx
from mcp.server.mcpserver import MCPServer
from presidio_x402 import (
    NOT_EVALUATED,
    AuditLog,
    FileAuditWriter,
    FileDecisionRefWriter,
    NullAuditWriter,
    PIIFilter,
    PolicyConfig,
    PolicyEngine,
    ReplayGuard,
    build_decision_evidence,
    build_payment_decision_content,
)
from presidio_x402.decision_ref import (
    ControlResults,
    details_hash,
    fingerprint_hash,
    policy_limit_hash,
    policy_snapshot_hash,
)
from presidio_x402.exceptions import (
    ConfigurationError,
    PolicyViolationError,
    ReplayDetectedError,
)
from presidio_x402.mica import EvidenceError, sign_evidence
from presidio_x402.replay_guard import compute_fingerprint

from presidio_x402_mcp import __version__

logger = logging.getLogger("presidio_x402_mcp")
logger.setLevel(os.getenv("PRESIDIO_X402_MCP_LOG_LEVEL", "INFO"))

# Wire-contract field-length limits (mirror screening-api/src/screening_api/models.py:40-44).
_MAX_RESOURCE_URL = 2048
_MAX_DESCRIPTION = 4096
_MAX_REASON = 4096


# ---------------------------------------------------------------------------
# Startup wiring
# ---------------------------------------------------------------------------


def _policy_config_from_env() -> PolicyConfig:
    per_endpoint_json = os.getenv("PRESIDIO_X402_MCP_PER_ENDPOINT_JSON", "")
    per_endpoint: dict[str, float] = {}
    if per_endpoint_json:
        try:
            raw = json.loads(per_endpoint_json)
            per_endpoint = {str(k): float(v) for k, v in raw.items()}
        except (json.JSONDecodeError, TypeError, ValueError) as exc:
            logger.error("PRESIDIO_X402_MCP_PER_ENDPOINT_JSON ignored: %s", exc)

    def _float(name: str) -> float | None:
        raw = os.getenv(name)
        return float(raw) if raw else None

    return PolicyConfig(
        max_per_call_usd=_float("PRESIDIO_X402_MCP_MAX_PER_CALL_USD"),
        daily_limit_usd=_float("PRESIDIO_X402_MCP_DAILY_LIMIT_USD"),
        per_endpoint=per_endpoint,
        window_seconds=int(os.getenv("PRESIDIO_X402_MCP_WINDOW_SECONDS", "86400")),
        agent_id=os.getenv("PRESIDIO_X402_MCP_AGENT_ID"),
    )


def _audit_writer() -> Any:
    path = os.getenv("PRESIDIO_X402_MCP_AUDIT_PATH")
    if path:
        return FileAuditWriter(path)
    return NullAuditWriter()


_MODE: str = os.getenv("PRESIDIO_X402_MCP_MODE", "regex")
_POLICY = PolicyEngine(_policy_config_from_env())
_REPLAY = ReplayGuard(
    ttl=int(os.getenv("PRESIDIO_X402_MCP_REPLAY_TTL", "300")),
    redis_url=os.getenv("PRESIDIO_X402_MCP_REDIS_URL"),
)
_AUDIT = AuditLog(writer=_audit_writer())

# Loopback is exempt from the TLS requirement: traffic that never leaves the host
# has no network path to intercept. Everything else must be https.
_LOOPBACK_HOSTS = frozenset({"localhost", "127.0.0.1", "::1"})


def _validate_remote_base_url(raw: str) -> str:
    """Return *raw* if payment metadata may safely be sent to it, else raise.

    Remote mode puts the *pre-redaction* ``resource_url`` / ``description`` /
    ``reason`` in the request body and a long-lived key in the ``X-API-Key``
    header. Over plain http both are cleartext on the wire, which inverts the
    purpose of the tool — so a non-TLS endpoint is refused rather than used.

    This fails closed at startup rather than at first call, and it raises rather
    than quietly falling back to in-process screening: a silent downgrade would
    leave the operator believing metadata is being screened remotely under their
    configured policy. An `http://` typo should stop the server, not change what
    it does.
    """
    parsed = urlparse(raw)
    if parsed.scheme == "https":
        return raw
    if parsed.scheme == "http" and parsed.hostname in _LOOPBACK_HOSTS:
        return raw
    raise ValueError(
        "PRESIDIO_X402_MCP_REMOTE_BASE_URL must use https:// — got "
        f"{parsed.scheme or 'no scheme'!r}. Plain http is accepted only for "
        f"loopback hosts ({', '.join(sorted(_LOOPBACK_HOSTS))}). Remote mode "
        "transmits pre-redaction PII and the screening API key."
    )


# HTTP-proxy mode for tool 1 (screen_payment_metadata). Activated only when
# both env vars are set; tools 2 and 3 always stay in-process.
_REMOTE_BASE_URL: str | None = os.getenv("PRESIDIO_X402_MCP_REMOTE_BASE_URL")
if _REMOTE_BASE_URL:
    # Validated whenever the URL is set, not only when remote mode ends up
    # enabled — a set-but-unsafe URL is a deployment defect either way, and
    # catching it needs to happen before a missing API key masks it.
    _REMOTE_BASE_URL = _validate_remote_base_url(_REMOTE_BASE_URL)
_REMOTE_API_KEY: str | None = os.getenv("PRESIDIO_X402_MCP_REMOTE_API_KEY")
_REMOTE_ENABLED: bool = bool(_REMOTE_BASE_URL and _REMOTE_API_KEY)
_REMOTE_TIMEOUT = httpx.Timeout(10.0, connect=3.0)


# ---------------------------------------------------------------------------
# Signed decision evidence (payment-decision@1)
#
# The HMAC audit log is tamper-evident only to whoever holds the chain key; a
# third party cannot check it. Each gate decision is therefore also emitted as
# a signed payment-decision@1 record through the parent library, which a
# verifier checks offline against a pinned trust store. Building, signing and
# the record schema all stay in the parent; this module only maps a tool call
# onto the parent's ControlResults.
# ---------------------------------------------------------------------------

_EVIDENCE_KEY_FILE_ENV = "PRESIDIO_X402_MCP_EVIDENCE_KEY_FILE"
# Same variable the parent's treasury-binding CLI reads, so one secret serves both.
_EVIDENCE_KEY_ENV = "PRESIDIO_X402_EVIDENCE_KEY"  # gitleaks:allow (env-var name)
_DECISION_PATH_ENV = "PRESIDIO_X402_MCP_DECISION_PATH"
_EVIDENCE_ALGORITHM_ENV = "PRESIDIO_X402_MCP_EVIDENCE_ALGORITHM"
_EVIDENCE_SIGNER_ENV = "PRESIDIO_X402_MCP_EVIDENCE_SIGNER"
_EVIDENCE_KEY_ID_ENV = "PRESIDIO_X402_MCP_EVIDENCE_KEY_ID"  # gitleaks:allow
_REQUIRE_EVIDENCE_ENV = "PRESIDIO_X402_MCP_REQUIRE_EVIDENCE_KEY"

DEFAULT_EVIDENCE_SIGNER = "presidio-hardened-x402-mcp"
_MIN_HMAC_SECRET_CHARS = 32
#: Fields an MCP tool never sees (no wallet, no network, no raw 402 offer).
_UNSPECIFIED = "unspecified"
_OFFER_ABSENT = "not-presented"
#: A decision_ref is a bare 64-hex sha256; bound the list an agent may pass.
_DECISION_REF_RE = re.compile(r"^[0-9a-f]{64}$")
_MAX_PRIOR_REFS = 8
_ISSUED_REFS_CAP = 4096
#: Payment fields copied into a record verbatim only when they look like an
#: address / amount / ticker; anything else is still bound by details_hash.
_RECORD_TOKEN_RE = re.compile(r"^[A-Za-z0-9:._-]{1,128}$")


def _truthy(value: str | None) -> bool:
    return (value or "").strip().lower() in ("1", "true", "yes", "on")


@dataclass(frozen=True)
class _EvidenceConfig:
    signing_key: str = field(repr=False)  # never in repr, tracebacks, or logs
    algorithm: str
    signer: str
    key_id: str | None
    writer: Any


def _read_key_file(path: str) -> str:
    key_path = Path(path)
    mode = key_path.stat().st_mode
    if os.name == "posix" and mode & (stat.S_IRWXG | stat.S_IRWXO):
        logger.warning(
            "%s is readable by group or others; restrict it to the server user (chmod 600)",
            _EVIDENCE_KEY_FILE_ENV,
        )
    return key_path.read_text(encoding="utf-8").strip()


def _evidence_from_env() -> _EvidenceConfig | None:
    """Read the signing configuration once, at startup.

    Without a usable key the server keeps its pre-0.3.0 behaviour (HMAC audit
    log only) and says so once, loudly. Refusing to start would break every
    existing deployment on upgrade, so failing closed is opt-in via
    ``PRESIDIO_X402_MCP_REQUIRE_EVIDENCE_KEY``. No message here ever includes
    key material.
    """
    strict = _truthy(os.getenv(_REQUIRE_EVIDENCE_ENV))

    def disabled(reason: str, level: int = logging.WARNING) -> None:
        if strict:
            raise ConfigurationError(
                f"signed payment-decision@1 evidence is not available: {reason}. "
                f"Refusing to start because {_REQUIRE_EVIDENCE_ENV} is set."
            )
        # The variable names are spelled out rather than interpolated from the
        # *_KEY_* constants, so static analysis sees no key-named value reach a log.
        logger.log(
            level,
            "Signed payment-decision@1 evidence is DISABLED: %s. Gate decisions are "
            "recorded only in the HMAC audit log. Set PRESIDIO_X402_MCP_EVIDENCE_KEY_FILE "
            "(or PRESIDIO_X402_EVIDENCE_KEY) and PRESIDIO_X402_MCP_DECISION_PATH to enable "
            "it; set PRESIDIO_X402_MCP_REQUIRE_EVIDENCE_KEY=1 to refuse to start without it.",
            reason,
        )
        return None

    key_file = os.getenv(_EVIDENCE_KEY_FILE_ENV, "").strip()
    if key_file:
        try:
            key = _read_key_file(key_file)
        except OSError as exc:
            return disabled(
                f"PRESIDIO_X402_MCP_EVIDENCE_KEY_FILE could not be read ({type(exc).__name__})",
                logging.ERROR,
            )
    else:
        key = os.getenv(_EVIDENCE_KEY_ENV, "").strip()
    if not key:
        return disabled("no signing key is configured")

    path = os.getenv(_DECISION_PATH_ENV, "").strip()
    if not path:
        return disabled(
            f"a signing key is set but {_DECISION_PATH_ENV} is not, so records have nowhere to go",
            logging.ERROR,
        )

    algorithm = os.getenv(_EVIDENCE_ALGORITHM_ENV, "").strip() or "ed25519"
    signer = os.getenv(_EVIDENCE_SIGNER_ENV, "").strip() or DEFAULT_EVIDENCE_SIGNER
    key_id = os.getenv(_EVIDENCE_KEY_ID_ENV, "").strip() or None
    if algorithm == "hmac-sha256" and len(key) < _MIN_HMAC_SECRET_CHARS:
        return disabled(
            f"the hmac-sha256 secret is shorter than {_MIN_HMAC_SECRET_CHARS} characters",
            logging.ERROR,
        )
    # Sign a probe once so a malformed key or unknown algorithm surfaces at
    # startup rather than as a silent per-call emission failure.
    try:
        sign_evidence("0" * 64, signer, algorithm=algorithm, key=key)
    except EvidenceError:
        return disabled(f"the signing key is not valid for algorithm {algorithm!r}", logging.ERROR)

    logger.info(
        "Signed payment-decision@1 evidence enabled: signer=%s algorithm=%s path=%s",
        signer,
        algorithm,
        path,
    )
    return _EvidenceConfig(
        signing_key=key,
        algorithm=algorithm,
        signer=signer,
        key_id=key_id,
        writer=FileDecisionRefWriter(path),
    )


_EVIDENCE: _EvidenceConfig | None = _evidence_from_env()

# decision_refs this process signed. A prior_decision_refs entry is signed into
# a later record as provenance, so only refs this server issued are accepted —
# otherwise the signer would vouch for links an agent made up.
_ISSUED_REFS: OrderedDict[str, None] = OrderedDict()
_ISSUED_LOCK = threading.Lock()

mcp = MCPServer("presidio-x402")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _validate_lengths(resource_url: str, description: str, reason: str) -> None:
    if len(resource_url) > _MAX_RESOURCE_URL:
        raise ValueError(f"resource_url exceeds {_MAX_RESOURCE_URL} characters")
    if len(description) > _MAX_DESCRIPTION:
        raise ValueError(f"description exceeds {_MAX_DESCRIPTION} characters")
    if len(reason) > _MAX_REASON:
        raise ValueError(f"reason exceeds {_MAX_REASON} characters")


def _screen_url(resource_url: str) -> tuple[str, list[str] | None]:
    """Redact *resource_url* and return it with the entity types found.

    Entity types are ``None`` when redaction failed, so a caller cannot mistake
    "screening did not run" for "no PII".
    """
    try:
        filt = PIIFilter(mode=_MODE, redaction_template="<{entity_type}>")
        clean, hits = filt.scan_and_redact(resource_url)
        return clean, sorted({h.entity_type for h in hits})
    except Exception:  # noqa: BLE001 - see _audit_safe_url: never leak the raw URL
        # No exc_info: a traceback can carry the input string, i.e. the raw URL.
        logger.warning("URL redaction failed; using a placeholder")
        return "<REDACTION_FAILED>", None


def _audit_safe_url(resource_url: str) -> str:
    """Redact *resource_url* before it is written to the audit log.

    Tools 2 and 3 receive the URL unscreened — the agent is not obliged to have
    called `screen_payment_metadata` first — so writing it verbatim would put the
    very PII this server exists to catch into a file on disk, and one that
    outlives the process. The parent library takes the same line, auditing the
    redacted URL rather than the raw one (`core.py`, `resource_url=clean_url`).

    Redaction failures must not break the payment path: the caller is mid-gate,
    and an audit-formatting error is not a reason to refuse an otherwise valid
    payment. On failure this degrades to a constant placeholder — never to the
    raw URL.
    """
    return _screen_url(resource_url)[0]


def _record_origin(redacted_url: str) -> str:
    """Scheme and host of an already-redacted URL, without userinfo."""
    try:
        parsed = urlparse(redacted_url)
        host = parsed.hostname
        port = parsed.port
    except ValueError:
        return _UNSPECIFIED
    if not parsed.scheme or not host:
        return _UNSPECIFIED
    if ":" in host:
        host = f"[{host}]"
    return f"{parsed.scheme}://{host}" + (f":{port}" if port else "")


def _record_token(value: str) -> str:
    return value if _RECORD_TOKEN_RE.fullmatch(value) else "unrecognised"


def _validated_prior_refs(prior_decision_refs: list[str] | None) -> list[str]:
    """Check caller-supplied prior refs before any gate records state.

    Runs ahead of ``check_and_record`` so a rejected call never consumes spend
    budget or a replay fingerprint.
    """
    refs = list(prior_decision_refs or [])
    if len(refs) > _MAX_PRIOR_REFS:
        raise ValueError(f"prior_decision_refs accepts at most {_MAX_PRIOR_REFS} entries")
    for ref in refs:
        if not (isinstance(ref, str) and _DECISION_REF_RE.fullmatch(ref)):
            raise ValueError("prior_decision_refs entries must be 64-character lowercase hex")
    if _EVIDENCE is not None:
        with _ISSUED_LOCK:
            unknown = [r for r in refs if r not in _ISSUED_REFS]
        if unknown:
            raise ValueError(
                "prior_decision_refs contains a decision_ref this server did not issue"
            )
    return list(dict.fromkeys(refs))


def _controls(
    pii_entities: list[str],
    *,
    pii_mutated: bool,
    policy_verdict: str = NOT_EVALUATED,
    replay_verdict: str = NOT_EVALUATED,
    fingerprint: str | None = None,
) -> ControlResults:
    """Map one tool's outcome onto the parent's five-control record.

    Every control the tool did not run is ``NOT_EVALUATED`` — a record never
    claims a check that did not happen. Each tool screens the URL it is handed,
    so ``pii`` is always evaluated: ``screen_payment_metadata`` returns redacted
    strings (``PII_REDACTED``); the gates observe PII in the URL but pay it
    unchanged, so the honest verdict there is ``PII_WARNED``. The MCP has no
    wallet allowlist or multi-party approval, so ``trusted_wallet`` and ``mpa``
    are never evaluated.
    """
    if not pii_entities:
        pii_verdict = "PII_NONE"
    else:
        pii_verdict = "PII_REDACTED" if pii_mutated else "PII_WARNED"
    policy_ran = policy_verdict != NOT_EVALUATED
    config = _POLICY.config
    return ControlResults(
        pii_verdict=pii_verdict,
        pii_entities=tuple(pii_entities),
        pii_mutated=bool(pii_entities) and pii_mutated,
        trusted_wallet_verdict=NOT_EVALUATED,
        policy_verdict=policy_verdict,
        policy_snapshot_hash=policy_snapshot_hash(config) if policy_ran else "",
        policy_limit_hash=policy_limit_hash(config) if policy_ran else None,
        replay_verdict=replay_verdict,
        replay_fingerprint_hash=fingerprint_hash(fingerprint) if fingerprint else None,
        mpa_verdict=NOT_EVALUATED,
    )


def _emit_decision(
    gate: str,
    controls: ControlResults,
    *,
    resource_origin: str,
    pay_to: str = _UNSPECIFIED,
    amount: str = _UNSPECIFIED,
    currency: str = _UNSPECIFIED,
    prior_decision_refs: list[str] | None = None,
) -> str | None:
    """Sign and write one payment-decision@1 record; return its decision_ref.

    Best-effort, like the parent pipeline's emitter: the gate has already
    decided, and a failure to record that decision must not reverse it. Errors
    are logged by type only, so nothing derived from the key reaches a log.
    """
    cfg = _EVIDENCE
    if cfg is None:
        return None
    try:
        content = build_payment_decision_content(
            agent_id=_POLICY.config.agent_id or "",
            payment_signer=_UNSPECIFIED,
            network=_UNSPECIFIED,
            binding="x402",
            offer_hash_absent=_OFFER_ABSENT,
            details_hash=details_hash(
                pay_to=pay_to, amount=amount, currency=currency, network=_UNSPECIFIED
            ),
            pay_to=_record_token(pay_to),
            amount=_record_token(amount),
            currency=_record_token(currency),
            resource_origin=resource_origin,
            controls=controls,
            prior_decision_refs=prior_decision_refs,
        )
        envelope = build_decision_evidence(
            content,
            signing_key=cfg.signing_key,
            algorithm=cfg.algorithm,
            signer=cfg.signer,
            key_id=cfg.key_id,
            source_version=__version__,
        )
        cfg.writer.write(envelope)
    except Exception as exc:  # noqa: BLE001 - see docstring: never reverse a decision
        logger.error(
            "payment-decision@1 emission failed for the %s gate (%s); gate outcome unaffected",
            gate,
            type(exc).__name__,
        )
        return None
    decision_ref = str(envelope["decision_ref"])
    with _ISSUED_LOCK:
        _ISSUED_REFS[decision_ref] = None
        while len(_ISSUED_REFS) > _ISSUED_REFS_CAP:
            _ISSUED_REFS.popitem(last=False)
    return decision_ref


async def _record_decision(
    gate: str,
    url_entities: list[str] | None,
    redacted_url: str,
    *,
    pii_mutated: bool = False,
    policy_verdict: str = NOT_EVALUATED,
    replay_verdict: str = NOT_EVALUATED,
    fingerprint: str | None = None,
    **payment: Any,
) -> str | None:
    if _EVIDENCE is None:
        return None
    if url_entities is None:
        logger.warning("no payment-decision@1 record for the %s gate: URL screening failed", gate)
        return None
    controls = _controls(
        url_entities,
        pii_mutated=pii_mutated,
        policy_verdict=policy_verdict,
        replay_verdict=replay_verdict,
        fingerprint=fingerprint,
    )
    return await asyncio.to_thread(
        _emit_decision,
        gate,
        controls,
        resource_origin=_record_origin(redacted_url),
        **payment,
    )


def _collapse(hits: list, field: str) -> list[dict[str, Any]]:
    # Mirrors screening-api/src/screening_api/screening.py:_collapse (lines 38-48).
    counts: dict[str, int] = {}
    for h in hits:
        counts[h.entity_type] = counts.get(h.entity_type, 0) + 1
    return [{"entity_type": et, "field": field, "count": n} for et, n in counts.items()]


def _scan_in_process(
    resource_url: str,
    description: str,
    reason: str,
    entities: list[str] | None,
) -> tuple[str, str, str, list[dict[str, Any]]]:
    # Per-call PIIFilter mirrors screening.py:25 — needed to honour the per-call
    # entity allowlist without coupling all callers to one shared filter.
    filt = PIIFilter(mode=_MODE, entities=entities, redaction_template="<{entity_type}>")
    clean_url, url_hits = filt.scan_and_redact(resource_url)
    clean_desc, desc_hits = filt.scan_and_redact(description)
    clean_reason, reason_hits = filt.scan_and_redact(reason)
    findings: list[dict[str, Any]] = []
    findings.extend(_collapse(url_hits, "resource_url"))
    findings.extend(_collapse(desc_hits, "description"))
    findings.extend(_collapse(reason_hits, "reason"))
    return clean_url, clean_desc, clean_reason, findings


async def _scan_remote(
    resource_url: str,
    description: str,
    reason: str,
    entities: list[str] | None,
) -> dict[str, Any]:
    """POST /v1/screen on the configured remote screening-api.

    Returns either the wire-contract success body (extended with mode:"remote")
    or a structured error dict with an `error` discriminator. Never falls back
    to in-process — agents must be able to detect when centralized audit was
    bypassed.

    We bypass ``presidio_x402.ScreeningClient`` here: its
    ``scan_payment_fields`` reconstructs ``EntityResult`` objects from the
    wire-contract response but drops the per-field attribution that this tool
    surfaces to callers. Calling the endpoint directly preserves field info.
    """
    payload: dict[str, Any] = {
        "resource_url": resource_url,
        "description": description,
        "reason": reason,
    }
    if entities is not None:
        payload["entities"] = entities

    url = f"{(_REMOTE_BASE_URL or '').rstrip('/')}/v1/screen"
    headers = {"X-API-Key": _REMOTE_API_KEY or ""}
    try:
        async with httpx.AsyncClient(timeout=_REMOTE_TIMEOUT) as client:
            resp = await client.post(url, json=payload, headers=headers)
    except (httpx.RequestError, httpx.TimeoutException) as exc:
        return {"error": "unavailable", "detail": str(exc), "mode": "remote"}

    if resp.status_code == 401:
        return {
            "error": "auth_error",
            "detail": "remote screening-api rejected the API key",
            "mode": "remote",
        }
    if resp.status_code == 429:
        retry_after_raw = resp.headers.get("Retry-After")
        retry_after: int | None = None
        if retry_after_raw and retry_after_raw.isdigit():
            retry_after = int(retry_after_raw)
        return {
            "error": "rate_limit",
            "detail": "remote screening-api rate limit exceeded (HTTP 429)",
            "retry_after": retry_after,
            "mode": "remote",
        }
    if resp.status_code >= 500 or resp.status_code != 200:
        return {
            "error": "unavailable",
            "detail": f"remote screening-api returned HTTP {resp.status_code}",
            "mode": "remote",
        }

    data = resp.json()
    return {
        "redacted_resource_url": data["redacted_resource_url"],
        "redacted_description": data["redacted_description"],
        "redacted_reason": data["redacted_reason"],
        "entities_found": data["entities_found"],
        "mode": "remote",
    }


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------


@mcp.tool()
async def screen_payment_metadata(
    resource_url: str,
    description: str = "",
    reason: str = "",
    entities: list[str] | None = None,
) -> dict[str, Any]:
    """Screen x402 payment metadata for PII before signing the payment.

    Call BEFORE sending the payment request. Detects emails, phone numbers,
    SSNs, names, and other PII in the resource URL, description, and reason
    fields and returns redacted strings plus per-field entity counts.

    No side effects.

    Runs in one of two modes:
      - in_process (default): wraps the local presidio_x402 PIIFilter.
      - remote: when both PRESIDIO_X402_MCP_REMOTE_BASE_URL and
        ..._REMOTE_API_KEY are set, POSTs to /v1/screen on that host
        for centralized audit. On remote failure, returns a structured
        error dict instead of silently falling back — the caller must
        decide whether to retry, accept reduced screening, or abort.

    Args:
        resource_url: x402 resource URL the agent is about to pay (max 2048 chars).
        description: Human-readable description (max 4096 chars).
        reason: Reason / memo string (max 4096 chars).
        entities: Optional whitelist of Presidio entity types to detect.
            If None, all configured entities are scanned.

    Returns:
        On success: dict with keys redacted_resource_url, redacted_description,
        redacted_reason, entities_found (list of {entity_type, field, count}),
        and mode (one of "in_process", "remote"); plus decision_ref when signed
        decision evidence is enabled (pass it to the gates as prior_decision_refs).
        On remote failure: dict with keys error (one of "auth_error",
        "rate_limit", "unavailable"), detail, optional retry_after (for
        rate_limit), and mode ("remote").
    """
    _validate_lengths(resource_url, description, reason)
    if _REMOTE_ENABLED:
        remote = await _scan_remote(resource_url, description, reason, entities)
        if "error" not in remote:
            remote_types = sorted({f["entity_type"] for f in remote["entities_found"]})
            d_ref = await _record_decision(
                "screen", remote_types, remote["redacted_resource_url"], pii_mutated=True
            )
            if d_ref:
                remote["decision_ref"] = d_ref
        return remote
    url, desc, reason_out, findings = await asyncio.to_thread(
        _scan_in_process,
        resource_url,
        description,
        reason,
        entities,
    )
    entity_types = [f["entity_type"] for f in findings]
    _AUDIT.emit(
        "PII_REDACTED" if entity_types else "PAYMENT_ALLOWED",
        # Already redacted by the scan above — never the caller's raw URL.
        resource_url=url,
        outcome="allowed",
        pii_entities_found=entity_types,
    )
    result: dict[str, Any] = {
        "redacted_resource_url": url,
        "redacted_description": desc,
        "redacted_reason": reason_out,
        "entities_found": findings,
        "mode": "in_process",
    }
    d_ref = await _record_decision("screen", sorted(set(entity_types)), url, pii_mutated=True)
    if d_ref:
        result["decision_ref"] = d_ref
    return result


@mcp.tool()
async def check_payment_policy(
    resource_url: str,
    amount_usd: float,
    prior_decision_refs: list[str] | None = None,
) -> dict[str, Any]:
    """Check whether a payment is allowed by the configured spending policy.

    WARNING: this records the spend against rolling time-window ledgers.
    Call exactly once, immediately before submitting the payment. If you call
    this and then do not pay, the spend window will be inflated until it rolls
    over.

    Configure limits at server startup via PRESIDIO_X402_MCP_* env vars.

    Args:
        resource_url: x402 resource URL being paid. Screened first; only the
            redacted URL reaches the policy engine (per-endpoint limits match on
            it, so keep PII out of configured endpoint prefixes).
        amount_usd: Payment amount in USD-equivalent.
        prior_decision_refs: Optional decision_ref values this server returned
            earlier for the same payment (e.g. from screen_payment_metadata);
            linked into the signed record. Max 8.

    Returns:
        {"allowed": true} on success, or
        {"allowed": false, "reason": str, "limit_usd": float, "amount_usd": float};
        plus decision_ref when signed decision evidence is enabled.
    """
    prior = _validated_prior_refs(prior_decision_refs)
    safe_url, url_entities = await asyncio.to_thread(_screen_url, resource_url)
    if url_entities is None:
        # The engine is handed only the redacted URL (its contract, and the way
        # raw PII stays out of its logs). With no redacted URL there is nothing
        # safe to evaluate per-endpoint limits against, so deny rather than
        # check a placeholder that would match no endpoint cap.
        reason = "resource_url screening failed; policy not evaluated"
        _AUDIT.emit(
            "POLICY_BLOCKED",
            resource_url=safe_url,
            amount_usd=amount_usd,
            outcome="blocked",
            error_message=reason,
        )
        return {"allowed": False, "reason": reason, "limit_usd": None, "amount_usd": amount_usd}
    result: dict[str, Any]
    try:
        await asyncio.to_thread(
            _POLICY.check_and_record,
            resource_url=safe_url,
            amount_usd=amount_usd,
        )
        _AUDIT.emit(
            "PAYMENT_ALLOWED",
            resource_url=safe_url,
            amount_usd=amount_usd,
            outcome="allowed",
        )
        result = {"allowed": True}
        verdict = "ALLOW"
    except PolicyViolationError as exc:
        _AUDIT.emit(
            "POLICY_BLOCKED",
            resource_url=safe_url,
            amount_usd=amount_usd,
            outcome="blocked",
            policy_limit_usd=exc.limit_usd,
            error_message=str(exc),
        )
        result = {
            "allowed": False,
            "reason": str(exc),
            "limit_usd": exc.limit_usd,
            "amount_usd": exc.amount_usd,
        }
        verdict = "VIOLATION"
    d_ref = await _record_decision(
        "policy",
        url_entities,
        safe_url,
        policy_verdict=verdict,
        amount=str(amount_usd),
        currency="USD",
        prior_decision_refs=prior,
    )
    if d_ref:
        result["decision_ref"] = d_ref
    return result


@mcp.tool()
async def check_payment_replay(
    resource_url: str,
    pay_to: str,
    amount: str,
    currency: str,
    deadline_seconds: int,
    prior_decision_refs: list[str] | None = None,
) -> dict[str, Any]:
    """Check whether this exact payment has been seen recently (replay protection).

    WARNING: this records the fingerprint. Call exactly once, immediately before
    submitting the payment.

    Cross-process detection requires PRESIDIO_X402_FINGERPRINT_KEY (and
    optionally PRESIDIO_X402_MCP_REDIS_URL); otherwise each MCP server process
    has its own ephemeral in-memory store.

    Args:
        resource_url: x402 resource URL.
        pay_to: Recipient address.
        amount: Amount as string (preserves precision).
        currency: Currency symbol (e.g. "USDC").
        deadline_seconds: Payment deadline as epoch seconds.
        prior_decision_refs: Optional decision_ref values this server returned
            earlier for the same payment; linked into the signed record. Max 8.

    Returns:
        {"is_replay": false, "fingerprint": "<hex>"} on first seen, or
        {"is_replay": true, "fingerprint": "<hex>"} on duplicate;
        plus decision_ref when signed decision evidence is enabled.
    """
    prior = _validated_prior_refs(prior_decision_refs)
    fp = compute_fingerprint(resource_url, pay_to, amount, currency, deadline_seconds)
    safe_url, url_entities = await asyncio.to_thread(_screen_url, resource_url)
    try:
        await asyncio.to_thread(_REPLAY.check_and_record, fp)
        _AUDIT.emit(
            "PAYMENT_ALLOWED",
            resource_url=safe_url,
            outcome="allowed",
            replay_fingerprint=fp,
        )
        is_replay = False
    except ReplayDetectedError:
        _AUDIT.emit(
            "REPLAY_BLOCKED",
            resource_url=safe_url,
            outcome="blocked",
            replay_fingerprint=fp,
        )
        is_replay = True
    result: dict[str, Any] = {"is_replay": is_replay, "fingerprint": fp}
    d_ref = await _record_decision(
        "replay",
        url_entities,
        safe_url,
        replay_verdict="DUPLICATE" if is_replay else "FRESH",
        fingerprint=fp,
        pay_to=pay_to,
        amount=amount,
        currency=currency,
        prior_decision_refs=prior,
    )
    if d_ref:
        result["decision_ref"] = d_ref
    return result


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
