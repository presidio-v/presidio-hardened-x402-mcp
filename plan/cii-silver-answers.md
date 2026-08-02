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
<https://www.bestpractices.dev/en/projects/0>. It covers
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
[![OpenSSF Best Practices](https://www.bestpractices.dev/projects/0/badge)](https://www.bestpractices.dev/projects/0)
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
| `governance` | **Met** | Governance model documented at `REPO/blob/main/GOVERNANCE.md` — decision-making, escalation, and security/API change rules. <!-- FILL:governance — confirm GOVERNANCE.md describes the actual decision model for this project. --> |
| `roles_responsibilities` | **Met** | Key roles (steward org, maintainer, security contact, release manager, contributor) documented at `REPO/blob/main/GOVERNANCE.md#roles-and-responsibilities`. |
| `access_continuity` | **Met** | <!-- FILL:access-continuity — This is a silver MUST. Argue continuity is a property of the STEWARD ORGANISATION, not one person. The reference project cited: repo owned by a GitHub org (not a personal account); package publishing via Trusted Publishing/OIDC bound to the org repo + a gated release environment (no personal token that dies with an individual); release signing key held in the org password manager and recoverable; release process fully documented; more than one person able to assume each role. Adapt to THIS project's actual custody arrangements — do not claim org continuity the project does not have. --> URL: `REPO/blob/main/GOVERNANCE.md#project-continuity`. |
| `bus_factor` (SHOULD) | **Met** | <!-- FILL:bus-factor — argue more than one person can assume the maintainer, security-contact, and release-manager roles and that release credentials are org-held and recoverable (not tied to one machine). If genuinely single-maintainer with no org backing, this is honestly Unmet — say so; it is a SHOULD, not a blocker. --> See `REPO/blob/main/GOVERNANCE.md#project-continuity`. |

## Documentation

| Criterion | Status | Justification to paste |
|---|---|---|
| `documentation_roadmap` | **Met** | `REPO#roadmap` includes a "Planned direction (next 12 months)" section. <!-- FILL:documentation-roadmap — confirm the README roadmap names real intended work for this project. --> |
| `documentation_architecture` | **Met** | `REPO/blob/main/ARCHITECTURE.md` — components, core-flow pipeline, and trust boundaries; linked from the README. |
| `documentation_security` | **Met** | `REPO/blob/main/SECURITY.md` documents the security controls, threat model, and reporting process; `ARCHITECTURE.md#trust-boundaries` states the trust boundaries. <!-- FILL:documentation-security — point at where the full threat model / design rationale lives for this project. --> |
| `documentation_quick_start` | **Met** | README "Quick Start" (before/after example) plus `docs/`. <!-- FILL:documentation-quick-start — name the actual quick-start material. --> |
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
| `automated_integration_testing` | **Met** | `REPO/blob/main/.github/workflows/ci.yml` runs the full suite on every push and pull request. <!-- FILL:automated-integration-testing — note the version/platform matrix and any partner/end-to-end suite. --> |
| `regression_tests_added50` | **Met** | Policy requires a regression test with every bug fix. <!-- FILL:regression-tests-50 — cite one worked example and confirm >50% of bugs fixed in the last 6 months carry a regression test. --> |
| `test_statement_coverage80` | **Met** | <!-- FILL:coverage80 — cite the enforced coverage gate (e.g. `--cov-fail-under=90` in `ci.yml` / build config) showing statement coverage ≥80%. --> |
| `warnings_strict` | **Met** | <!-- FILL:warnings-strict — list the enabled lint rule sets (incl. security rules) and that CI fails on any finding. --> |
| `coding_standards` | **Met** | `REPO/blob/main/CONTRIBUTING.md#style` names the required style/lint tool; config in the project's build/lint config. <!-- FILL:coding-standards — name the tool. --> |
| `coding_standards_enforced` | **Met** | The style/lint check runs in CI on every PR (FLOSS enforcement). |
| `installation_common` | **Met** | Standard install from the package index. <!-- FILL:installation-common — give the one-line install command for presidio_x402_mcp. --> |
| `installation_development_quick` | **Met** | `REPO/blob/main/CONTRIBUTING.md#local-verification` — documents the one setup path that installs everything needed to build and test. |
| `build_repeatable` (SHOULD) | **Met** | Artefacts are built via the standard flow against a fully pinned dependency graph on GitHub-hosted runners with SHA-pinned Actions; the build is deterministic from pinned sources. <!-- FILL:build-repeatable — confirm the lockfile and pinning; do NOT claim bit-for-bit hermetic reproducibility unless it is actually true. --> |
| `build_standard_variables` | **N/A** | <!-- FILL:build-standard-variables — DEFAULT N/A for a pure-python package with no compiler/linker; if the project compiles native code, describe `CC`/`CFLAGS`/`LDFLAGS` handling instead. --> |
| `build_preserve_debug` | **N/A** | <!-- FILL:build-preserve-debug — DEFAULT N/A if there are no compiled artefacts; otherwise describe separable debug info. --> |
| `build_non_recursive` | **N/A** | <!-- FILL:build-non-recursive — DEFAULT N/A if there is no recursive make/subdirectory build; otherwise confirm the build is non-recursive. --> |
| `installation_standard_variables` | **N/A** | <!-- FILL:installation-standard-variables — DEFAULT N/A if installed via a language package manager (pip/uv/cargo/npm); `DESTDIR`-style conventions do not apply. --> |

## Dependencies & components

| Criterion | Status | Justification to paste |
|---|---|---|
| `external_dependencies` | **Met** | Dependencies are listed machine-readably in the project manifest and fully pinned in a lockfile; a CycloneDX SBOM is generated per release in CI. <!-- FILL:external-dependencies — name the manifest and lockfile for python. --> |
| `updateable_reused_components` | **Met** | All reused components are standard package-index packages installed via the package manager (no vendored copies); Dependabot tracks updates. |
| `interfaces_current` | **Met** | Dependencies are kept current (Dependabot + dependency floors), the public API is tracked in `SEMVER.md`, and the code does not rely on deprecated FLOSS functions where alternatives exist. |

## Security

| Criterion | Status | Justification to paste |
|---|---|---|
| `assurance_case` | **Met** (URL required) | URL: `REPO/blob/main/ASSURANCE.md`. Consolidated assurance case with all four required parts (threat model, trust boundaries, secure-design-principles argument, common-implementation-weakness argument). <!-- FILL:assurance-case — confirm ASSURANCE.md is fully filled for THIS project (its own FILL markers resolved); the badge reviewer reads this document. --> |
| `implement_secure_design` | **Met** | <!-- FILL:implement-secure-design — argue this project applies: fail-safe defaults / secure by default, complete mediation, least privilege, defence in depth, economy of mechanism (vetted crypto primitives, no bespoke crypto). Ground each in a real control. See `REPO/blob/main/ARCHITECTURE.md` and `SECURITY.md`. --> |
| `input_validation` | **Met** | <!-- FILL:input-validation — state that data crossing the untrusted-input boundary is validated before use, with a concrete example from this codebase. See `ARCHITECTURE.md#trust-boundaries`. --> |
| `hardening` | **Met** | <!-- FILL:hardening — list the hardening measures actually applied (e.g. TLS enforced on egress, secret scrubbing in logs, SHA-pinned GitHub Actions, digest-pinned base images). --> |
| `crypto_weaknesses` | **Met** | <!-- FILL:crypto-weaknesses — security functions use strong algorithms only (e.g. SHA-256/HMAC-SHA256/Ed25519); no MD5/SHA-1/DES for security purposes. N/A if the project uses no crypto. --> |
| `crypto_algorithm_agility` (SHOULD) | **N/A** | <!-- FILL:crypto-algorithm-agility — DEFAULT for a library with no user-facing crypto-negotiation surface: primitives are pinned to current strong choices and algorithm migration is a versioned format change, not a runtime switch. Confirm this holds, or answer Met if the project genuinely negotiates suites. It is a SHOULD. --> |
| `crypto_credential_agility` | **Met** | <!-- FILL:crypto-credential-agility — confirm all keys/secrets are supplied from OUTSIDE the source tree and are rotatable without recompilation (env vars / deployment-supplied files), none hard-coded. N/A if no credentials. --> |
| `crypto_used_network` | **Met** | Network communication uses TLS. <!-- FILL:crypto-used-network — confirm, or N/A if the project makes no network calls. --> |
| `crypto_tls12` | **Met** | The HTTP client uses TLS ≥1.2. <!-- FILL:crypto-tls12 — confirm, or N/A. --> |
| `crypto_certificate_verification` | **Met** | TLS certificate verification is on by default; verification is not disabled. <!-- FILL:crypto-certificate-verification — confirm, or N/A. --> |
| `crypto_verification_private` | **Met** | Certificate verification precedes transmission of any private data. <!-- FILL:crypto-verification-private — confirm, or N/A. --> |
| `signed_releases` | **Met** | Releases are cryptographically signed and the process for obtaining/verifying keys is documented at `REPO/blob/main/SECURITY.md#obtaining-the-public-signing-keys`: build provenance attestation, SSH-signed git tags with the public key in `REPO/blob/main/allowed_signers`. <!-- FILL:signed-releases — confirm the signing methods actually in use for this project. --> |
| `version_tags_signed` | **Met** | Every release is a git tag, SSH-signed with the org key and shown as Verified on GitHub. |
| `sites_password_security` | **N/A** | <!-- FILL:sites-password-security — DEFAULT N/A: the project stores no user passwords. Confirm; if it runs a service that authenticates users, describe password storage instead. --> |

## Analysis & monitoring

| Criterion | Status | Justification to paste |
|---|---|---|
| `static_analysis_common_vulnerabilities` | **Met** | CodeQL (`REPO/blob/main/.github/workflows/codeql.yml`) and OpenSSF Scorecard run on every push/PR. <!-- FILL:static-analysis-cve — add the language-specific security linter (e.g. bandit via ruff `S` rules for Python). --> |
| `dynamic_analysis_unsafe` | **N/A** | <!-- FILL:dynamic-analysis-unsafe — DEFAULT N/A if python is memory-safe; note any fuzzing that runs regardless. If the project has a memory-unsafe component, describe the dynamic tooling used against it. --> |
| `dependency_monitoring` | **Met** | Dependabot + dependency audit in CI + OpenSSF Scorecard continuously check external dependencies for known vulnerabilities. |

## Accessibility & internationalization

| Criterion | Status | Justification to paste |
|---|---|---|
| `accessibility_best_practices` | **N/A** | <!-- FILL:accessibility — DEFAULT N/A for a developer library with no graphical or end-user UI. If the project ships a UI, this is NOT N/A — describe accessibility conformance instead. --> |
| `internationalization` | **N/A** | <!-- FILL:internationalization — DEFAULT N/A: the project has no user-facing localizable UI strings. Confirm; if it does, describe i18n support. --> |

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
