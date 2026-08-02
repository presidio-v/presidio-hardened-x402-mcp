---
status: working sheet
owner: vstantch
target: OpenSSF Best Practices Badge — passing level
project_url: https://github.com/presidio-v/presidio-hardened-x402-mcp
---

# CII Best Practices — passing-level answer sheet

Fill-in sheet for <https://www.bestpractices.dev> (passing level). This is a
skeleton: rows already backed by rendered project files are answered; rows that
depend on the specifics of this codebase are left as `FILL` markers for you to
complete after reading the repo. Do not paste a `FILL` marker into the BadgeApp —
resolve it first, honestly, or set the row to N/A with a real reason.

## Before you start

1. **Register the URL as exactly** `https://github.com/presidio-v/presidio-hardened-x402-mcp`.
   Scorecard does a literal DB string match. A trailing slash, `www.`, or the
   package-index URL returns `NotFound` → score 0 despite a real badge.
2. **Log in with GitHub but decline the org grant.** BadgeApp requests `read:org`
   and no code path consumes it. Entry ownership is internal to its database.
3. **Confirm the community-health and process docs are on `main` first** —
   `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `SECURITY.md`, `CHANGELOG.md`,
   `SEMVER.md`. Every URL cited below must resolve on `main` before you answer.
4. Record your badge id in `hardening.toml` (`[badge] bestpractices_id`) once the
   project is created; this sheet's silver counterpart references it as
   `0`.

Shorthand below: `REPO` = `https://github.com/presidio-v/presidio-hardened-x402-mcp`.

---

## Basics — project website content

| Criterion | Status | Justification / URL |
|---|---|---|
| `description_good` | **Met** | `REPO#readme` — README opens with what `presidio-hardened-x402-mcp` does and the problem it solves. Confirmed. |
| `interact` | **Met** | `REPO#readme` — README covers obtaining (presidio_x402_mcp on the package index), feedback (issues), security reports (`SECURITY.md`), and contributing. |
| `contribution` | **Met** | URL: `REPO/blob/main/CONTRIBUTING.md` — documents the fork → branch → PR flow against `main`. |
| `contribution_requirements` | **Met** | URL: `REPO/blob/main/CONTRIBUTING.md#requirements-for-acceptable-contributions` — style config, test policy, security-change rules, dependency bar. |

## Basics — FLOSS license

| Criterion | Status | Justification / URL |
|---|---|---|
| `floss_license` | **Met** | `MIT`. |
| `floss_license_osi` | **Met** | `MIT` is OSI-approved. Confirmed: MIT is on the OSI approved list. |
| `license_location` | **Met** | URL: `REPO/blob/main/LICENSE` |

## Basics — documentation

| Criterion | Status | Justification / URL |
|---|---|---|
| `documentation_basics` | **Met** | README plus `docs/`. The README is the documentation: installation, MCP host configuration, the three tools and their arguments, both operating modes, and the full environment-variable table. There is no separate `docs/` tree. |
| `documentation_interface` | **Met** | README API section; the public interface is documented and, for a library, enumerated in `SEMVER.md` (`presidio_x402_mcp.__all__` or equivalent). The external interface is the MCP tool surface — three tools, their arguments and result shapes — documented in the README and defined as the public API in `REPO/blob/main/SEMVER.md`. Note that `SEMVER.md` states the Python module is *not* a supported import surface; the server is consumed over MCP. |

## Basics — other

| Criterion | Status | Justification / URL |
|---|---|---|
| `sites_https` | **Met** | GitHub and the package index are HTTPS. Confirmed: the project runs no hosted site of its own. GitHub, PyPI and the MCP registry entry are all HTTPS. The optional remote screening endpoint an operator may configure is now required to be HTTPS. |
| `discussion` | **Met** | GitHub Issues: `REPO/issues` — searchable, URL-addressable, open, no proprietary client. |
| `english` | **Met** | All docs and issue handling in English. |
| `maintained` | **Met** | Actively maintained. Actively maintained: **v0.1.3 released 2026-08-02**, carrying a parent security floor and a fix for an open audit finding, with four pull requests merged that day. |

## Change control — repository

| Criterion | Status | Justification / URL |
|---|---|---|
| `repo_public` | **Met** | `REPO` |
| `repo_track` | **Met** | git. |
| `repo_interim` | **Met** | Feature and fix branches are pushed between releases; PR-based flow. |
| `repo_distributed` | **Met** | git. |

## Change control — versioning

| Criterion | Status | Justification / URL |
|---|---|---|
| `version_unique` | **Met** | Semver per release, tagged. |
| `version_semver` | **Met** | URL: `REPO/blob/main/SEMVER.md` — documents the semver profile. |
| `version_tags` | **Met** | Every release is a git tag, SSH-signed and GitHub-verified. |

## Change control — release notes

| Criterion | Status | Justification / URL |
|---|---|---|
| `release_notes` | **Met** | URL: `REPO/blob/main/CHANGELOG.md` — Keep a Changelog format, hand-written, not VCS log output. |
| `release_notes_vulns` | **Met** | CHANGELOG names each CVE/GHSA fixed. No CVE or GHSA identifier has ever applied to this project, so there is nothing of that kind to name. The CHANGELOG does document security-relevant fixes explicitly: the 0.1.3 entry describes the parent percent-encoding redaction bypass and the reason the previous version bound hid it, and names the audit findings closed (1, 2 and 8). |

## Reporting — bug reports

| Criterion | Status | Justification / URL |
|---|---|---|
| `report_process` | **Met** | URL: `REPO/blob/main/CONTRIBUTING.md#reporting-bugs-and-requesting-features` |
| `report_tracker` | **Met** | GitHub Issues. |
| `report_responses` | **Met** | The project has received **no bug reports** to date. The single issue in the tracker (#30, opened 2026-07-31) is an unsolicited promotional post advertising a third-party analytics service, not a report or an enhancement request, and it has not been answered. The criterion is therefore satisfied vacuously rather than by a record of responses, and it is stated that way so a reviewer can judge it. |
| `enhancement_responses` | **Met** | No enhancement requests have been received. See the note on `report_responses` — the only tracker item is a promotional post. |
| `report_archive` | **Met** | URL: `REPO/issues?q=is%3Aissue` — public and searchable. |

## Reporting — vulnerability reports

| Criterion | Status | Justification / URL |
|---|---|---|
| `vulnerability_report_process` | **Met** | URL: `REPO/blob/main/SECURITY.md#reporting-a-vulnerability` |
| `vulnerability_report_private` | **Met** | URL: `REPO/blob/main/SECURITY.md#reporting-a-vulnerability` — private GitHub Security Advisory via the Security tab; acknowledgement and patch targets stated. |
| `vulnerability_report_response` | **N/A** | Confirmed N/A: no vulnerability has been reported to this project by an external party. The findings addressed in 0.1.3 came from the project's own audit (`REPO/blob/main/SECURITY-AUDIT.md`) and from the parent library's release notes. |

## Quality — build system

| Criterion | Status | Justification / URL |
|---|---|---|
| `build` | **Met** | Standard PEP 517 build from source: `python -m build`, or `uv build`. The release workflow builds the sdist and wheel this way before publishing. |
| `build_common_tools` | **Met** | Built with common, widely available tools. Python, `hatchling` as the PEP 517 backend, and `uv` — all common and freely available. |
| `build_floss_tools` | **Met** | The entire toolchain is FLOSS. |

## Quality — automated test suite

| Criterion | Status | Justification / URL |
|---|---|---|
| `test` | **Met** | Test suite under `tests/`, licensed with the project. How to run: `CONTRIBUTING.md#local-verification` and `.github/workflows/ci.yml`. Six test modules under `tests/`, organised by tool: one per MCP tool (`test_screen_payment_metadata.py`, `test_check_payment_policy.py`, `test_check_payment_replay.py`), plus `test_remote_url_validation.py` for the TLS gate, `test_parent_compatibility.py` guarding the parent version floor, and `test_e2e_inprocess_client.py` driving the server through a real in-process MCP client. 48 tests in total. |
| `test_invocation` | **Met** | `pytest tests/` |
| `test_most` | **Met** | Coverage is gated in CI at `--cov-fail-under=90` on statements, currently measuring **91.27%** across 48 tests. `tests/test_e2e_inprocess_client.py` drives the server end-to-end through a real in-process MCP client rather than calling the tool functions directly. |
| `test_continuous_integration` | **Met** | GitHub Actions on every push and PR (`.github/workflows/ci.yml`). Python 3.10, 3.11, 3.12 and 3.13 on Linux, on every push and pull request. |

## Quality — new functionality testing

| Criterion | Status | Justification / URL |
|---|---|---|
| `test_policy` | **Met** | URL: `REPO/blob/main/CONTRIBUTING.md#tests` — written policy that functional changes ship with tests and fixes ship with regression tests. |
| `tests_are_added` | **Met** | Worked example: **PR #32** fixed the missing HTTPS requirement on the remote screening endpoint and shipped 19 tests in the same pull request, including prefix-match traps (`http://localhost.evil.example.com`) and a subprocess test proving the server refuses to start against a cleartext endpoint. **PR #31** is a second example: four regression tests shipped with the parent-floor fix, each verified to fail against the previous parent version. |
| `tests_documented_added` | **Met** | The policy is stated in the contribution instructions themselves (`CONTRIBUTING.md#tests`). |

## Quality — warning flags

| Criterion | Status | Justification / URL |
|---|---|---|
| `warnings` | **Met** | Lint/warnings enforced in CI. ruff, run in CI as `ruff check src/ tests/ fuzz/` and `ruff format --check`, with the job failing on any finding. |
| `warnings_fixed` | **Met** | CI fails on any finding; `main` is clean. |
| `warnings_strict` | **Met** | Enabled rule sets: `E`, `F`, `W`, `I`, `N`, `UP`, `S`, `B`, `A`, `C4`, `SIM`, `TCH` — substantially beyond ruff's defaults, and including the `S` (bandit) security rules. Exclusions are narrow and documented in `pyproject.toml`: `S101` (assert is the test idiom) and `S603`/`S607` (subprocess calls use fixed, non-shell argv). |

## Security — secure development knowledge

| Criterion | Status | Justification / URL |
|---|---|---|
| `know_secure_design` | **Met** | The maintainer designs to these principles and the codebase shows it: fail-closed defaults (both gates raise rather than returning permissive results; a cleartext endpoint stops startup instead of downgrading), least privilege (least-privilege CI tokens; no long-lived secret held that is not needed), defence in depth (three independent controls, plus two SAST tools), complete mediation (validation before any processing, on every call), and economy of mechanism (no bespoke cryptography — none is implemented here at all). The reasoning is written out in `REPO/blob/main/ASSURANCE.md#3-secure-design-principles-applied`. |
| `know_common_errors` | **Met** | The documented threat model (`REPO/blob/main/ASSURANCE.md#1-threat-model`) names the classes defended and maps each to a control: personal data leaking to a counterparty, an agent driven to overspend, duplicate submission, cleartext egress from a misconfigured endpoint, a remote failure mistaken for a clean result, audit-trail tampering, and protocol-channel corruption. Section 4 maps CWE classes — improper input validation (CWE-20/74), insecure transport and SSRF (CWE-319/295), unsafe deserialization (CWE-502), exposed secrets (CWE-798/532), vulnerable dependencies (CWE-1104) — each to its control and to the tool that checks it. |

## Security — cryptographic practices

<!-- If this project performs NO cryptographic operations of its own, most of these
are N/A — say so explicitly per row rather than leaving them blank. If it does,
resolve each FILL against the actual primitives used. -->

| Criterion | Status | Justification / URL |
|---|---|---|
| `crypto_published` | **Met** | N/A for this package: it implements no security function and calls no hash or cipher primitive. TLS is used for transport; the parent library performs HMAC-SHA256 chaining and Ed25519 signing. |
| `crypto_call` | **Met** | N/A: no cryptographic primitive is re-implemented or called here. Transport security comes from `httpx`/OpenSSL; the parent library uses Python's `hmac`/`hashlib` and `cryptography`. |
| `crypto_floss` | **Met** | The crypto libraries used are FLOSS. Confirmed: OpenSSL, and the parent library's `cryptography` — both FLOSS. |
| `crypto_keylength` | **Met** | N/A here — no keys are generated or chosen by this package. TLS key sizes follow the platform defaults, and the parent library's Ed25519 and SHA-256 choices exceed NIST's 2030 minimums. |
| `crypto_working` | **Met** | No MD4, MD5, single DES, RC4, or Dual_EC_DRBG. Confirmed: none of these appear anywhere in this codebase. |
| `crypto_weaknesses` | **Met** | No SHA-1 and no CBC-mode dependency in default paths. Confirmed: no SHA-1 and no CBC-mode dependency; this package uses no cipher directly. |
| `crypto_pfs` | **N/A** | Implements no key-agreement protocol of its own; transport PFS is provided by TLS in the network layer. Confirmed: no key-agreement protocol of its own; PFS comes from the TLS layer. |
| `crypto_password_storage` | **N/A** | Stores no external-user passwords. Confirmed: no external-user passwords are stored. |
| `crypto_random` | **Met** | N/A: this package generates no security-relevant randomness — it contains no `random`, `secrets`, or key-generation call. Replay fingerprints and audit-chain keys are the parent library's responsibility. |

## Security — delivery

| Criterion | Status | Justification / URL |
|---|---|---|
| `delivery_mitm` | **Met** | Distributed over HTTPS via the package index and GitHub. Published to PyPI through **Trusted Publishing (OIDC)** from the org-owned repository, so no long-lived API token exists to steal. Release tags are SSH-signed and shown as Verified on GitHub, and the verifying public key is committed in `REPO/blob/main/allowed_signers`. Distribution is HTTPS throughout. |
| `delivery_unsigned` | **Met** | No hash is fetched over plain HTTP. Release tags are SSH-signed and GitHub-verified. |

## Security — known vulnerabilities

| Criterion | Status | Justification / URL |
|---|---|---|
| `vulnerabilities_fixed_60_days` | **Met** | No known unpatched medium+ vulnerabilities. Dependabot plus dependency audit in CI. Confirmed: no known unpatched medium-or-higher vulnerability. `pip-audit` runs on every pull request, Dependabot covers both pip and GitHub Actions, and Dependabot security updates are enabled on the repository. |
| `vulnerabilities_critical_fixed` | **Met** | Recent dependency criticals were closed by floor bumps within days. Confirmed. The most recent example is the parent redaction bypass: the fixed parent was released on 2026-08-02 and this project's floor was raised and released the same day, in 0.1.3. |

## Security — other

| Criterion | Status | Justification / URL |
|---|---|---|
| `no_leaked_credentials` | **Met** | **Verified.** No `.env`, `.pem`, key, keystore or credential-shaped file appears anywhere in the repository's history — checked across all refs. Gitleaks scans the full history (`fetch-depth: 0`) on every push and pull request, and secret-scanning push protection is enabled on the repository. |

## Analysis — static

| Criterion | Status | Justification / URL |
|---|---|---|
| `static_analysis` | **Met** | CodeQL (results uploaded to GitHub code scanning), `.github/workflows/codeql.yml`. In addition to CodeQL: Bandit at medium severity and confidence on every push and pull request, and ruff's `S` (bandit) rule set at lint time. |
| `static_analysis_common_vulnerabilities` | **Met** | CodeQL's security query suite targets common vulnerability classes. CodeQL runs the `security-and-quality` query suite with results uploaded to GitHub code scanning, covering injection, unsafe deserialization and insecure-transport classes. |
| `static_analysis_fixed` | **Met** | Findings are triaged and fixed before release. |
| `static_analysis_often` | **Met** | CodeQL runs on every push and PR to `main`, plus a weekly scheduled run. |

## Analysis — dynamic

| Criterion | Status | Justification / URL |
|---|---|---|
| `dynamic_analysis` | **Met** | An Atheris coverage-guided fuzz harness (`fuzz/fuzz_config_validation.py`) runs in CI on every pull request, time-boxed, under Python 3.12 on Linux. It drives the two configuration parsers: `_validate_remote_base_url` and the per-endpoint policy JSON parsing. The URL target asserts a **security invariant** — anything accepted must be https or loopback — rather than only checking for crashes, because a validator that accepts `http://evil.example.com` without raising is exactly the defect the gate exists to prevent. |
| `dynamic_analysis_unsafe` | **N/A** | Confirmed N/A: Python is memory-safe and there is no native code in this package. |
| `dynamic_analysis_enable_assertions` | **Met** | The suite is assertion-based; assertions stay enabled in tests. Confirmed: assertions are enabled during both the test suite and the fuzz job — Python is invoked without `-O` and `PYTHONOPTIMIZE` is unset, so the harness's invariant assertions are actually evaluated. |
| `dynamic_analysis_fixed` | **Met** | No unfixed medium+ findings. |

---

## Notes

- Any passing criterion not listed here is answerable **Met** by an existing
  rendered artefact or **N/A** (library vs. website/app). Check
  `SECURITY.md` / `CONTRIBUTING.md` / `ci.yml` before writing anything new.
- Silver (score 7) is generally **not** honestly reachable while a project is
  single-maintainer: `access_continuity` is a silver MUST requiring the project to
  survive the loss of any one person within a week, and `bus_factor`,
  `governance`, and `roles_responsibilities` share that root cause. A second
  person with org access and release capability resolves all four and also moves
  Scorecard's Code-Review check off 0. See the silver sheet for how the reference
  project answered these via organisational continuity rather than a lone
  maintainer.
