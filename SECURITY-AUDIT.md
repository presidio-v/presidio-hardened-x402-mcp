# Security Audit — `presidio-hardened-x402-mcp`

**Audit date:** 2026-06-03
**Commit audited:** `49e8204` (branch `claude/security-audit-ziQWX`)
**Scope:** This repository only — the MCP adapter (`src/presidio_x402_mcp/server.py`),
its packaging, CI/CD, and supply-chain configuration. Security controls implemented
inside the `presidio_x402.*` parent library (PII detection accuracy, policy-engine
semantics, replay-guard cryptography, audit-chain HMAC) are **out of scope** per
`SECURITY.md` and are not re-reviewed here.

## Methodology

Manual review of all source, tests, GitHub Actions workflows, `pyproject.toml`,
`uv.lock`, `server.json`, and supporting docs. Focus areas: the stdio JSON-RPC tool
surface, the HTTP-proxy trust boundary, input validation, secret handling, and
supply-chain integrity of the release pipeline.

## Summary

The codebase is small, well-structured, and shows clear security intent (stdout
discipline, no silent fallback in remote mode, request timeouts, trusted-publishing
release flow, pinned lockfile with hashes). No critical vulnerabilities were found.
The findings below are hardening opportunities, the most notable being the absence of
TLS-scheme enforcement on the remote screening endpoint and incomplete least-privilege
configuration in CI.

**Remediation update (2026-06-22):** Finding 4 is closed in `0.1.2` by pinning
the parent runtime dependency to `presidio-hardened-x402>=0.7.0,<0.8.0` and
regenerating `uv.lock` against parent `0.7.0`.

| # | Severity | Finding |
|---|----------|---------|
| 1 | Medium | No `https://` scheme enforcement on `PRESIDIO_X402_MCP_REMOTE_BASE_URL` — PII + API key can leave the host in cleartext |
| 2 | Medium | CI workflows missing least-privilege `permissions:` block (`ci.yml`, `secret-scan.yml`) |
| 3 | Low–Medium | GitHub Actions pinned to mutable tags, not commit SHAs |
| 4 | Low–Medium | Unbounded upper version on `presidio-hardened-x402>=0.4.0` affects `uvx` runtime resolution |
| 5 | Low | No input-length limits on `check_payment_policy` / `check_payment_replay` |
| 6 | Low | Remote 200 response is not defensively parsed (`KeyError`/`JSONDecodeError` propagate) |
| 7 | Low | Invalid numeric env vars crash the server at startup with an uncaught exception |
| 8 | Info | `codeql.yml` runs Bandit, not CodeQL — name overstates the analysis performed |

---

## Findings

### 1. (Medium) Remote screening endpoint is not required to be HTTPS

**Location:** `src/presidio_x402_mcp/server.py:106-108`, `181-185`

`_REMOTE_BASE_URL` is taken verbatim from the environment and used to build the
request URL with no scheme validation:

```python
_REMOTE_BASE_URL: str | None = os.getenv("PRESIDIO_X402_MCP_REMOTE_BASE_URL")
...
url = f"{(_REMOTE_BASE_URL or '').rstrip('/')}/v1/screen"
headers = {"X-API-Key": _REMOTE_API_KEY or ""}
resp = await client.post(url, json=payload, headers=headers)
```

In HTTP-proxy mode, the request body carries the very payment metadata the tool exists
to protect (`resource_url`, `description`, `reason` — which may contain emails, SSNs,
names) **before** redaction, and the `X-API-Key` header carries a long-lived secret. If
an operator sets `PRESIDIO_X402_MCP_REMOTE_BASE_URL=http://...` (typo, internal testing
config promoted to prod, or a downgrade), both the PII and the API key are transmitted
in cleartext. `httpx` does verify TLS certificates by default (good), but it does not
prevent a plain-`http://` URL.

**Impact:** Cleartext disclosure of pre-redaction PII and the screening-API key on the
network path. This directly undercuts the tool's stated purpose.

**Recommendation:** Reject non-`https` base URLs at startup (allow an explicit
`http://localhost`/`127.0.0.1` carve-out for local testing if needed). Fail closed —
refuse to enable remote mode rather than silently sending cleartext.

```python
from urllib.parse import urlparse

def _validate_remote_base_url(raw: str) -> str:
    parsed = urlparse(raw)
    if parsed.scheme != "https" and parsed.hostname not in {"localhost", "127.0.0.1"}:
        raise ValueError("PRESIDIO_X402_MCP_REMOTE_BASE_URL must use https://")
    return raw
```

---

### 2. (Medium) CI workflows do not set least-privilege `permissions`

**Location:** `.github/workflows/ci.yml`, `.github/workflows/secret-scan.yml`

`codeql.yml` correctly sets `permissions: contents: read` and `release.yml` scopes
`id-token: write`, but `ci.yml` and `secret-scan.yml` declare **no** top-level
`permissions:` block. They therefore inherit the repository/organization default
`GITHUB_TOKEN` scope, which in many configurations is read/write. These workflows run
on `pull_request`, so a malicious PR that compromises a build step (e.g. via a poisoned
transitive dev dependency pulled during `pip install -e ".[dev]"`) would execute with
whatever the default token grants.

**Impact:** Larger blast radius than necessary if any CI step is compromised on an
untrusted PR.

**Recommendation:** Add an explicit minimal block to every workflow:

```yaml
permissions:
  contents: read
```

Override per-job only where a broader scope is genuinely required.

---

### 3. (Low–Medium) GitHub Actions are pinned to mutable tags, not commit SHAs

**Location:** all files under `.github/workflows/`

Third-party and first-party actions are referenced by floating tags — e.g.
`actions/checkout@v6`, `astral-sh/setup-uv@v7`, `actions/upload-artifact@v5`, and most
critically `pypa/gh-action-pypi-publish@release/v1` in the release path. Tags are
mutable: if an action's release tag is moved (or the action's repo is compromised), the
new code runs with this repository's CI privileges — including, for the publish job, an
OIDC token that can push to PyPI.

**Impact:** Supply-chain exposure in the build/publish pipeline of a security-tooling
package.

**Recommendation:** Pin actions to full commit SHAs with the human-readable tag in a
trailing comment, and let Dependabot (already configured for the `github-actions`
ecosystem) propose SHA bumps:

```yaml
- uses: actions/checkout@<40-char-sha>  # v6
```

Prioritize the `release.yml` actions, as that is the workflow with publish authority.

---

### 4. (Low–Medium) Unbounded upper bound on the parent dependency at runtime

**Location:** `pyproject.toml:29-32`

```toml
dependencies = [
    "mcp[cli]>=1.27.2,<2.0.0",
    "presidio-hardened-x402>=0.4.0",
]
```

`mcp` is correctly capped below the next major, but `presidio-hardened-x402` has no
upper bound. `uv.lock` pins it to `0.4.0` with a hash, which protects developers and CI.
However, the documented runtime install path is `uvx presidio-hardened-x402-mcp` (see
`server.json` `runtimeHint: "uvx"`), which resolves dependencies fresh against PyPI and
**does not** consult this repo's lockfile. End users therefore receive whatever the
latest published `presidio-hardened-x402` is — including a future breaking or
compromised release — with no integrity pin.

**Impact:** The entire security surface of this thin adapter is delegated to the parent
library; an unbounded version range removes the one place this package could constrain
which parent-library code its users run.

**Recommendation:** Add a compatible-release upper bound, e.g.
`presidio-hardened-x402>=0.4.0,<0.5.0` (or `<1.0.0`), and bump it deliberately per
release after verifying the new parent version against the wire contract this adapter
mirrors.

---

### 5. (Low) No input-length limits on the policy and replay tools

**Location:** `src/presidio_x402_mcp/server.py:285-353`

`screen_payment_metadata` enforces `_MAX_RESOURCE_URL` / `_MAX_DESCRIPTION` /
`_MAX_REASON` via `_validate_lengths`. The other two tools do not bound any input.
`check_payment_policy(resource_url, ...)` and
`check_payment_replay(resource_url, pay_to, amount, currency, ...)` accept arbitrarily
large strings. Because both tools **record** state keyed on these values (spend ledger
per endpoint URL, fingerprint cache), an unbounded `resource_url` or `pay_to` can grow
in-memory structures and the audit/ledger entries.

**Impact:** Low — the stdio transport is single-client and the caller is the agent
itself, so this is resource-exhaustion-by-misbehaving-client rather than a remote-attacker
vector. Still inconsistent with the validation already applied to tool 1.

**Recommendation:** Apply the same length ceilings (e.g. reuse `_MAX_RESOURCE_URL` for
`resource_url`, add a sane cap for `pay_to`/`amount`/`currency`) at the top of both
tools.

---

### 6. (Low) Remote success response is parsed without defensive guards

**Location:** `src/presidio_x402_mcp/server.py:213-220`

```python
data = resp.json()
return {
    "redacted_resource_url": data["redacted_resource_url"],
    ...
    "entities_found": data["entities_found"],
    "mode": "remote",
}
```

A `200` response with a non-JSON body raises `json.JSONDecodeError`; a `200` with a
JSON body missing an expected key raises `KeyError`. Neither is caught, so the exception
propagates out of the tool instead of being mapped to the structured
`{"error": "unavailable", ...}` contract the rest of the function so carefully
maintains. A buggy or hostile remote screening service could thus turn a "screening"
call into an unhandled tool error rather than a clean, detectable failure.

**Impact:** Low (the remote is a configured, semi-trusted boundary), but it breaks the
explicit "never silently fall back / always return a structured error" design goal.

**Recommendation:** Wrap the parse in `try/except (ValueError, KeyError)` and return the
`unavailable` error dict on malformed responses; optionally validate that all required
keys are present.

---

### 7. (Low) Invalid numeric configuration crashes the server at import time

**Location:** `src/presidio_x402_mcp/server.py:76-101`

`_float()` does `float(raw)` and `int(os.getenv(..., "300"))` with no error handling.
A malformed `PRESIDIO_X402_MCP_MAX_PER_CALL_USD=abc`, `..._REPLAY_TTL`, or
`..._WINDOW_SECONDS` raises `ValueError` during module import, before the MCP server
starts. (`PRESIDIO_X402_MCP_PER_ENDPOINT_JSON`, by contrast, is handled gracefully and
logged.)

**Impact:** Low — fail-fast on bad config is defensible, but the crash is opaque (a raw
traceback on stderr) and inconsistent with the JSON env var's graceful handling.

**Recommendation:** Catch the conversion error and emit a clear `logger.error` naming
the offending variable, then either exit cleanly or fall back to the documented default.

---

### 8. (Info) `codeql.yml` runs Bandit rather than CodeQL

**Location:** `.github/workflows/codeql.yml`

The workflow is named "CodeQL" and its job "Analyze (Python)", but it installs and runs
**Bandit** (`bandit -r src/ --severity-level medium --confidence-level medium`). Bandit
is a useful linter-style SAST tool, but it is not CodeQL and performs no taint/dataflow
analysis. The mismatch is misleading for anyone reviewing the security posture from the
Actions tab or `SECURITY.md` (which lists "CodeQL / Bandit SAST").

**Impact:** Informational. Coverage is narrower than the name implies; no results are
uploaded to GitHub code scanning (no SARIF), so findings live only in job logs.

**Recommendation:** Either (a) rename the workflow/job to "Bandit SAST" for honesty, or
(b) add the real `github/codeql-action` (init → analyze) alongside Bandit and upload
SARIF so findings surface in the Security tab. Note Bandit's medium/medium gate does
fail the build on findings, so functional SAST coverage exists — this is about accuracy
and visibility.

---

## Positive observations

The following controls were verified and are working as intended:

- **stdout discipline.** No `print`/stdout writes in `server.py`; all diagnostics go
  through `logging` (stderr), and the default audit writer is `NullAuditWriter`. JSON-RPC
  framing integrity is preserved.
- **No silent fallback in remote mode.** Remote failures return an explicit
  `{"error": ...}` discriminator so callers can detect that centralized audit was
  bypassed (`server.py:155-211`) — a deliberate fail-loud design.
- **Request timeouts.** Remote calls use `httpx.Timeout(10.0, connect=3.0)`, preventing
  a hung remote from stalling the agent.
- **TLS verification on by default.** `httpx.AsyncClient` is created without disabling
  `verify`, so certificates are validated (see Finding 1 for the remaining scheme gap).
- **Trusted Publishing + mandatory reviewer.** Releases use PyPI OIDC trusted publishing
  (no long-lived token), a separate build/publish job split, and `PUBLISHING.md`
  documents the `pypi`-environment required-reviewer gate as non-optional.
- **Pinned lockfile with hashes + drift enforcement.** `uv.lock` pins every dependency
  with a SHA-256 hash; `uv lock --locked` runs in CI to catch drift.
- **Layered supply-chain CI.** Gitleaks secret scanning, `pip-audit`, Bandit SAST, and
  Dependabot (weekly, `pip` + `github-actions`) are all configured.
- **No secrets committed.** No hardcoded credentials, keys, or tokens were found in
  source, tests, or config; secret material is supplied exclusively via env vars.
- **Input length caps on the PII tool.** `screen_payment_metadata` bounds all three text
  fields, mirroring the upstream wire contract.

## Out-of-scope reminders

Per `SECURITY.md`, the cryptographic and detection cores live in
`presidio-hardened-x402` and must be audited there. Two behaviors that *surface* in this
repo but are *implemented* upstream are worth carrying into that review:

- **Replay protection without `PRESIDIO_X402_FINGERPRINT_KEY`** falls back to an
  ephemeral per-process in-memory store (documented at `server.py:333-336`). Confirm the
  parent library's default-key behavior is safe and that cross-process deployments set
  the key.
- **Audit logging is off by default** (`NullAuditWriter` unless
  `PRESIDIO_X402_MCP_AUDIT_PATH` is set). Confirm this matches the intended default for
  deployments that rely on the audit chain.

---

*Audit limited to static review of the listed commit. No dynamic testing, fuzzing, or
review of the deployed remote screening service was performed.*
