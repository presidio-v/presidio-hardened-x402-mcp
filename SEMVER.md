# Stability & semver guarantees — presidio-hardened-x402-mcp

For downstream integrators depending on this project.

## What is the public API

The public API of this project is **the MCP tool surface, not the Python module**:

- The three tool names — `screen_payment_metadata`, `check_payment_policy`,
  `check_payment_replay` — together with their argument names and the shape of the
  dict each returns, including the `error` discriminator values.
- The console entry point `presidio-hardened-x402-mcp`.
- The documented `PRESIDIO_X402_MCP_*` environment variables and their meanings.

Everything in `presidio_x402_mcp.server` is **internal**, including the names without a
leading underscore. Importing this package as a Python library is not a supported use;
it is a server, and it is consumed over MCP. Underscore-prefixed helpers such as
`_validate_remote_base_url` are referenced by the test and fuzz suites only.

## Versioning rules (semver, pre-1.0 profile)

- **Patch (0.x.Y):** bug fixes, security fixes, dependency floor bumps. No API
  change, no behaviour change except the fixed defect. Safe to auto-upgrade; this
  is the channel security releases ship on.
- **Minor (0.X.0):** additive API (new exports, new optional parameters with
  defaults, new optional extras). Existing code keeps working, including the
  documented public behaviour. Deprecations are announced here (docstring +
  CHANGELOG) at least one minor before any change.
- **Major (1.0.0+):** the only place deprecated surface may be removed.

**Pin guidance for integrators:** pin `presidio_x402_mcp` to the current minor
in production and run the verification step (below) in your CI on every upgrade.

## Behavioural guarantees (stronger than API stability)

These are security invariants, not just interfaces; weakening any of them is
treated as a breaking change regardless of which version component moves.

- **The gates record on call.** `check_payment_policy` consumes budget and
  `check_payment_replay` burns a fingerprint at the moment they are called. They are
  gates, not queries. Making either non-recording is a breaking change.
- **Remote screening never falls back to local.** On any auth, quota, or network
  failure the tool returns a structured `error` result. Silently degrading to
  in-process screening would hide that centralized audit was bypassed.
- **The remote endpoint must be TLS.** A non-`https` base URL (loopback excepted)
  stops the server at startup rather than being used.
- **stdout carries protocol frames only.** All diagnostics go to stderr. Writing
  anything else to stdout corrupts the JSON-RPC stream.
- **The parent lower bound is a security control.** It is raised to exclude parent
  releases with known defects and is not lowered for convenience.

## Verifying an installation

The project ships no self-check command. The recommended smoke test:

```bash
# 1. the server starts and speaks MCP
presidio-hardened-x402-mcp --help

# 2. the parent floor is satisfied (exit 0)
python -c "import importlib.metadata as m; v=tuple(int(x) for x in m.version('presidio-hardened-x402').split('.')[:3]); assert (0,11,1) <= v < (0,12,0), v"

# 3. a cleartext endpoint is refused (should FAIL to start)
PRESIDIO_X402_MCP_REMOTE_BASE_URL=http://example.com \
  PRESIDIO_X402_MCP_REMOTE_API_KEY=x \
  python -c "import presidio_x402_mcp.server"
```

Passing looks like: steps 1 and 2 exit 0, and step 3 exits non-zero with
`must use https://` on stderr. A step 3 that *succeeds* means the TLS gate is not
active and remote mode must not be used.

## Schema/wire stability

This project emits no on-disk schema of its own. Two external contracts it tracks:

- **The MCP tool-result dicts** it returns. Fields are additive-only within a minor
  line: new keys may appear, existing keys do not change meaning or disappear. The
  `error` discriminator values (`auth_error`, `rate_limit`, `unavailable`) are part of
  the contract.
- **The `screening-api` `/v1/screen` wire contract**, consumed in HTTP-proxy mode. The
  field-length limits here mirror that service's request model deliberately, so both
  entry points reject the same oversized input; they are kept in step by hand.

Audit records are written by the parent library and follow its schema, not one defined
here.

## Security response

See [SECURITY.md](SECURITY.md). Security fixes ship as patch releases on the
latest minor; any minimum-safe dependency floors are bumped in the same release.
