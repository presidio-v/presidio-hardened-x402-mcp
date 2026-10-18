# presidio-hardened-x402-mcp

[![PyPI version](https://img.shields.io/pypi/v/presidio-hardened-x402-mcp.svg)](https://pypi.org/project/presidio-hardened-x402-mcp/)
[![Python](https://img.shields.io/pypi/pyversions/presidio-hardened-x402-mcp.svg)](https://pypi.org/project/presidio-hardened-x402-mcp/)
[![GitHub release](https://img.shields.io/github/v/release/presidio-v/presidio-hardened-x402-mcp.svg)](https://github.com/presidio-v/presidio-hardened-x402-mcp/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![CI](https://github.com/presidio-v/presidio-hardened-x402-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/presidio-v/presidio-hardened-x402-mcp/actions/workflows/ci.yml)
[![OpenSSF Scorecard](https://api.scorecard.dev/projects/github.com/presidio-v/presidio-hardened-x402-mcp/badge)](https://scorecard.dev/viewer/?uri=github.com/presidio-v/presidio-hardened-x402-mcp)
[![OpenSSF Best Practices](https://www.bestpractices.dev/projects/13930/badge)](https://www.bestpractices.dev/projects/13930)

<!-- mcp-name: io.github.presidio-v/presidio-hardened-x402-mcp -->

Pre-payment safety gate for x402 — agents call `screen_payment_metadata(...)`, `check_payment_policy(...)`, and `check_payment_replay(...)` before signing, catching PII, budget overruns, and duplicate payments before metadata or money leaves the agent host.

Part of the [`presidio-hardened-*`](https://github.com/presidio-v) toolkit family. Thin MCP (Model Context Protocol) adapter over the [`presidio-hardened-x402`](https://pypi.org/project/presidio-hardened-x402/) library, pinned for parent `0.11.x`–`0.12.x` compatibility (`presidio-hardened-x402>=0.11.1,<0.13.0`). The `>=0.11.1` floor is a security floor, not a preference — it is the release that closed the percent-encoded PII redaction bypass.

## Why this exists

x402 agentic payments routinely carry user-supplied free text — descriptions, memos, query-string parameters — straight through to merchants and facilitators. When an LLM agent generates that text, it can include PII the user never intended to share. Once the merchant logs it, retention is their decision, not yours.

This MCP server gives agents a small default-deny gate *before* payment leaves the agent host. Three tools expose the parent library's stable pre-payment controls: PII redaction, spending policy, and replay detection. Since 0.3.0 each decision can also be emitted as a signed `payment-decision@1` record that a third party verifies offline (see [Signed decision evidence](#signed-decision-evidence)). The tools are designed to compose with payment-execution and endpoint-safety MCP servers ([x402station](https://github.com/sF1nX/x402station-mcp), Coinbase x402, Sardis, ...), while other parent-library surfaces — `evidence-ref@1` verification of inbound evidence, the v0.9.1 SLO broker, the v0.10.0 `settlement-ref@1` treasury binding, and the v0.11.0 `CapabilityEnforcer` — stay in the Python library unless an MCP tool explicitly wraps them later.

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
| `PRESIDIO_X402_MCP_EVIDENCE_KEY_FILE` | File holding the decision-signing key (preferred; wins over the env key) | unset |
| `PRESIDIO_X402_EVIDENCE_KEY` | Decision-signing key (the parent library's variable): Ed25519 private key as 64 hex chars, or an HMAC secret | unset |
| `PRESIDIO_X402_MCP_DECISION_PATH` | Append-only JSON-L file for signed `payment-decision@1` records | unset |
| `PRESIDIO_X402_MCP_EVIDENCE_ALGORITHM` | `ed25519` or `hmac-sha256` | `ed25519` |
| `PRESIDIO_X402_MCP_EVIDENCE_SIGNER` | Signer identity; the trust-store key verifiers look up | `presidio-hardened-x402-mcp` |
| `PRESIDIO_X402_MCP_EVIDENCE_KEY_ID` | Optional key id written into each record (for rotation) | unset |
| `PRESIDIO_X402_MCP_REQUIRE_EVIDENCE_KEY` | Fail startup unless signed evidence is fully configured and the key signs | unset |

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
  // + "decision_ref": "<64 hex>" when signed decision evidence is enabled
}
```

`entities` (optional list of Presidio entity types) narrows detection to a whitelist. Field-length caps mirror the screening-api wire contract that remains stable through parent `0.7.x`: `resource_url ≤ 2048`, `description ≤ 4096`, `reason ≤ 4096` characters. Oversized inputs raise `ValueError`.

### `check_payment_policy(resource_url, amount_usd, prior_decision_refs?)`

Spending-policy gate. **Records the spend on success** — call exactly once, immediately before payment. Skipping the actual payment after a successful check inflates the daily-limit ledger until the window rolls over.

```jsonc
// Input
{ "resource_url": "https://api.foo.com/x", "amount_usd": 1.50 }

// Output (allowed)
{ "allowed": true }

// Output (denied — over per-call limit of $5.00)
{ "allowed": false, "reason": "...", "limit_usd": 5.00, "amount_usd": 6.00 }
```

With signed evidence enabled, both outputs also carry `decision_ref`. `prior_decision_refs` (optional, up to 8) links refs this server returned earlier for the same payment — typically the one from `screen_payment_metadata` — into the signed record; a ref this process did not issue is refused before any spend is recorded.

### `check_payment_replay(resource_url, pay_to, amount, currency, deadline_seconds, prior_decision_refs?)`

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

`decision_ref` and `prior_decision_refs` behave as for `check_payment_policy`.

## Signed decision evidence

The audit log (`PRESIDIO_X402_MCP_AUDIT_PATH`) is HMAC-chained: tamper-evident to whoever holds `PRESIDIO_X402_CHAIN_KEY`, and to nobody else. From 0.3.0 every tool decision — allow and block alike — can also be written as a signed [`payment-decision@1`](https://github.com/presidio-v/presidio-hardened-x402#decision-ref-emission-payment-decision1) record, built and signed by the parent library (`build_payment_decision_content`, `build_decision_evidence`) and checked by anyone with the public key (`verify_decision_ref`). The audit log is still written; the records go alongside it, never instead of it.

```bash
# One-time: an Ed25519 key pair for the signer (hex private key, 0600).
python - <<'PY'
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
sk = Ed25519PrivateKey.generate()
open("evidence.key", "w").write(sk.private_bytes_raw().hex())
print(sk.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw).hex())  # -> trust store
PY
chmod 600 evidence.key
```

```json
"env": {
  "PRESIDIO_X402_MCP_EVIDENCE_KEY_FILE": "/etc/presidio/evidence.key",
  "PRESIDIO_X402_MCP_DECISION_PATH": "/var/log/presidio/x402-mcp-decisions.jsonl",
  "PRESIDIO_X402_MCP_REQUIRE_EVIDENCE_KEY": "1"
}
```

Verify offline with the parent's CLI against a trust store that pins the public key under the signer name:

```bash
echo '{"presidio-hardened-x402-mcp": {"alg": "ed25519", "public_key": "<public hex>"}}' > trust.json
python -m presidio_x402.decision_ref /var/log/presidio/x402-mcp-decisions.jsonl trust.json
```

**Without a key** the server behaves exactly as 0.2.x — audit log only — and logs one WARNING at startup saying signed evidence is disabled. A key without `PRESIDIO_X402_MCP_DECISION_PATH`, an unreadable key file, or a key the signer rejects is logged at ERROR and also leaves evidence off. Set `PRESIDIO_X402_MCP_REQUIRE_EVIDENCE_KEY=1` to refuse to start in any of those cases instead. Once running, a failed write is logged and the gate's answer stands: a record of a decision never reverses the decision.

**What a record says.** Each tool evaluates one control, but `payment-decision@1` always carries all five (`pii → trusted_wallet → policy → replay → mpa`). The control the tool evaluated holds its real verdict; the others carry the schema's pass values. The signed `policy_version` names the gate — `presidio-x402-mcp.screen.v1`, `.policy.v1`, or `.replay.v1` — so read a record as *that gate's* decision, not as proof that every control ran. Chain the three with `prior_decision_refs` to get one linked set per payment.

**What it never contains.** Raw `resource_url`, `description`, or `reason`; only the URL's scheme and host, the entity-type labels found, and hashes (policy snapshot, replay fingerprint, payment details). The gates see PII in the URL they are handed but pay it unchanged, so their PII verdict is `PII_WARNED`; `screen_payment_metadata` returns redacted strings and records `PII_REDACTED`. Fields an MCP tool never sees — payer wallet, network, the raw 402 offer — are recorded as `unspecified` / `not-presented`. The records carry no capability-chain `parents`, so they are identical on parent 0.12.2 and on later releases that add the top-level ADR-0002 `parents` field.

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

**What none of these gates can see: a request body the agent made up.** The three tools screen the 402 challenge's metadata and the spend; they never see the body the agent sends to a POST route. Independent measurement of the x402 and MPP catalogues (probe402, MCRI #001, 1 September 2026) found 1,521 of 8,056 listed POST routes — 18.9% — publish no usable request example, and 72% of those still return a payable quote at the wall. A route like that is *listed*, *priced*, and *not machine-executable from the published contract*. An agent that fills the gap by synthesising a body is guessing, and a guessed body is where user data enters the request unscreened. Posture: if the catalogue entry carries no request example or schema, stop at the 402 quote and surface it; do not invent a body to get past the wall. Put that rule in the agent's instructions — it is a decision the agent makes before any of these tools run.

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
- This MCP release exposes the same three tools as `0.1.1`. 0.3.0 adds signed `payment-decision@1` emission from those tools and an optional `prior_decision_refs` argument on the two gates; the rest of the parent SLO/evidence/capability surface is not promoted into MCP.
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

This repository is on the **open-source baseline** of the PRESIDIO hardened-family SDLC
([report](https://github.com/presidio-v/presidio-hardened-docs/blob/main/sdlc/sdlc-report.md) ·
[PDF](https://github.com/presidio-v/presidio-hardened-docs/blob/main/sdlc/sdlc-report.pdf)).
The controls measured for it, and any open gaps, are its row in the
[applicability matrix](https://github.com/presidio-v/presidio-hardened-docs/blob/main/sdlc/applicability.md).

## Roadmap (next 12 months)

- **Now / in flight** — OpenSSF Best Practices **silver** and a Scorecard above 7:
  governance docs, a real CodeQL job alongside Bandit, least-privilege workflow
  tokens, and Atheris fuzzing of the configuration validators. Closing the
  remaining findings in [`SECURITY-AUDIT.md`](SECURITY-AUDIT.md).
- **Next** — hash-pinned CI dependencies, ideally as a family-wide change rather than in
  this repo alone.
- **Later** *(under evaluation)* — signed releases with build provenance; tracking
  the MCP specification as it stabilises; exposing the parent library's
  `capability-grant@1` enforcement as a fourth tool, if agent demand justifies the
  added surface.

## Governance, Architecture, Security

- [Governance](GOVERNANCE.md) — roles, decision process, and how to become a maintainer.
- [Architecture](ARCHITECTURE.md) — components, trust boundaries, and the core processing path.
- [Assurance case](ASSURANCE.md) — the security claims and the evidence backing each one.
- [Security policy](SECURITY.md) — supported versions and how to report a vulnerability.
- [Contributing](CONTRIBUTING.md) — review bar, test policy, and verification commands.
- [Stability guarantees](SEMVER.md) — what counts as the public API and what may not change.
