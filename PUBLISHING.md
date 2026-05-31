# Publishing

This package is published to PyPI via [Trusted Publishing](https://docs.pypi.org/trusted-publishers/) (OIDC). No API tokens or repository secrets are involved.

## One-time PyPI setup (before the first release)

Done once by an account with permission to register a new PyPI project.

1. Sign in to [PyPI](https://pypi.org).
2. Go to <https://pypi.org/manage/account/publishing/>.
3. Under **"Add a new pending publisher"**, fill in:
   - **PyPI Project Name:** `presidio-hardened-x402-mcp`
   - **Owner:** `presidio-v`
   - **Repository name:** `presidio-hardened-x402-mcp`
   - **Workflow name:** `release.yml`
   - **Environment name:** `pypi`
4. Click **Add**. The pending publisher is now armed and will activate when the first release workflow run completes.

## One-time GitHub environment setup

In the repo, go to **Settings → Environments → New environment**:

1. Name: `pypi`
2. **Required reviewers — MUST be set.** Add at least one maintainer. The reviewer
   gate is the only thing between a pushed `v*.*.*` tag and a real PyPI publish; without
   it, anyone who can create a release tag (a compromised CI bot, a stolen contributor
   credential, a misclicked tag) can publish a version with no human check. For a
   security-tooling package, treat this as non-optional.
3. Save.

## Guarding the trust relationship

Once the pending publisher activates, the binding is `(PyPI project, GitHub org, repo,
workflow filename, environment name)`. Changes to any of those break the binding and
PyPI will reject the publish:

- Don't rename `release.yml`, the `pypi` environment, or the repo without re-registering
  the publisher on PyPI.
- The PyPI-side publisher list (`pypi.org/manage/account/publishing/`) is itself a
  high-value target. Anyone with PyPI account access could swap the trust relationship
  to a malicious fork. Audit the PyPI publisher list when reviewing the GitHub repo
  permissions list.

## Cutting a release

1. Bump `version` in `pyproject.toml` and `server.json`, update `CHANGELOG.md`, open a PR, get it green, merge.
2. Tag and push:
   ```bash
   git tag v0.1.0
   env -u GITHUB_TOKEN git push origin v0.1.0
   ```
3. The `Release to PyPI` workflow runs automatically on tag push. It:
   - Builds the sdist + wheel via `uv build`.
   - Uploads artifacts.
   - Publishes to PyPI using the trusted-publisher OIDC token.
4. If the `pypi` environment has required reviewers, approve the run from the Actions tab.
5. Verify the release lands at <https://pypi.org/project/presidio-hardened-x402-mcp/>.

## Sanity check before tagging

```bash
# Verify clean working tree, all CI green on main, and the package builds:
git status
uv build
ls -la dist/
unzip -l dist/presidio_hardened_x402_mcp-*.whl
```

## Rollback / yank

PyPI does not allow re-uploading the same version. To pull a broken release:

1. **Yank** at <https://pypi.org/project/presidio-hardened-x402-mcp/>. Yanked versions stay downloadable but are excluded from `pip install` without an explicit version pin.
2. Cut a fixed `0.1.x` (or `0.x.x+1`) release via the normal workflow above.
