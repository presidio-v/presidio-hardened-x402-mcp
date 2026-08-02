# presidio-hardened-x402-mcp

[![PyPI version](https://img.shields.io/pypi/v/presidio-hardened-x402-mcp.svg)](https://pypi.org/project/presidio-hardened-x402-mcp/)
[![Python](https://img.shields.io/pypi/pyversions/presidio-hardened-x402-mcp.svg)](https://pypi.org/project/presidio-hardened-x402-mcp/)
[![GitHub release](https://img.shields.io/github/v/release/presidio-v/presidio-hardened-x402-mcp.svg)](https://github.com/presidio-v/presidio-hardened-x402-mcp/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![CI](https://github.com/presidio-v/presidio-hardened-x402-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/presidio-v/presidio-hardened-x402-mcp/actions/workflows/ci.yml)

<!-- mcp-name: io.github.presidio-v/presidio-hardened-x402-mcp -->

Pre-payment safety gate for x402 — agents call `screen_payment_metadata(...)`, `check_payment_policy(...)`, and `check_payment_replay(...)` before signing, catching PII, budget overruns, and duplicate payments before metadata or money leaves the agent host.

Part of the [`presidio-hardened-*`](https://github.com/presidio-v) toolkit family. Thin MCP (Model Context Protocol) adapter over the [`presidio-hardened-x402`](https://pypi.org/project/presidio-hardened-x402/) library, pinned for parent `0.9.x` compatibility (`presidio-hardened-x402>=0.9.1,<0.10.0`).

## Why this exists

x402 agentic payments routinely carry user-supplied free text — descriptions, memos, query-string parameters — straight through to merchants and facilitators. When an LLM agent generates that text, it can include PII the user never intended to share. Once the merchant logs it, retention is their decision, not yours.

This MCP server gives agents a small default-deny gate *before* payment leaves the agent host. Three tools expose the parent library's stable pre-payment controls: PII redaction, spending policy, and replay detection. They are designed to compose with payment-execution and endpoint-safety MCP servers ([x402station](https://github.com/sF1nX/x402station-mcp), Coinbase x402, Sardis, ...), while newer parent-library surfaces such as `evidence-ref@1` verification and the v0.9.1 SLO broker stay in the Python library unless an MCP tool explicitly wraps them later.

## Install & configure

Requires Python ≥ 3.10. Distributed on PyPI; recommended invocation via `uvx` (no global install).

### Claude Desktop / Claude Code

Add to `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) or the equivalent on your platform:

```json
{
  "mcpServers": {
    "presidio-x402": {
      "command": "uvx",
      "args": ["presidio-hardened-x402-mcp"]
    }
  }
}
```

### Cursor / Windsurf / Continue

Same shape — every MCP host accepts `command` / `args` / `env`. See your editor's MCP-server docs for the config-file path.

### Environment variables

All optional. Defaults give a zero-config in-process mode with no quota, no network, and no PII storage.

| Variable | Purpose | Default |
|---|---|---|
| `PRESIDIO_X402_MCP_MODE` | `regex` (zero-setup) or `nlp` (needs `[nlp]` extra + a spaCy model) | `regex` |
| `PRESIDIO_X402_MCP_MAX_PER_CALL_USD` | Max USD per single payment (policy gate) | unset → no limit |
| `PRESIDIO_X402_MCP_DAILY_LIMIT_USD` | Max USD per rolling window (policy gate) | unset → no limit |
| `PRESIDIO_X402_MCP_PER_ENDPOINT_JSON` | Per-endpoint cap, e.g. `'{"api.foo.com": 5.00}'` | unset |
| `PRESIDIO_X402_MCP_WINDOW_SECONDS` | Rolling window for the daily limit | `86400` |
| `PRESIDIO_X402_MCP_AGENT_ID` | Label written into audit records | unset |
| `PRESIDIO_X402_MCP_REPLAY_TTL` | Fingerprint cache TTL (seconds) | `300` |
| `PRESIDIO_X402_MCP_REDIS_URL` | Use Redis for replay state instead of in-memory | unset |
| `PRESIDIO_X402_MCP_AUDIT_PATH` | Append-only JSON-L audit log path; omit to disable | unset |
| `PRESIDIO_X402_MCP_LOG_LEVEL` | `DEBUG` / `INFO` / `WARNING` / `ERROR` | `INFO` |
| `PRESIDIO_X402_MCP_REMOTE_BASE_URL` | Enable HTTP-proxy mode for tool 1 — see Modes. Must be `https://`; plain `http://` is accepted only for loopback and otherwise refuses to start | unset |
| `PRESIDIO_X402_MCP_REMOTE_API_KEY` | API key for the remote screening service | unset |
| `PRESIDIO_X402_FINGERPRINT_KEY` | 32-byte hex key for cross-process replay detection | unset (per-process) |
| `PRESIDIO_X402_CHAIN_KEY` | 32-byte hex key for cross-process audit-chain HMAC | unset (per-process) |
| `PRESIDIO_X402_REQUIRE_FINGERPRINT_KEY` | Fail startup if replay key is absent or invalid | unset |
| `PRESIDIO_X402_REQUIRE_CHAIN_KEY` | Fail startup if audit-chain key is absent or invalid | unset |

Generate cross-process keys with `openssl rand -hex 32`.

## Tools

### `screen_payment_metadata(resource_url, description, reason, entities?)`

Detects and redacts PII in payment metadata. **No side effects** — safe to call repeatedly.

```jsonc
// Input
{
  "resource_url": "https://api.foo.com/u/jane@example.com",
  "description": "monthly fee for jane@example.com",
  "reason": ""
}

// Output
{
  "redacted_resource_url": "https://api.foo.com/u/<EMAIL_ADDRESS>",
  "redacted_description": "monthly fee for <EMAIL_ADDRESS>",
  "redacted_reason": "",
  "entities_found": [
    { "entity_type": "EMAIL_ADDRESS", "field": "resource_url", "count": 1 },
    { "entity_type": "EMAIL_ADDRESS", "field": "description", "count": 1 }
  ],
  "mode": "in_process"
}
```

`entities` (optional list of Presidio entity types) narrows detection to a whitelist. Field-length caps mirror the screening-api wire contract that remains stable through parent `0.7.x`: `resource_url ≤ 2048`, `description ≤ 4096`, `reason ≤ 4096` characters. Oversized inputs raise `ValueError`.

### `check_payment_policy(resource_url, amount_usd)`

Spending-policy gate. **Records the spend on success** — call exactly once, immediately before payment. Skipping the actual payment after a successful check inflates the daily-limit ledger until the window rolls over.

```jsonc
// Input
{ "resource_url": "https://api.foo.com/x", "amount_usd": 1.50 }

// Output (allowed)
{ "allowed": true }

// Output (denied — over per-call limit of $5.00)
{ "allowed": false, "reason": "...", "limit_usd": 5.00, "amount_usd": 6.00 }
```

### `check_payment_replay(resource_url, pay_to, amount, currency, deadline_seconds)`

Duplicate-payment gate via HMAC-SHA256 fingerprint of the canonical fields. **Records the fingerprint on success** — call exactly once, immediately before payment.

`amount` is a **string** to preserve precision. Cross-process detection requires `PRESIDIO_X402_FINGERPRINT_KEY` (and optionally `PRESIDIO_X402_MCP_REDIS_URL`); otherwise each MCP server process keeps its own in-memory store.

```jsonc
// Input
{
  "resource_url": "https://api.foo.com/x",
  "pay_to": "0xabc...",
  "amount": "1.50",
  "currency": "USDC",
  "deadline_seconds": 1700000000
}

// Output (first seen)
{ "is_replay": false, "fingerprint": "29aaf60f..." }

// Output (duplicate within TTL)
{ "is_replay": true, "fingerprint": "29aaf60f..." }
```

## Modes

**In-process (default).** Wraps the local `presidio-hardened-x402` library in the same process as the MCP server. No network, no API key, no quota. PII never leaves the agent host. Use this unless you have a specific reason not to.

**HTTP-proxy.** When both `PRESIDIO_X402_MCP_REMOTE_BASE_URL` and `PRESIDIO_X402_MCP_REMOTE_API_KEY` are set, `screen_payment_metadata` calls `/v1/screen` on the configured host (e.g. `https://screen.presidio-group.eu`) for centralized audit. On auth / quota / network failure, returns a structured `{ "error": "auth_error" | "rate_limit" | "unavailable", "detail": ..., "mode": "remote" }` — never silently falls back to in-process. Tools 2 and 3 always stay in-process.

## Composability

Designed to slot into agent flows alongside payment-execution and endpoint-safety MCP servers:

```
agent intent: pay https://api.foo.com/x with 1.50 USDC
    │
    ├─ x402station    preflight(url)            ← is the ENDPOINT safe? (decoys, dead, traps)
    │
    ├─ presidio-x402  screen_payment_metadata   ← is the PAYLOAD safe? (PII)
    ├─ presidio-x402  check_payment_policy      ← within budget?
    ├─ presidio-x402  check_payment_replay      ← not a duplicate?
    │
    └─ pay()
```

`screen_payment_metadata` is read-only and safe to interleave anywhere. The policy and replay gates record state on call — sequence them immediately before payment.

### Combined snippet: preflight → screen → pay

Endpoint-safety and payload-safety are independent signals — calling both is what you actually want before signing. Configure the two MCP servers side-by-side:

```json
{
  "mcpServers": {
    "x402station":   { "command": "npx", "args": ["-y", "x402station-mcp"],
                       "env": { "AGENT_PRIVATE_KEY": "0x…" } },
    "presidio-x402": { "command": "uvx", "args": ["presidio-hardened-x402-mcp"] }
  }
}
```

Agent flow before signing a payment (pseudocode — each step is one MCP tool call):

```python
# 1. endpoint safety: is the URL trustworthy? (x402station-mcp)
pf = preflight(url)
if not pf["ok"]:
    abort(reason=pf["warnings"])  # decoy / zombie / dead / price-trap

# 2. payload safety: redact PII before it leaves the host (presidio-x402)
s = screen_payment_metadata(resource_url=url, description=description, reason="")
url, description = s["redacted_resource_url"], s["redacted_description"]

# 3. spend gates: record-on-success, call exactly once each (presidio-x402)
if not check_payment_policy(url, amount_usd)["allowed"]:
    abort(reason="policy")
if check_payment_replay(url, pay_to, amount, currency, deadline_seconds)["is_replay"]:
    abort(reason="replay")

# 4. sign + pay
pay(url, amount, description=description)
```

The two servers are developed independently, on purpose — keeping the signals uncorrelated is the point. See [x402station-mcp](https://github.com/sF1nX/x402station-mcp) for the preflight tool's full output schema and warning catalog.

## Notes for developers

- Logs go to stderr (MCP clients capture stderr). stdout is reserved for JSON-RPC frames.
- The package is a thin adapter. All security logic lives in [`presidio-hardened-x402`](https://pypi.org/project/presidio-hardened-x402/) — read its docs for the entity-type catalog, policy semantics, evidence-ref verification, SLO broker, and audit-chain details.
- This MCP release intentionally exposes the same three tools as `0.1.1`; the compatibility update is dependency and metadata alignment with parent `0.7.x`, not a promotion of the full parent SLO/evidence surface into MCP.
- When testing via `mcp-inspector --cli`, bare numeric `--tool-arg amount=1.50` is auto-coerced to a float and rejected by the schema. Real MCP clients send proper JSON types; the tool's `amount` argument is a string to preserve precision.
- Local dev: `uv venv && uv pip install -e ".[dev]" && pytest tests/`.

## License

MIT. See [LICENSE](LICENSE).

## Links

- This repo: https://github.com/presidio-v/presidio-hardened-x402-mcp
- Issues: https://github.com/presidio-v/presidio-hardened-x402-mcp/issues
- Parent library: https://github.com/presidio-v/presidio-hardened-x402
- Library on PyPI: https://pypi.org/project/presidio-hardened-x402/
- Requirements: [PRESIDIO-REQ.md](PRESIDIO-REQ.md)
- Security policy: [SECURITY.md](SECURITY.md)
- MCP spec: https://modelcontextprotocol.io
- x402: https://x402.org

---

## SDLC

This repository is developed under the Presidio hardened-family SDLC:
<https://github.com/presidio-v/presidio-hardened-docs/blob/main/sdlc/sdlc-report.md>.
