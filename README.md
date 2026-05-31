# presidio-hardened-x402-mcp

Pre-payment PII screener for x402 — agents call `screen_payment_metadata(...)` before signing, catching emails, SSNs, phone numbers, names, and other personal data in payment metadata before it reaches the merchant.

Part of the [`presidio-hardened-*`](https://github.com/presidio-v) toolkit family. Thin MCP (Model Context Protocol) adapter over the [`presidio-hardened-x402`](https://pypi.org/project/presidio-hardened-x402/) library.

## Why this exists

x402 agentic payments routinely carry user-supplied free text — descriptions, memos, query-string parameters — straight through to merchants and facilitators. When an LLM agent generates that text, it can include PII the user never intended to share. Once the merchant logs it, retention is their decision, not yours.

This MCP server gives agents a one-call gate to screen and redact PII *before* the payment leaves the agent host. Three tools, designed to compose with payment-execution and endpoint-safety MCP servers (x402station, Coinbase x402, Sardis, ...).

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
| `PRESIDIO_X402_MCP_REMOTE_BASE_URL` | Enable HTTP-proxy mode for tool 1 — see Modes | unset |
| `PRESIDIO_X402_MCP_REMOTE_API_KEY` | API key for the remote screening service | unset |
| `PRESIDIO_X402_FINGERPRINT_KEY` | 32-byte hex key for cross-process replay detection | unset (per-process) |
| `PRESIDIO_X402_CHAIN_KEY` | 32-byte hex key for cross-process audit-chain HMAC | unset (per-process) |

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

`entities` (optional list of Presidio entity types) narrows detection to a whitelist. Field-length caps mirror the v0.4.0 wire contract: `resource_url ≤ 2048`, `description ≤ 4096`, `reason ≤ 4096` characters. Oversized inputs raise `ValueError`.

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

## Notes for developers

- Logs go to stderr (MCP clients capture stderr). stdout is reserved for JSON-RPC frames.
- The package is a thin adapter. All security logic lives in [`presidio-hardened-x402`](https://pypi.org/project/presidio-hardened-x402/) — read its docs for the entity-type catalog, policy semantics, and audit-chain details.
- When testing via `mcp-inspector --cli`, bare numeric `--tool-arg amount=1.50` is auto-coerced to a float and rejected by the schema. Real MCP clients send proper JSON types; the tool's `amount` argument is a string to preserve precision.
- Local dev: `uv venv && uv pip install -e ".[dev]" && pytest tests/`.

## License

MIT. See [LICENSE](LICENSE).

## Links

- This repo: https://github.com/presidio-v/presidio-hardened-x402-mcp
- Issues: https://github.com/presidio-v/presidio-hardened-x402-mcp/issues
- Parent library: https://github.com/presidio-v/presidio-hardened-x402
- Library on PyPI: https://pypi.org/project/presidio-hardened-x402/
- MCP spec: https://modelcontextprotocol.io
- x402: https://x402.org
