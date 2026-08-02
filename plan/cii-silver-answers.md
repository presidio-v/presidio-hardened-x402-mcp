---
status: working sheet
owner: vstantch
target: OpenSSF Best Practices Badge — SILVER level (on top of passing)
project_url: https://github.com/presidio-v/presidio-hardened-x402-mcp
related:
  - cii-passing-answers.md
---

# CII Best Practices — SILVER answer sheet

Fill-in sheet for the **silver** tab at
<https://www.bestpractices.dev/en/projects/13930>. It covers
only the criteria silver *adds* on top of passing; passing answers carry over
unchanged (see `cii-passing-answers.md`).

This is a skeleton: rows backed by rendered project files are answered; rows that
depend on this codebase are left as `FILL` markers. Resolve every `FILL` honestly
before pasting — do not paste a marker into the BadgeApp.

Each row shows the **Status** to set in the dropdown and the **Justification** to
paste. `REPO` = `https://github.com/presidio-v/presidio-hardened-x402-mcp`.

## Badge embed — no change needed

Silver uses the **same** embed code as passing; the badge image auto-renders the
current level:

```markdown
[![OpenSSF Best Practices](https://www.bestpractices.dev/projects/13930/badge)](https://www.bestpractices.dev/projects/13930)
```

If the README badge already uses this URL, it upgrades to "silver" automatically
once the badge cache refreshes — no edit required.

## Backing docs

These rendered files back the silver answers; confirm each is on `main`:

- `GOVERNANCE.md` — governance model, roles, continuity
- `ARCHITECTURE.md` — components, core flow, trust boundaries
- `ASSURANCE.md` — consolidated security assurance case (`assurance_case`)
- `allowed_signers` — public release signing key for local tag verification
- `CONTRIBUTING.md` — DCO sign-off requirement
- `SECURITY.md` — reporter credit, how to obtain signing keys, assurance-case link
- `README.md` — 12-month roadmap + links to GOVERNANCE/ARCHITECTURE/ASSURANCE

---

## Governance & continuity

| Criterion | Status | Justification to paste |
|---|---|---|
| `dco` | **Met** | Every commit must carry a DCO `Signed-off-by` line (`git commit -s`); enforced in review. Documented at `REPO/blob/main/CONTRIBUTING.md#licensing-and-developer-certificate-of-origin-dco`. Inbound = outbound `MIT`. |
| `code_of_conduct` | **Met** | Contributor Covenant at `REPO/blob/main/CODE_OF_CONDUCT.md` (standard location). |
| `governance` | **Met** | Governance model documented at `REPO/blob/main/GOVERNANCE.md` — decision-making, escalation, and security/API change rules. Confirmed against the file. |
| `roles_responsibilities` | **Met** | Key roles (steward org, maintainer, security contact, release manager, contributor) documented at `REPO/blob/main/GOVERNANCE.md#roles-and-responsibilities`. |
| `access_continuity` | **Met** | Continuity rests on the steward organisation, not one person: the repository is owned by the `presidio-v` GitHub org (not a personal account); PyPI publishing uses Trusted Publishing (OIDC) bound to the org repo, so there is no personal API token that dies with an individual; the release signing key is held in the organisation password manager and is recoverable; and the release procedure is written down in `REPO/blob/main/PUBLISHING.md`. A second person with write access is in place: `ceoofcyber` is a write collaborator and a code owner, so more than one individual can assume each role. URL: `REPO/blob/main/GOVERNANCE.md#project-continuity`. |
| `bus_factor` (SHOULD) | **Met** | Bus factor is backed by the PRESIDIO organisation rather than a lone maintainer. More than one person can assume the maintainer, security-contact and release-manager roles: an external reviewer (`ceoofcyber`) holds write access and is named in `.github/CODEOWNERS`, and PRESIDIO is a staffed organisation with the depth to backfill each role. All release credentials are organisation-held and recoverable from an enterprise vault rather than tied to one machine or one person — the signing key, the deployment secrets, and the publishing path (Trusted Publishing via OIDC bound to the org repo, so no personal API token exists to be lost). Issue triage, change acceptance and releases can therefore continue if any single individual becomes unavailable. See `REPO/blob/main/GOVERNANCE.md#project-continuity`. |

## Documentation

| Criterion | Status | Justification to paste |
|---|---|---|
| `documentation_roadmap` | **Met** | `REPO#roadmap` includes a "Planned direction (next 12 months)" section. Confirmed: the README roadmap names real, dated intended work. |
| `documentation_architecture` | **Met** | `REPO/blob/main/ARCHITECTURE.md` — components, core-flow pipeline, and trust boundaries; linked from the README. |
| `documentation_security` | **Met** | `REPO/blob/main/SECURITY.md` documents the security controls, threat model, and reporting process; `ARCHITECTURE.md#trust-boundaries` states the trust boundaries. The full threat model, trust boundaries, secure-design argument and weakness-class argument live in `REPO/blob/main/ASSURANCE.md`; the audit history, including findings that remain open, is in `REPO/blob/main/SECURITY-AUDIT.md`. |
| `documentation_quick_start` | **Met** | README "Quick Start" (before/after example) plus `docs/`. README "Quick start" shows the MCP host configuration and the three tool calls an agent makes; `REPO/blob/main/CONTRIBUTING.md#local-verification` covers the development path. There is no separate `docs/` tree — the README is the quick-start material. |
| `documentation_current` | **Met** | Docs track the current release line; per-version roadmap and hand-written `CHANGELOG.md` are kept in sync with each release. |
| `documentation_achievements` | **Met** | The OpenSSF Best Practices badge is displayed and hyperlinked on the README front page. |

## Change control & reporting

| Criterion | Status | Justification to paste |
|---|---|---|
| `contribution_requirements` | **Met** | `REPO/blob/main/CONTRIBUTING.md#requirements-for-acceptable-contributions` — style, tests, security-change rules, dependency bar. |
| `report_tracker` | **Met** | GitHub Issues: `REPO/issues`. |
| `maintenance_or_update` | **Met** | `REPO/blob/main/SECURITY.md#supported-versions` states which versions are supported and for how long; `REPO/blob/main/SEMVER.md` documents the upgrade path and what counts as a breaking change. |
| `vulnerability_report_credit` | **Met** | `REPO/blob/main/SECURITY.md#reporting-a-vulnerability` — reporters are credited by name in the published advisory and the CHANGELOG entry unless they request anonymity. |
| `vulnerability_response_process` | **Met** | `REPO/blob/main/SECURITY.md#reporting-a-vulnerability` — private GitHub Security Advisory intake, acknowledgement and patch targets stated. |

## Quality & testing

| Criterion | Status | Justification to paste |
|---|---|---|
| `tests_documented_added` | **Met** | `REPO/blob/main/CONTRIBUTING.md#tests` states the policy that changes adding/modifying functionality ship with tests in the same PR. |
| `test_policy_mandated` | **Met** | Formal written policy at `REPO/blob/main/CONTRIBUTING.md#tests`: functionality changes ship with tests; bug fixes include a regression test. Enforced in review and by the coverage gate. |
| `automated_integration_testing` | **Met** | `REPO/blob/main/.github/workflows/ci.yml` runs the full suite on every push and pull request. `ci.yml` runs the full suite on every push and pull request across a **Python 3.10 / 3.11 / 3.12 / 3.13 matrix** on Linux, plus lint, lockfile-drift, dependency audit, Bandit, CodeQL, Gitleaks and an Atheris fuzz job. There is no partner or external end-to-end suite; `tests/test_e2e_inprocess_client.py` drives the server in-process through a real MCP client. |
| `regression_tests_added50` | **Met** | Policy requires a regression test with every bug fix. Worked example: PR #31 raised the parent floor after a redaction bypass and shipped four `TestPercentEncodedPII` cases **verified to fail against the previous parent** — a genuine regression test, not a restatement of current behaviour. PR #32 fixed the missing TLS check on the remote endpoint and shipped 19 tests in the same change. Both bug fixes in the last six months carry regression tests, so the >50% bar is met on a small but complete sample. |
| `test_statement_coverage80` | **Met** | Enforced in CI, above the required floor: `.github/workflows/ci.yml` runs `pytest --cov=presidio_x402_mcp --cov-fail-under=90`, so a pull request dropping statement coverage below **90%** fails. Current measured coverage is **91.27%**. |
| `warnings_strict` | **Met** | ruff with `select = ["E","F","W","I","N","UP","S","B","A","C4","SIM","TCH"]` — well beyond defaults, and including the `S` (bandit) security rule set. Documented exclusions are narrow and justified in `pyproject.toml`: `S101` (assert is the idiom in tests) and `S603`/`S607` (subprocess calls use fixed, non-shell argv). CI fails on any finding: `ruff check` and `ruff format --check` both gate the Lint job. |
| `coding_standards` | **Met** | `REPO/blob/main/CONTRIBUTING.md#style` names the required style/lint tool; config in the project's build/lint config. The tool is **ruff**; configuration in `[tool.ruff]` in `pyproject.toml`. |
| `coding_standards_enforced` | **Met** | The style/lint check runs in CI on every PR (FLOSS enforcement). |
| `installation_common` | **Met** | Standard install from the package index. `pip install presidio-hardened-x402-mcp`, or run it directly with `uvx presidio-hardened-x402-mcp` — the documented MCP host invocation. |
| `installation_development_quick` | **Met** | `REPO/blob/main/CONTRIBUTING.md#local-verification` — documents the one setup path that installs everything needed to build and test. |
| `build_repeatable` (SHOULD) | **Met** | Artefacts are built via the standard flow against a fully pinned dependency graph on GitHub-hosted runners with SHA-pinned Actions; the build is deterministic from pinned sources. Confirmed pinned, and deliberately **not** claimed as bit-for-bit reproducible. `uv.lock` pins the full dependency graph; every GitHub Action is pinned to a commit SHA with the tag in a trailing comment; builds run on GitHub-hosted runners via a standard PEP 517 build. Hermetic, byte-identical reproducibility has not been verified and is not asserted. |
| `build_standard_variables` | **N/A** | Confirmed N/A: pure Python, no compiler or linker step. |
| `build_preserve_debug` | **N/A** | Confirmed N/A: no compiled artefacts. |
| `build_non_recursive` | **N/A** | Confirmed N/A: no make or recursive subdirectory build. |
| `installation_standard_variables` | **N/A** | Confirmed N/A: installed via pip/uv from PyPI, so `DESTDIR`-style conventions do not apply. |

## Dependencies & components

| Criterion | Status | Justification to paste |
|---|---|---|
| `external_dependencies` | **Met** | Dependencies are listed machine-readably in the project manifest and fully pinned in a lockfile; a CycloneDX SBOM is generated per release in CI. Manifest `pyproject.toml`; lockfile `uv.lock`, pinning all 87 resolved packages. CI enforces the two stay in step via a `uv lock --locked` drift check on every PR. |
| `updateable_reused_components` | **Met** | All reused components are standard package-index packages installed via the package manager (no vendored copies); Dependabot tracks updates. |
| `interfaces_current` | **Met** | Dependencies are kept current (Dependabot + dependency floors), the public API is tracked in `SEMVER.md`, and the code does not rely on deprecated FLOSS functions where alternatives exist. |

## Security

| Criterion | Status | Justification to paste |
|---|---|---|
| `assurance_case` | **Met** (URL required) | URL: `REPO/blob/main/ASSURANCE.md`. Consolidated assurance case with all four required parts (threat model, trust boundaries, secure-design-principles argument, common-implementation-weakness argument). Confirmed: `ASSURANCE.md` is fully written for this project — no template placeholders remain — and its threat model states what is out of scope (the parent library's internals, key custody, detector recall, the payment rail) rather than leaving those silently assumed. |
| `implement_secure_design` | **Met** | **Fail-safe defaults:** the default mode is fully local with no network egress; both gates raise rather than returning a permissive result; a cleartext remote endpoint prevents startup. **Complete mediation:** every tool call passes length validation before processing, and the gates record as they check, so no caller observes an allow decision that was not also accounted for. **Least privilege:** the package holds no long-lived secret it does not need, and CI workflows declare `contents: read` at the top level with only CodeQL's SARIF upload and the release job's OIDC token re-declaring more. **Defence in depth:** three tools counter distinct threats and do not substitute for one another; Bandit and CodeQL analyse the same code differently. **Economy of mechanism:** no cryptography is implemented here at all, and the adapter is small enough to read end to end. See `REPO/blob/main/ASSURANCE.md#3-secure-design-principles-applied`. |
| `input_validation` | **Met** | All data crossing the untrusted boundary is validated against a whitelist before use. Concrete example: `_validate_lengths` caps `resource_url` at 2048 and `description` / `reason` at 4096 characters before any processing, mirroring the screening service's request model so both entry points reject the same oversized input; the metadata is then screened by the parent `PIIFilter`. Separately, `_validate_remote_base_url` whitelists the `https` scheme (loopback excepted) and matches on the parsed hostname, so `http://localhost.evil.example.com` is refused. |
| `hardening` | **Met** | TLS is required on the only outbound endpoint, verified at import and refusing to start otherwise; certificate verification is on by default and never disabled; requests are time-boxed. Every GitHub Action is SHA-pinned. Workflow tokens are least-privilege. Gitleaks scans the full history and secret-scanning push protection is enabled on the repository. Secrets are read from the environment and never logged; diagnostics go to stderr so they cannot corrupt the stdio protocol channel. |
| `crypto_weaknesses` | **Met** | N/A for this package: it implements no security functions of its own and contains no call to any hash or cipher primitive. Cryptography (HMAC-SHA256 chaining, Ed25519 signing) belongs to the parent library. Transport security is TLS via `httpx`. |
| `crypto_algorithm_agility` (SHOULD) | **N/A** | Confirmed N/A: this package negotiates no cipher suites of its own. TLS suite selection is delegated to `httpx`/OpenSSL, which follow the platform's current defaults. |
| `crypto_credential_agility` | **Met** | Confirmed: every credential — `PRESIDIO_X402_MCP_REMOTE_API_KEY`, `PRESIDIO_X402_FINGERPRINT_KEY`, `PRESIDIO_X402_CHAIN_KEY` — is supplied from outside the source tree through environment variables and is rotatable by restarting the process. None is hard-coded; Gitleaks gates this on every push. |
| `crypto_used_network` | **Met** | Network communication uses TLS. Confirmed. The single outbound call is HTTPS, and a non-TLS base URL now refuses to start (loopback excepted, where traffic does not cross a network). |
| `crypto_tls12` | **Met** | The HTTP client uses TLS ≥1.2. Confirmed: `httpx` on the platform OpenSSL negotiates TLS 1.2 or better; this package does not lower the default minimum version. |
| `crypto_certificate_verification` | **Met** | TLS certificate verification is on by default; verification is not disabled. Confirmed: `httpx` verifies certificates by default and this package never passes `verify=False` or supplies a permissive SSL context. |
| `crypto_verification_private` | **Met** | Certificate verification precedes transmission of any private data. Confirmed: the pre-redaction payload and the `X-API-Key` header are only sent inside the verified TLS session established by `httpx.AsyncClient`, after certificate verification. |
| `signed_releases` | **Met** | Releases are cryptographically signed and the process for obtaining/verifying keys is documented at `REPO/blob/main/SECURITY.md#obtaining-the-public-signing-keys`: build provenance attestation, SSH-signed git tags with the public key in `REPO/blob/main/allowed_signers`. Confirmed for this project: release tags are SSH-signed with the org key and show as Verified on GitHub (v0.1.3 verified `reason: valid`); the public key is in `REPO/blob/main/allowed_signers`. PyPI artefacts are published through Trusted Publishing (OIDC), so no long-lived token is involved. |
| `version_tags_signed` | **Met** | Every release is a git tag, SSH-signed with the org key and shown as Verified on GitHub. |
| `sites_password_security` | **N/A** | Confirmed N/A: this project stores no user passwords and operates no authenticating site. |

## Analysis & monitoring

| Criterion | Status | Justification to paste |
|---|---|---|
| `static_analysis_common_vulnerabilities` | **Met** | CodeQL (`REPO/blob/main/.github/workflows/codeql.yml`) and OpenSSF Scorecard run on every push/PR. Bandit runs on every push and pull request at medium severity and medium confidence (`.github/workflows/codeql.yml`, the `Analyze (Python)` job), and ruff's `S` rule set applies the same checks at lint time. |
| `dynamic_analysis_unsafe` | **N/A** | Confirmed N/A: Python is memory-safe and this package contains no native code. Note that coverage-guided fuzzing runs regardless — an Atheris harness (`fuzz/fuzz_config_validation.py`) exercises the configuration validators on every pull request. |
| `dependency_monitoring` | **Met** | Dependabot + dependency audit in CI + OpenSSF Scorecard continuously check external dependencies for known vulnerabilities. |

## Accessibility & internationalization

| Criterion | Status | Justification to paste |
|---|---|---|
| `accessibility_best_practices` | **N/A** | Confirmed N/A: this is a headless stdio MCP server with no graphical or end-user interface. |
| `internationalization` | **N/A** | Confirmed N/A: no user-facing localizable strings; the only output is a JSON-RPC tool result consumed by an agent. |

---

## Notes

- Any silver criterion **not** listed here carries over unchanged from the passing
  sheet — leave those answers as they already are.
- If BadgeApp shows a silver-only criterion not covered above, it is almost
  certainly answerable **N/A** (library vs. website/app) or **Met** by an existing
  artefact; check `SECURITY.md` / `CONTRIBUTING.md` / `ci.yml` first.
- `bus_factor`, `build_repeatable`, and `crypto_algorithm_agility` are SHOULD
  criteria — "Met" / "N/A" with an honest justification is accepted; none is a
  hard blocker.
- `assurance_case` is the only silver MUST that requires a net-new document
  (`ASSURANCE.md`); resolve its own FILL markers before answering this row.
