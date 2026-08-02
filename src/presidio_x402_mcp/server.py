"""FastMCP server for presidio-hardened-x402 — PII screening for x402 agents.

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
from typing import Any
from urllib.parse import urlparse

import httpx
from mcp.server.fastmcp import FastMCP
from presidio_x402 import (
    AuditLog,
    FileAuditWriter,
    NullAuditWriter,
    PIIFilter,
    PolicyConfig,
    PolicyEngine,
    ReplayGuard,
)
from presidio_x402.exceptions import PolicyViolationError, ReplayDetectedError
from presidio_x402.replay_guard import compute_fingerprint

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

mcp = FastMCP("presidio-x402")


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
        and mode (one of "in_process", "remote").
        On remote failure: dict with keys error (one of "auth_error",
        "rate_limit", "unavailable"), detail, optional retry_after (for
        rate_limit), and mode ("remote").
    """
    _validate_lengths(resource_url, description, reason)
    if _REMOTE_ENABLED:
        return await _scan_remote(resource_url, description, reason, entities)
    url, desc, reason_out, findings = await asyncio.to_thread(
        _scan_in_process,
        resource_url,
        description,
        reason,
        entities,
    )
    return {
        "redacted_resource_url": url,
        "redacted_description": desc,
        "redacted_reason": reason_out,
        "entities_found": findings,
        "mode": "in_process",
    }


@mcp.tool()
async def check_payment_policy(resource_url: str, amount_usd: float) -> dict[str, Any]:
    """Check whether a payment is allowed by the configured spending policy.

    WARNING: this records the spend against rolling time-window ledgers.
    Call exactly once, immediately before submitting the payment. If you call
    this and then do not pay, the spend window will be inflated until it rolls
    over.

    Configure limits at server startup via PRESIDIO_X402_MCP_* env vars.

    Args:
        resource_url: x402 resource URL being paid (used for per-endpoint limits).
        amount_usd: Payment amount in USD-equivalent.

    Returns:
        {"allowed": true} on success, or
        {"allowed": false, "reason": str, "limit_usd": float, "amount_usd": float}.
    """
    try:
        await asyncio.to_thread(
            _POLICY.check_and_record,
            resource_url=resource_url,
            amount_usd=amount_usd,
        )
        return {"allowed": True}
    except PolicyViolationError as exc:
        return {
            "allowed": False,
            "reason": str(exc),
            "limit_usd": exc.limit_usd,
            "amount_usd": exc.amount_usd,
        }


@mcp.tool()
async def check_payment_replay(
    resource_url: str,
    pay_to: str,
    amount: str,
    currency: str,
    deadline_seconds: int,
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

    Returns:
        {"is_replay": false, "fingerprint": "<hex>"} on first seen, or
        {"is_replay": true, "fingerprint": "<hex>"} on duplicate.
    """
    fp = compute_fingerprint(resource_url, pay_to, amount, currency, deadline_seconds)
    try:
        await asyncio.to_thread(_REPLAY.check_and_record, fp)
        return {"is_replay": False, "fingerprint": fp}
    except ReplayDetectedError:
        return {"is_replay": True, "fingerprint": fp}


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
