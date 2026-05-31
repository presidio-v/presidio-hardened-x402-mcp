# Changelog

All notable changes to `presidio-hardened-x402-mcp` will be documented in this file.
Format based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
versioning follows [SemVer](https://semver.org/).

## [Unreleased]

## [0.1.1] — 2026-05-31

### Added

- README badges (PyPI version, supported Python versions, GitHub release, MIT license, CI status).
- `<!-- mcp-name: io.github.presidio-v/presidio-hardened-x402-mcp -->` HTML comment in README — ownership-verification annotation for the official MCP Registry. The registry verifies PyPI ownership by checking the package description (which is the README at publish time) for this string. Required for canonical-registry submission, which is the upstream that PulseMCP and other registries ingest from.

### Notes

- No functional code changes. The version bump is required because PyPI does not allow re-uploading the same version, and the README annotation only takes effect when re-published.

## [0.1.0] — 2026-05-31

Initial public release.

### Added

- FastMCP stdio server exposing three tools that wrap the [`presidio-hardened-x402`](https://pypi.org/project/presidio-hardened-x402/) library:
  - `screen_payment_metadata(resource_url, description, reason, entities?)` — PII detection + redaction. No side effects.
  - `check_payment_policy(resource_url, amount_usd)` — spending-policy gate. Records spend on success.
  - `check_payment_replay(resource_url, pay_to, amount, currency, deadline_seconds)` — fingerprint-based replay detection. Records fingerprint on success.
- Two execution modes:
  - **In-process (default)** — local `PIIFilter`, `PolicyEngine`, `ReplayGuard`. No network, no API key, no quota.
  - **HTTP-proxy (opt-in)** — tool 1 can proxy to a configured screening service via `PRESIDIO_X402_MCP_REMOTE_BASE_URL` + `..._REMOTE_API_KEY`. Returns structured `{error, ...}` on remote failure rather than silently falling back to in-process.
- Wire-contract parity with the v0.4.0 screening-api: field-length caps (`resource_url ≤ 2048`, `description ≤ 4096`, `reason ≤ 4096`) and entity-finding shape are identical.
- Env-var configuration for PII mode, spending policy, replay TTL / Redis URL, audit-file path, log level, and remote screening endpoint.
- `server.json` MCP registry manifest (`registryType: pypi`, `runtimeHint: uvx`).
- `LICENSE` (MIT), `SECURITY.md` (disclosure path + MCP-specific considerations), `PRESIDIO-REQ.md` (requirements baseline).
- CI gates (all required): lint (ruff), test matrix (CPython 3.10–3.13) with coverage ≥ 90%, lockfile drift, dependency audit (`pip-audit`), SAST (`bandit`), secret scan (`gitleaks`).
- Branch protection requiring all 8 CI checks; `enforce_admins: true`; no force-push, no delete.
- Dependabot config for weekly `pip` + `github-actions` updates.

### Notes

- Tools 2 and 3 (`check_payment_policy`, `check_payment_replay`) record state on every call. Invoke each exactly once, immediately before the actual payment.
- Audit-event emission from tools is deferred to v0.2.0; the `AuditLog` instance is constructed at startup but tools do not currently call `_AUDIT.emit()`.
