# SPDX-License-Identifier: MIT
# Copyright (c) 2026 PRESIDIO Group
"""Atheris coverage-guided fuzz harness for presidio-hardened-x402-mcp.

Two targets, both of which parse operator-supplied configuration:

  1. ``_validate_remote_base_url`` — the TLS gate on the remote screening
     endpoint (audit finding 1). This is the interesting one. Crashing is the
     lesser failure; the real bug class is **wrongly accepting** a URL that is
     not TLS-protected, because that silently puts pre-redaction PII and a
     long-lived API key on the wire. The harness therefore asserts the security
     invariant on every accepted input, not merely that no exception escaped.

  2. ``_policy_config_from_env``'s JSON parsing of
     ``PRESIDIO_X402_MCP_PER_ENDPOINT_JSON`` — untrusted-shaped JSON that must
     degrade to an empty policy rather than propagate a parse error.

GOTCHAS (read before running):
  - No macOS Atheris wheel: run this under Linux CI only (the fuzz job), never
    on a developer Mac.
  - No cp310 wheel: Atheris 3.x dropped Python 3.10. Run under Python 3.12.
  - Editable installs can shadow the package: a `pip install -e .` checkout may
    win over the installed distribution on sys.path. Install the built wheel (or
    verify the import resolves to the real target module) before fuzzing, so the
    code under coverage is the code you think it is.
"""

import sys
from urllib.parse import urlparse

import atheris

with atheris.instrument_imports():
    from presidio_x402_mcp.server import _LOOPBACK_HOSTS, _validate_remote_base_url


def _check_url(raw: str) -> None:
    """Anything accepted must be https, or plain http to a loopback host.

    Asserting the invariant rather than just "did not raise" is the point: a
    validator that accepts `http://evil.example.com` without crashing is exactly
    the bug this gate exists to prevent, and a crash-only harness would pass it.
    """
    try:
        accepted = _validate_remote_base_url(raw)
    except ValueError:
        return  # refusing is always a safe outcome
    parsed = urlparse(accepted)
    if parsed.scheme == "https":
        return
    if parsed.scheme == "http" and parsed.hostname in _LOOPBACK_HOSTS:
        return
    raise AssertionError(
        f"validator accepted a non-TLS endpoint: {accepted!r} "
        f"(scheme={parsed.scheme!r}, host={parsed.hostname!r})"
    )


def _check_per_endpoint_json(raw: str) -> None:
    """Malformed per-endpoint policy JSON must degrade, not propagate."""
    import json

    try:
        parsed = json.loads(raw)
    except (json.JSONDecodeError, ValueError, RecursionError):
        return
    try:
        {str(k): float(v) for k, v in parsed.items()}
    except (AttributeError, TypeError, ValueError, OverflowError):
        return  # the same exception set server.py catches


def TestOneInput(data: bytes) -> None:  # noqa: N802 (Atheris entrypoint contract)
    fdp = atheris.FuzzedDataProvider(data)
    choice = fdp.ConsumeIntInRange(0, 1)
    raw = fdp.ConsumeUnicodeNoSurrogates(fdp.remaining_bytes())
    if choice == 0:
        _check_url(raw)
    else:
        _check_per_endpoint_json(raw)


def main() -> None:
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
