# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| 0.1.x   | ✓ (current) |

## Reporting a Vulnerability

Please report security vulnerabilities by opening a private GitHub Security Advisory
(via the "Security" tab → "Report a vulnerability") rather than a public issue.

Include:

- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

You will receive an acknowledgement within 5 business days. We aim to release a patch
within 30 days of a confirmed vulnerability.

## Scope

This repository is a thin MCP adapter over [`presidio-hardened-x402`](https://github.com/presidio-v/presidio-hardened-x402). Security controls (PII redaction, spending policy, replay detection, audit logging, evidence-ref verification, and SLO-payment authorization) are implemented in the parent library — see its [SECURITY.md](https://github.com/presidio-v/presidio-hardened-x402/blob/main/SECURITY.md) for the library-level threat model.

In-scope for this repo:

- The MCP server itself (transport, tool registration, env-var configuration, HTTP-proxy mode)
- The wire-contract surface exposed via stdio JSON-RPC
- Dependency / supply-chain integrity of `presidio-hardened-x402-mcp` releases

Out-of-scope (route to parent repo):

- PII detection accuracy / Presidio rule coverage
- Policy-engine semantics, replay-guard cryptography, audit-chain HMAC design
- Anything implemented in `presidio_x402.*` modules

## MCP-Specific Considerations

- **stdout discipline.** stdio MCP servers MUST NOT write to stdout (corrupts JSON-RPC framing). All logs go to stderr via the `logging` module; the default audit writer is `NullAuditWriter`. Configuring `PRESIDIO_X402_MCP_AUDIT_PATH` routes audit records to a file (never stdout).
- **Env-var injection.** All configuration is via `PRESIDIO_X402_MCP_*` env vars. Do not pass secrets via shell history or world-readable files; use the MCP client's `env:` block in its config file with appropriate file-system permissions.
- **Production key gates.** Set `PRESIDIO_X402_REQUIRE_FINGERPRINT_KEY=1` and `PRESIDIO_X402_REQUIRE_CHAIN_KEY=1` when cross-process replay or audit-chain continuity is required; the parent library will fail startup instead of falling back to per-process keys.
- **HTTP-proxy mode trust boundary.** When `PRESIDIO_X402_MCP_REMOTE_BASE_URL` and `PRESIDIO_X402_MCP_REMOTE_API_KEY` are set, payment metadata leaves the agent host. The remote screening service is the new trust boundary; verify its TLS configuration and audit policy before enabling.
- **Tool side effects.** `check_payment_policy` and `check_payment_replay` mutate state on every call (spend ledger / fingerprint cache). Replay an exact call only when you intend to consume the gate budget.
- **SLO-payment surface.** The parent v0.9.1 `SLOPaymentBroker` is not exposed as an MCP tool in this release. Do not treat raw MCP-readable telemetry as payment authorization; use the parent Python API's signed `evidence-ref@1` verification path if you wire SLO-triggered capacity payments.

## Dependency Security

- Dependencies are pinned via `uv.lock`; lockfile drift is enforced in CI
- `pip-audit` runs per PR; Medium+ CVEs without a documented waiver block merge
- Dependabot is configured for weekly `pip` and `github-actions` ecosystem updates
- CodeQL / Bandit SAST runs per PR and on a weekly schedule
- Secret-scanning (Gitleaks) runs per PR

## Software Development Lifecycle

This package is developed under the Presidio hardened-family SDLC. The full SDLC report — scope, standards mapping, threat-model gates, and supply-chain controls — is at <https://github.com/presidio-v/presidio-hardened-docs/blob/main/sdlc/sdlc-report.md>.
