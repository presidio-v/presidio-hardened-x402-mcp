# Security Assurance Case

This document is the assurance case for `presidio-hardened-x402-mcp`: an explicit argument
for why the project's security requirements are met. It has four parts, as
required by the OpenSSF Best Practices silver criterion `assurance_case`:

1. the threat model,
2. the trust boundaries,
3. the argument that secure design principles are applied, and
4. the argument that common implementation weaknesses are countered.

It is a summary that links to the authoritative detail in
[`SECURITY.md`](SECURITY.md) (controls, per-version threat tables, reporting) and
[`ARCHITECTURE.md`](ARCHITECTURE.md) (components, flow, boundaries) for
`presidio-v/presidio-hardened-x402-mcp`.

## 1. Threat model

**The asset is an irreversible action about to be taken by a machine.** An x402
payment, once signed and sent, cannot be recalled, and the agent deciding to send
it is not a person who will notice something looks wrong. The secondary asset is
the payment metadata itself, which routinely carries personal data.

| Threat | Control |
|---|---|
| An agent leaks personal data into payment metadata that reaches a counterparty | `screen_payment_metadata` detects and redacts before the agent proceeds |
| An agent is driven — by a prompt injection or its own error — to overspend | `check_payment_policy` enforces per-call, daily and per-endpoint caps, and **records** the spend so the budget genuinely depletes |
| The same payment is submitted twice, by retry or by manipulation | `check_payment_replay` fingerprints the payment and refuses a duplicate within the TTL |
| An operator misconfigures the remote endpoint so metadata leaves in cleartext | The base URL must be `https` (loopback excepted); a bad value stops the server at startup rather than at first call |
| A remote screening failure is mistaken for a clean result | Remote mode never falls back to local; it returns a structured `error` discriminator so the caller can see that centralized audit was bypassed |
| The audit trail is tampered with, or an action is later repudiated | Audit records go through the parent library's HMAC-chained `AuditLog` |
| Diagnostics corrupt the JSON-RPC channel and desynchronise the agent | All logging goes to stderr; stdout carries protocol frames only |

**Explicitly out of scope**, documented rather than silently assumed:

- **The parent library's internals.** Detection accuracy, policy arithmetic,
  replay cryptography and the audit chain belong to `presidio-hardened-x402` and
  are audited there. This repo's contribution is to expose them faithfully — and
  to pin a parent floor new enough to be worth exposing.
- **Key custody.** `PRESIDIO_X402_FINGERPRINT_KEY`, `PRESIDIO_X402_CHAIN_KEY` and
  the remote API key are supplied through the environment by the operator. This
  project reads them; it does not store, rotate or protect them.
- **Detector recall.** PII detection is a heuristic. Screening reduces exposure;
  it does not guarantee that no personal data reaches a counterparty.
- **The payment rail.** What happens after the agent decides to pay is the rail's
  concern, not this server's.

## 2. Trust boundaries

Names are kept aligned with [ARCHITECTURE.md](ARCHITECTURE.md#trust-boundaries).

| Boundary | Kind | Control |
|---|---|---|
| MCP client → server | Input validation | Untrusted tool arguments: field-length caps first, then parent-library screening. The primary validation boundary. |
| Operator environment → server | Configuration | Fallible human input. TLS validation of the remote base URL at import; malformed policy JSON degrades to an empty policy with an error log. |
| Server → remote screening API | Egress | The most sensitive egress: pre-redaction metadata plus a long-lived key. Mandatory `https`, default certificate verification, request timeouts, no silent fallback. |
| Server → stdout | Egress (integrity) | stdout is the protocol channel; diagnostics are confined to stderr. |
| Server → audit sink / Redis | Egress (persistence) | HMAC-chained audit writes and an optional Redis replay store, both inheriting the parent library's guarantees. |

## 3. Secure design principles applied

**Fail-safe defaults / secure by default.** The default mode is fully local — no
network egress unless an operator explicitly configures it. The two gates fail
closed: a policy violation or a detected replay raises rather than returning a
permissive result. A cleartext remote endpoint prevents startup instead of being
tolerated.

**Complete mediation.** Every tool call passes length validation before any
processing, and screening runs on all three metadata fields rather than a subset.
Ordering is part of the contract: the gates record *as* they check, so a caller
cannot observe an allow decision that was not also accounted for.

**Least privilege.** The server holds no long-lived secret it does not need; key
custody is delegated to the operator by contract. CI workflows declare
`permissions: contents: read` at the top level, and only the jobs that genuinely
need more — CodeQL's SARIF upload, the release job's OIDC token — re-declare it.

**Defense in depth.** The three tools counter distinct threats and do not
substitute for one another; screening additionally runs at two independent layers
(this server and, in proxy mode, the remote service). Bandit and CodeQL analyse
the same code from different angles.

**Economy of mechanism.** This package implements no cryptography. Fingerprinting,
HMAC chaining and signing are the parent library's, which uses vetted primitives.
The adapter is small enough to be read end to end in one sitting — which is itself
a security property.

## 4. Common implementation weaknesses countered

| Weakness class | How it is countered |
|---|---|
| Improper input validation / injection (CWE-20, CWE-74) | Field-length caps mirroring the service wire contract; tool arguments are typed and never interpolated into a shell or query. Fuzzed by `fuzz/fuzz_config_validation.py`. |
| Memory safety (CWE-119 family) | Not applicable at the source level: Python is memory-safe. Native risk is confined to vetted dependencies, which are version-floored and audited. |
| Cryptographic misuse (CWE-327, CWE-916) | No cryptography is implemented here. All of it is delegated to the parent library. |
| Hard-coded / exposed secrets (CWE-798, CWE-532) | Secrets come from the environment, never from source; Gitleaks scans the full history on every push and pull request. Diagnostics go to stderr and do not log key material. |
| Insecure network / SSRF (CWE-319, CWE-295) | `https` is required on the only outbound endpoint, with certificate verification on by default and request timeouts set. Loopback is the sole documented exception, and matching is on the parsed hostname so prefix tricks such as `localhost.evil.example.com` are refused. |
| Unsafe deserialization (CWE-502) | Only `json` is used — never `pickle`, `yaml.load`, or `eval`. Malformed policy JSON is caught and degraded. Fuzzed alongside the URL validator. |
| Vulnerable dependencies (CWE-1104) | `pip-audit` runs in CI; Dependabot watches both pip and GitHub Actions; the parent library carries a **lower bound of 0.11.1**, chosen because earlier releases contained a redaction bypass. |

These classes are checked continuously on every push and pull request by
**CodeQL** (`security-and-quality` queries, results uploaded to GitHub code
scanning), **Bandit** (medium severity and confidence), **Gitleaks**,
**`pip-audit`**, and **OpenSSF Scorecard**. Coverage-guided fuzzing with
**Atheris** exercises the configuration-validation surface, asserting the TLS
invariant rather than merely checking for crashes.

An independent security audit of this repository was performed on 2026-06-03 and
is published in [`SECURITY-AUDIT.md`](SECURITY-AUDIT.md), including findings that
remain open. It is an internal review, not a third-party engagement, and is
described as such.

## Conclusion

The threats above are each matched to a control; the controls sit at explicit
trust boundaries; the design follows fail-safe, least-privilege, complete-
mediation, defense-in-depth, and economy-of-mechanism principles; and the common
implementation weakness classes are countered by design and checked by automated
analysis. The project's stated security requirements are therefore met, subject
to the documented out-of-scope assumptions.
