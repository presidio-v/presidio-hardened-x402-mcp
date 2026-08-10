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
- **Unwrapped parent surfaces.** The three MCP tools cover the parent library's stable pre-payment controls — PII redaction, spending policy, replay detection — and nothing beyond them. Passing all three is not evidence that any other parent control ran. Reach these through the parent Python API, not through this server:
  - *Capability enforcement.* The v0.11.0 `CapabilityEnforcer` — which makes a payment prove it is authorized by a verified `capability-grant@1` chain before signing — is not wired into any MCP tool. An agent that clears `check_payment_policy` has shown the payment is within budget, not that it was authorized. Do not treat these tools as an authorization gate.
  - *Settlement reconciliation.* The v0.10.0 `settlement-ref@1` treasury binding is not emitted here. MCP tool output records why a payment was allowed but carries no transaction hash, so it cannot be reconciled against the settlement it authorized.
  - *SLO-triggered payments.* The v0.9.1 `SLOPaymentBroker` is not exposed either. Do not treat raw MCP-readable telemetry as payment authorization; use the parent's signed `evidence-ref@1` verification path if you wire SLO-triggered capacity payments.

## Dependency Security

- Dependencies are pinned via `uv.lock`; lockfile drift is enforced in CI
- `pip-audit` runs per PR; Medium+ CVEs without a documented waiver block merge
- Dependabot is configured for weekly `pip` and `github-actions` ecosystem updates
- CodeQL / Bandit SAST runs per PR and on a weekly schedule
- Secret-scanning (Gitleaks) runs per PR

### Active audit waivers

Waivers are declared as explicit `--ignore-vuln` IDs in the `audit` job of
`.github/workflows/ci.yml`. Scoping them to single advisory IDs means an
unrelated advisory in the same package still blocks merge.

| Advisory | Package | Rationale | Removal condition |
|---|---|---|---|
| PYSEC-2026-3552 | `cryptography` 48.0.1 | PKCS#7 `EnvelopedData` decryption oracle. Not reachable: nothing in the dependency tree imports `cryptography.hazmat.primitives.serialization.pkcs7`. Fix lands in 50.0.0, which the tree cannot resolve. | `presidio-anonymizer` allows `cryptography>=49` |
| PYSEC-2026-3553 | `cryptography` 48.0.1 | X.509 chain-building exponential-blowup DoS. Not reachable: nothing imports `cryptography.x509.verification`. Fix lands in 49.0.0. | as above |
| PYSEC-2026-3554 | `cryptography` 48.0.1 | X.509 name-constraint wildcard escape. Same unreachable surface as PYSEC-2026-3553. Fix lands in 49.0.0. | as above |

`cryptography` is a transitive dependency only. `presidio-anonymizer` 2.2.364
(latest at time of waiver) requires `cryptography>=48.0.1,<49.0.0`, so no
resolvable version of this tree contains the fixes. This tree uses
`cryptography` solely for AES-CBC (the `presidio-anonymizer` Encrypt operator)
and Ed25519 signature verification (`presidio-x402`) — neither touches the
affected code paths.

## Software Development Lifecycle

This package is developed under the Presidio hardened-family SDLC. The full SDLC report — scope, standards mapping, threat-model gates, and supply-chain controls — is at <https://github.com/presidio-v/presidio-hardened-docs/blob/main/sdlc/sdlc-report.md>.
