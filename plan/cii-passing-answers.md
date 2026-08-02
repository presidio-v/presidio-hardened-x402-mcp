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
| `description_good` | **Met** | `REPO#readme` — README opens with what `presidio-hardened-x402-mcp` does and the problem it solves. <!-- FILL:description-good — confirm the README's first paragraph actually states purpose + problem; adjust if not. --> |
| `interact` | **Met** | `REPO#readme` — README covers obtaining (presidio_x402_mcp on the package index), feedback (issues), security reports (`SECURITY.md`), and contributing. |
| `contribution` | **Met** | URL: `REPO/blob/main/CONTRIBUTING.md` — documents the fork → branch → PR flow against `main`. |
| `contribution_requirements` | **Met** | URL: `REPO/blob/main/CONTRIBUTING.md#requirements-for-acceptable-contributions` — style config, test policy, security-change rules, dependency bar. |

## Basics — FLOSS license

| Criterion | Status | Justification / URL |
|---|---|---|
| `floss_license` | **Met** | `MIT`. |
| `floss_license_osi` | **Met** | `MIT` is OSI-approved. <!-- FILL:license-osi — confirm the chosen license is on the OSI list (MIT/Apache-2.0/BSD/GPL all qualify); if not, this is Unmet. --> |
| `license_location` | **Met** | URL: `REPO/blob/main/LICENSE` |

## Basics — documentation

| Criterion | Status | Justification / URL |
|---|---|---|
| `documentation_basics` | **Met** | README plus `docs/`. <!-- FILL:documentation-basics — name the actual docs that cover installation and basic use for THIS project. --> |
| `documentation_interface` | **Met** | README API section; the public interface is documented and, for a library, enumerated in `SEMVER.md` (`presidio_x402_mcp.__all__` or equivalent). <!-- FILL:documentation-interface — point at where the external interface is actually documented. --> |

## Basics — other

| Criterion | Status | Justification / URL |
|---|---|---|
| `sites_https` | **Met** | GitHub and the package index are HTTPS. <!-- FILL:sites-https — if the project runs any hosted site/service, confirm it is HTTPS too and name it. --> |
| `discussion` | **Met** | GitHub Issues: `REPO/issues` — searchable, URL-addressable, open, no proprietary client. |
| `english` | **Met** | All docs and issue handling in English. |
| `maintained` | **Met** | Actively maintained. <!-- FILL:maintained — cite the most recent release/version and its date as evidence of activity. --> |

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
| `release_notes_vulns` | **Met** | CHANGELOG names each CVE/GHSA fixed. <!-- FILL:release-notes-vulns — list the specific advisories this project's changelog records, or set N/A if no security-relevant releases have shipped yet. --> |

## Reporting — bug reports

| Criterion | Status | Justification / URL |
|---|---|---|
| `report_process` | **Met** | URL: `REPO/blob/main/CONTRIBUTING.md#reporting-bugs-and-requesting-features` |
| `report_tracker` | **Met** | GitHub Issues. |
| `report_responses` | **Met** | <!-- FILL:report-responses — cite 2–3 real issues opened in the last ~6 months that received a maintainer response (numbers, open/close dates). If the project is brand new with no external reports, say so honestly and note it is Met by the documented process. --> |
| `enhancement_responses` | **Met** | <!-- FILL:enhancement-responses — cite real enhancement/feature requests and how they were answered, or note none received yet. --> |
| `report_archive` | **Met** | URL: `REPO/issues?q=is%3Aissue` — public and searchable. |

## Reporting — vulnerability reports

| Criterion | Status | Justification / URL |
|---|---|---|
| `vulnerability_report_process` | **Met** | URL: `REPO/blob/main/SECURITY.md#reporting-a-vulnerability` |
| `vulnerability_report_private` | **Met** | URL: `REPO/blob/main/SECURITY.md#reporting-a-vulnerability` — private GitHub Security Advisory via the Security tab; acknowledgement and patch targets stated. |
| `vulnerability_report_response` | **N/A** | <!-- FILL:vulnerability-report-response — DEFAULT N/A: no externally reported vulnerabilities in the last 6 months. Confirm zero advisories filed; if any were reported, switch to Met and describe the response timeline. --> |

## Quality — build system

| Criterion | Status | Justification / URL |
|---|---|---|
| `build` | **Met** | <!-- FILL:build — name the standard build entry point for python (e.g. a PEP 517 build, `make`, `cargo build`) that rebuilds from source. --> |
| `build_common_tools` | **Met** | Built with common, widely available tools. <!-- FILL:build-common-tools — name them. --> |
| `build_floss_tools` | **Met** | The entire toolchain is FLOSS. |

## Quality — automated test suite

| Criterion | Status | Justification / URL |
|---|---|---|
| `test` | **Met** | Test suite under `tests/`, licensed with the project. How to run: `CONTRIBUTING.md#local-verification` and `.github/workflows/ci.yml`. <!-- FILL:test — state how many test modules/how the suite is organised for THIS project. --> |
| `test_invocation` | **Met** | <!-- FILL:test-invocation — the one standard command that runs the tests (e.g. `pytest tests/`, `cargo test`, `npm test`). --> |
| `test_most` | **Met** | <!-- FILL:test-most — cite the coverage gate (e.g. `--cov-fail-under=90`) and any end-to-end suite; state the actual enforced floor. --> |
| `test_continuous_integration` | **Met** | GitHub Actions on every push and PR (`.github/workflows/ci.yml`). <!-- FILL:test-ci — note the version/platform matrix. --> |

## Quality — new functionality testing

| Criterion | Status | Justification / URL |
|---|---|---|
| `test_policy` | **Met** | URL: `REPO/blob/main/CONTRIBUTING.md#tests` — written policy that functional changes ship with tests and fixes ship with regression tests. |
| `tests_are_added` | **Met** | <!-- FILL:tests-are-added — give ONE worked example: a real PR that shipped its test in the same change (the bug fixed + the test added). This is the single most-scrutinised passing row; make it concrete. --> |
| `tests_documented_added` | **Met** | The policy is stated in the contribution instructions themselves (`CONTRIBUTING.md#tests`). |

## Quality — warning flags

| Criterion | Status | Justification / URL |
|---|---|---|
| `warnings` | **Met** | Lint/warnings enforced in CI. <!-- FILL:warnings — name the linter/compiler-warning setup for python. --> |
| `warnings_fixed` | **Met** | CI fails on any finding; `main` is clean. |
| `warnings_strict` | **Met** | <!-- FILL:warnings-strict — list the enabled rule sets and any documented exclusions; show they exceed defaults. --> |

## Security — secure development knowledge

| Criterion | Status | Justification / URL |
|---|---|---|
| `know_secure_design` | **Met** | <!-- FILL:know-secure-design — argue the maintainer knows secure design: least privilege, fail-closed defaults, defence in depth, documented trust boundaries as applied in THIS project. Cite any external review. --> |
| `know_common_errors` | **Met** | <!-- FILL:know-common-errors — cite the documented threat model / attack classes this project defends (injection, SSRF, etc.) and their named countermeasures. --> |

## Security — cryptographic practices

<!-- If this project performs NO cryptographic operations of its own, most of these
are N/A — say so explicitly per row rather than leaving them blank. If it does,
resolve each FILL against the actual primitives used. -->

| Criterion | Status | Justification / URL |
|---|---|---|
| `crypto_published` | **Met** | <!-- FILL:crypto-published — list the published algorithms used (e.g. SHA-256, HMAC-SHA256, Ed25519), or N/A if none. --> |
| `crypto_call` | **Met** | <!-- FILL:crypto-call — name the vetted library calls (no primitive re-implemented), or N/A. --> |
| `crypto_floss` | **Met** | The crypto libraries used are FLOSS. <!-- FILL:crypto-floss — confirm or N/A. --> |
| `crypto_keylength` | **Met** | <!-- FILL:crypto-keylength — state key/digest sizes meet NIST 2030 minimums, or N/A. --> |
| `crypto_working` | **Met** | No MD4, MD5, single DES, RC4, or Dual_EC_DRBG. <!-- FILL:crypto-working — confirm for this codebase, or N/A. --> |
| `crypto_weaknesses` | **Met** | No SHA-1 and no CBC-mode dependency in default paths. <!-- FILL:crypto-weaknesses — confirm, or N/A. --> |
| `crypto_pfs` | **N/A** | Implements no key-agreement protocol of its own; transport PFS is provided by TLS in the network layer. <!-- FILL:crypto-pfs — confirm this default holds. --> |
| `crypto_password_storage` | **N/A** | Stores no external-user passwords. <!-- FILL:crypto-password-storage — confirm this default holds. --> |
| `crypto_random` | **Met** | <!-- FILL:crypto-random — cite the CSPRNG call (e.g. `secrets.token_bytes`) and where, or N/A if no security-relevant randomness. --> |

## Security — delivery

| Criterion | Status | Justification / URL |
|---|---|---|
| `delivery_mitm` | **Met** | Distributed over HTTPS via the package index and GitHub. <!-- FILL:delivery-mitm — note the publish path (e.g. Trusted Publishing / OIDC, no long-lived token) if applicable. --> |
| `delivery_unsigned` | **Met** | No hash is fetched over plain HTTP. Release tags are SSH-signed and GitHub-verified. |

## Security — known vulnerabilities

| Criterion | Status | Justification / URL |
|---|---|---|
| `vulnerabilities_fixed_60_days` | **Met** | No known unpatched medium+ vulnerabilities. Dependabot plus dependency audit in CI. <!-- FILL:vulnerabilities-60-days — name the audit tool for python. --> |
| `vulnerabilities_critical_fixed` | **Met** | Recent dependency criticals were closed by floor bumps within days. <!-- FILL:vulnerabilities-critical — confirm, or state none have arisen. --> |

## Security — other

| Criterion | Status | Justification / URL |
|---|---|---|
| `no_leaked_credentials` | **Met** | <!-- FILL:no-leaked-credentials — VERIFY: no `.env`, `.pem`, key, or credential-shaped file appears anywhere in this repo's history. Run a history scan before answering Met. --> |

## Analysis — static

| Criterion | Status | Justification / URL |
|---|---|---|
| `static_analysis` | **Met** | CodeQL (results uploaded to GitHub code scanning), `.github/workflows/codeql.yml`. <!-- FILL:static-analysis — add the language-specific second pass (e.g. bandit for Python). --> |
| `static_analysis_common_vulnerabilities` | **Met** | CodeQL's security query suite targets common vulnerability classes. <!-- FILL:static-analysis-cve — name any additional in-line security linting. --> |
| `static_analysis_fixed` | **Met** | Findings are triaged and fixed before release. |
| `static_analysis_often` | **Met** | CodeQL runs on every push and PR to `main`, plus a weekly scheduled run. |

## Analysis — dynamic

| Criterion | Status | Justification / URL |
|---|---|---|
| `dynamic_analysis` | **Met** | <!-- FILL:dynamic-analysis — describe the fuzz/dynamic harness for THIS project (what functions, which tool, where it runs). If none yet, this is a SHOULD-adjacent gap — either add one or answer honestly. --> |
| `dynamic_analysis_unsafe` | **N/A** | <!-- FILL:dynamic-analysis-unsafe — DEFAULT N/A if python is memory-safe; if the project has a memory-unsafe component, describe the tooling used against it. --> |
| `dynamic_analysis_enable_assertions` | **Met** | The suite is assertion-based; assertions stay enabled in tests. <!-- FILL:dynamic-analysis-assertions — confirm for this suite. --> |
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
