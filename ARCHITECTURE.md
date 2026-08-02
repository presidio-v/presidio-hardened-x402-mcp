# Architecture

This document describes the high-level design of `presidio-hardened-x402-mcp`: its
components, how data flows through them, and the trust boundaries the project is
built to enforce. For the security requirements and threat model that motivate
this design, see [SECURITY.md](SECURITY.md) and the assurance case in
[ASSURANCE.md](ASSURANCE.md).

## Overview

`presidio-hardened-x402-mcp` is a **stdio MCP server** that exposes the pre-payment
safety controls of the [`presidio-hardened-x402`](https://github.com/presidio-v/presidio-hardened-x402)
library as three tools an autonomous agent can call before committing to an x402
payment: PII screening of payment metadata, a spending-policy gate, and a
duplicate-payment gate. It is deliberately a **thin adapter** — detection, policy,
replay and audit logic all live in the parent library, and this package's job is to
expose them over JSON-RPC without weakening them. It is **stateful** (two of the
three tools record on call) and makes **no network calls by default**; an optional
HTTP-proxy mode routes screening to a remote service. The design stance that shapes
everything else: **an agent must always be able to tell what actually happened** —
no tool silently degrades to a weaker check.

## Components

| Component | Responsibility |
|---|---|
| `server.py` — startup wiring | Reads configuration from environment variables and constructs the singletons: `PolicyEngine`, `ReplayGuard`, `AuditLog`, and the optional remote-mode settings. Validation that must fail closed happens here, at import, not at first call. |
| `server.py` — `_validate_remote_base_url` | TLS gate on the remote screening endpoint. Refuses any non-`https` base URL except loopback, and raises rather than downgrading to local screening. |
| `server.py` — `_validate_lengths` | Wire-contract field-length limits (2048 / 4096 / 4096), mirroring `screening-api`'s request model so both entry points reject the same oversized input. |
| `server.py` — `_scan_in_process` | Default screening path. Builds a per-call `PIIFilter` so the per-call entity allowlist is honoured without coupling every caller to one shared filter. |
| `server.py` — `_scan_remote` | HTTP-proxy screening path. Calls `/v1/screen` on the configured host and returns a structured error discriminator on failure — never a silent fallback. |
| `server.py` — `_collapse` | Reduces per-field entity hits to counts, preserving which field each finding came from. Mirrors `screening_api.screening._collapse`. |
| The three `@mcp.tool` functions | `screen_payment_metadata` (no side effects), `check_payment_policy` (**records spend**), `check_payment_replay` (**records the fingerprint**). |
| Parent library `presidio_x402.*` | All actual security logic: PII detection and redaction, policy arithmetic, replay fingerprinting, the HMAC audit chain. Out of scope for this repo's audits by design. |

## Data / processing flow

A tool call moves through the server as follows:

1. **Arguments arrive** over stdio JSON-RPC from the MCP client.
2. **Length validation** (`_validate_lengths`) rejects oversized fields before any
   further work.
3. **The tool's control runs** — screening (in-process or remote), the policy gate,
   or the replay gate.
4. **Side effects are recorded** for tools 2 and 3: policy records the spend, replay
   records the fingerprint. Tool 1 has none.
5. **An audit event is written** through the parent `AuditLog`.
6. **A structured result** returns to the caller.

Two properties are load-bearing and part of the contract:

- **Failures are visible, not absorbed.** Remote screening never falls back to
  in-process on error; it returns `{"error": "auth_error" | "rate_limit" |
  "unavailable", "mode": "remote"}` so the agent can tell that centralized audit was
  bypassed. A misconfigured endpoint stops the server at startup.
- **Tools 2 and 3 record on call.** They are gates, not queries: calling them
  consumes budget and burns a fingerprint. This is why they never run remotely — a
  network failure mid-gate would leave the recorded state ambiguous.

## Trust boundaries

| Boundary | Kind | Control |
|---|---|---|
| **MCP client → server** | Input validation | Tool arguments are untrusted. Field lengths are capped before processing; metadata is then screened by the parent `PIIFilter`. This is the primary validation boundary. |
| **Operator environment → server** | Configuration | Env vars are trusted-but-fallible: they come from a human, so typos are the expected failure. The remote base URL is TLS-validated at import; malformed policy JSON degrades to an empty policy with an error log rather than propagating. |
| **Server → remote screening API** | Egress | Carries **pre-redaction** metadata and a long-lived API key, making it the most sensitive egress in the project. `https` is mandatory (loopback excepted), certificates are verified by default, requests are time-boxed, and failure is reported rather than hidden. |
| **Server → stdout** | Egress (integrity) | stdout *is* the JSON-RPC frame channel. Anything written there corrupts the protocol, so all diagnostics go through `logging` to stderr. |
| **Server → audit sink / Redis** | Egress (persistence) | Audit records are written through the parent `AuditLog` with its HMAC chain; the replay store is optionally Redis. Both are operator-configured and inherit the parent library's guarantees. |

Out of scope by contract rather than omission: the parent library's detection
accuracy and cryptography (see [SECURITY.md](SECURITY.md)), custody of the keys
supplied through the environment, and the downstream payment rail itself.
