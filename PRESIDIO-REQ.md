# PRESIDIO-REQ — presidio-hardened-x402-mcp

Requirements, feature deliberation, and versioning rationale for the MCP server that exposes [`presidio-hardened-x402`](https://github.com/presidio-v/presidio-hardened-x402) library capabilities to autonomous agents over the Model Context Protocol.

This package is a **thin MCP adapter**. All security primitives live in the parent library; this document specifies how selected primitives are made available over stdio MCP transport. Version `0.3.0` is pinned to parent `presidio-hardened-x402>=0.13.0,<0.14.0` (first release with the `NOT_EVALUATED` control verdict); it keeps the original three-tool MCP surface, adds signed `payment-decision@1` emission from those tools, and does not expose the parent v0.7.0 SLO-payment broker as an MCP tool.

---

## v0.1.0 Requirements (MVP)

### Mandatory MCP tools

1. **`screen_payment_metadata(resource_url, description, reason, entities?)`** — exposes the parent lib's `PIIFilter.scan_payment_fields()` over MCP. Returns redacted strings plus per-field entity counts. No side effects.

2. **`check_payment_policy(resource_url, amount_usd)`** — exposes `PolicyEngine.check_and_record()`. Returns `{allowed: bool, ...}`. Records spend on success; caller must invoke immediately before the actual payment.

3. **`check_payment_replay(resource_url, pay_to, amount, currency, deadline_seconds)`** — exposes `compute_fingerprint()` + `ReplayGuard.check_and_record()`. Returns `{is_replay: bool, fingerprint: hex}`. Records the fingerprint on success.

### Mandatory transport and configuration

4. **Stdio MCP transport** via `mcp.server.mcpserver.MCPServer`. JSON-RPC over stdin/stdout per MCP spec.

5. **Strict stdout discipline.** No `print()` or unguarded writes to stdout (would corrupt JSON-RPC framing). All diagnostic output goes through `logging` (stderr default). Default audit writer is `NullAuditWriter` to eliminate accidental stdout contamination.

6. **Two execution modes:**
   - **In-process (default)** — wraps the local `presidio-hardened-x402` library. No network, no API key, no quota. PII never leaves the agent host.
   - **HTTP-proxy (opt-in)** — when both `PRESIDIO_X402_MCP_REMOTE_BASE_URL` and `PRESIDIO_X402_MCP_REMOTE_API_KEY` are set, tool 1 routes to a configured screening service for centralised audit. On failure, returns a structured `{error, detail, mode: "remote"}` rather than silently falling back.

7. **Env-var configuration.** Every runtime knob is a `PRESIDIO_X402_MCP_*` env var (mode, policy limits, replay TTL, audit path, log level, remote URL/key). MCP host config files (e.g. `claude_desktop_config.json`) carry these via their `env:` block.

8. **Wire-contract parity.** Field-length caps (`resource_url ≤ 2048`, `description ≤ 4096`, `reason ≤ 4096`) and entity-finding shape mirror the screening-api wire contract exactly. A payload accepted in in-process mode is accepted identically by the remote API.

### Scoping decisions (deferred to later versions)

- **TypeScript MCP server.** Python first; TS port deferred until adoption signal warrants the maintenance burden.
  *Rationale: Python matches the parent codebase (no FFI), keeps the test suite shared, and recent MCP-client adoption of `uvx` makes Python install equally smooth.*

- **Endpoint preflight (decoys, dead endpoints, price traps).** Owned by [`x402station-mcp`](https://github.com/sF1nX/x402station-mcp). This MCP composes with x402station, does not replace it.
  *Rationale: Endpoint reputation is a separate problem with a separate network-level moat (every-10-minute probing of all `agentic.market` listings) we cannot reasonably replicate.*

- **Wallet / payment execution.** Owned by Coinbase x402 MCP, MetaMask `mcp-x402`, [`Sardis`](https://github.com/EfeDurmaz16/sardis), and the rest of the payment-execution ecosystem. This MCP screens payloads; it does not sign or send.
  *Rationale: Signing is high-stakes and would massively expand the security surface; not duplicating what others already do well.*

- **Mandate verification / approval workflows.** Owned by Sardis-class governance MCPs (AP2 + spending mandates).
  *Rationale: Spending policy in the parent lib is sufficient for individual agents; mandate/approval workflows are governance-team scope.*

- **Audit-event emission from tools.** Deferred from v0.1.0, when tools did not call `_AUDIT.emit()`; delivered in v0.2.0 (see below).
  *Rationale: Audit semantics at the MCP-call boundary need a design pass — emitting only blocked events would be misleading; emitting allowed events on every call would be noisy without payment-context (the tool sees the check, not the payment that follows).*

---

## v0.2.0 Requirements (post-launch hardening)

Scope driven by post-launch distribution outcomes. Tentative:

- **Delivered:** audit emission from tools. All three tools call `_AUDIT.emit()`, for allowed and blocked outcomes alike: `screen_payment_metadata` emits `PII_REDACTED` (entities found) or `PAYMENT_ALLOWED` in in-process mode, with the already-redacted URL; `check_payment_policy` emits `PAYMENT_ALLOWED` or `POLICY_BLOCKED`; `check_payment_replay` emits `PAYMENT_ALLOWED` or `REPLAY_BLOCKED` with the fingerprint. Remote-mode screening emits no local event. Payment-id correlation remains open.
- Per-call entity-profile override (current `entities` whitelist is per-call but tied to startup `_MODE`; surface more flexibility)
- `mypy --strict` in CI (parent SDLC §6 planned item)
- OpenSSF Scorecard ≥ 7.0 weekly check (parent SDLC §6 supply-chain item)
- HTTP-proxy mode lifecycle improvements: shared `AsyncClient`, connection pooling, lifespan-based cleanup
- Optional TypeScript port — gated on registry install counts from v0.1.0

---

## v0.3.0 Requirements (signed decision evidence)

Founder decision, 2026-10-18: the MCP payment gates must emit signed `payment-decision@1` evidence, not only the HMAC audit log. The audit chain is verifiable only by the holder of `PRESIDIO_X402_CHAIN_KEY`; a signed record is verifiable by anyone holding the public key.

- [x] **Every tool decision emits a signed record.** `screen_payment_metadata` (in-process and successful remote calls), `check_payment_policy` (allow and block) and `check_payment_replay` (fresh and duplicate) each build a `presidio-hardened-x402/payment-decision@1` record with the parent's `build_payment_decision_content` and sign it with `build_decision_evidence`. Records are appended to `PRESIDIO_X402_MCP_DECISION_PATH` (JSON-L, parent `FileDecisionRefWriter`), alongside — never replacing — the HMAC audit log. The tool response carries the `decision_ref`.
- [x] **Reuse, not reimplementation.** Schema, hashing, signing and the verdict function stay in the parent. The MCP maps a tool outcome onto the parent's `ControlResults`: controls the tool ran carry real verdicts, every other control is `NOT_EVALUATED` (parent 0.13.0), so a record never claims a check that did not happen. `policy_version` stays the parent default — with `NOT_EVALUATED` the signed controls block already identifies the gate, and `policy_version` is the policy predicate's version, not a gate label.
- [x] **Screening outcome in every record.** The gates scan the URL they are handed and record the entity-type labels as `PII_WARNED` (seen, not redacted); the screening tool records `PII_REDACTED`. No raw metadata string, fingerprint, or userinfo enters a record.
- [x] **Provenance.** `check_payment_policy` and `check_payment_replay` accept `prior_decision_refs` (max 8, 64-hex), linked into the signed `provenance.prior_decision_refs`. Only refs this process issued are accepted, and the check runs before the gate records state. The tools have no capability chain, so `parents` stays empty and the ADR-0002 top-level `parents` field is never set.
- [x] **No raw URL reaches the parent.** `check_payment_policy` passes only the redacted URL to `PolicyEngine` (the parent's contract); if screening fails it denies without recording spend. A test runs every tool at DEBUG and asserts no raw PII appears in any log record.
- [x] **Key configuration follows the parent.** Key from `PRESIDIO_X402_MCP_EVIDENCE_KEY_FILE` (preferred) or the parent's `PRESIDIO_X402_EVIDENCE_KEY`; `ed25519` (default) or `hmac-sha256` (≥ 32-character secret); signer, key id configurable. The key is probe-signed at startup, held in a field excluded from `repr`, and never logged.
- [x] **Default stays open; strict is opt-in.** No key ⇒ 0.2.x behaviour plus one startup WARNING. `PRESIDIO_X402_MCP_REQUIRE_EVIDENCE_KEY=1` refuses to start unless evidence is fully configured and the key signs. Emission failures after startup are logged and never change a gate's answer.
- [x] **Tests.** Records verify with `verify_decision_ref` for Ed25519 and HMAC keys; no key ⇒ no record + warning; strict mode refuses; key material absent from logs and `repr`. Verified against the parent 0.13.0 release candidate (`feat/not-evaluated-verdict`).

---

## Security Model

This MCP server inherits the parent library's threat model. MCP-specific additions:

| Threat | Mitigation |
|--------|-----------|
| stdout contamination corrupts JSON-RPC frames | No `print()` in production code paths; `NullAuditWriter` default; all logs to stderr via `logging` |
| Env-var-injected secrets leak via process listing | Only `PRESIDIO_X402_MCP_REMOTE_API_KEY` is secret-class; documented as `isSecret: true` in `server.json` so MCP-client UIs can redact in logs |
| Silent fallback hides centralised-audit bypass in HTTP-proxy mode | Remote failure returns structured `{error: ...}` instead of falling back to in-process; the agent must explicitly decide |
| Tool side effects (`check_payment_policy` and `check_payment_replay` record state on every call) misused | Side-effect warnings in tool docstrings, README, `server.json` env-var descriptions, and `SECURITY.md` |
| Oversize payload from a compromised agent stresses the lib | Pre-screen field-length validation (`_validate_lengths`) rejects with `ValueError` before the lib is touched |
| Compromised remote screening service injects fake redacted output | Out of scope — operator must verify TLS configuration and audit policy of the configured remote |
| Gate decisions disputed after the fact; HMAC audit chain not third-party verifiable | Signed `payment-decision@1` records (v0.3.0), verified offline with the parent's `verify_decision_ref`; strict mode `PRESIDIO_X402_MCP_REQUIRE_EVIDENCE_KEY` |
| Decision-signing key leaks via logs or env listing | Key file preferred (warning if group/world-readable); key excluded from `repr`; startup and emission errors log the exception type only |
| Agent forges provenance links in a signed record | `prior_decision_refs` accepted only if this process issued them; validated before any gate state is recorded |
| Parent v0.7.0 SLO broker misinterpreted as an MCP payment tool | Not exposed in this MCP release; agents must use the parent Python API and verified `ArchTranslucencyAdapter` path for signed degradation evidence |

See the parent lib's [SECURITY.md](https://github.com/presidio-v/presidio-hardened-x402/blob/main/SECURITY.md) and [PRESIDIO-REQ.md](https://github.com/presidio-v/presidio-hardened-x402/blob/main/PRESIDIO-REQ.md) for the library-level threat model and full set of security controls.

---

## Design Principles

- **Thin adapter, not a reimplementation.** All security logic lives in `presidio-hardened-x402`; this package exposes it, never re-derives it.
- **Stdio discipline.** stdout is reserved for JSON-RPC. Every code path that could write to stdout is removed or routed via `logging` (stderr).
- **No silent fallback.** Failure modes are surfaced as structured tool output. The agent decides what to do.
- **Composition over replacement.** Pairs cleanly with `x402station-mcp` (endpoint safety), payment-execution MCP servers, and governance MCP servers — does not duplicate their surfaces.
- **Zero-config default.** Works with no env vars set (regex mode, no policy, in-memory replay, NullAuditWriter). Configuration is opt-in escalation.
- **Wire-contract parity.** What the in-process tool accepts and returns is identical to the screening-api wire contract. Mode is a transport detail, not a semantic difference.

---

## SDLC

This repository is developed under the Presidio hardened-family SDLC:
<https://github.com/presidio-v/presidio-hardened-docs/blob/main/sdlc/sdlc-report.md>.
