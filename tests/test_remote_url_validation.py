"""Audit finding #1 (Medium, 2026-06-03): the remote screening endpoint was not
required to be HTTPS.

`PRESIDIO_X402_MCP_REMOTE_BASE_URL` was taken verbatim from the environment, so an
`http://` value — a typo, or a local testing config promoted to production — put
the pre-redaction `resource_url` / `description` / `reason` and the long-lived
`X-API-Key` on the wire in cleartext. That inverts the purpose of the tool.
"""

from __future__ import annotations

import os
import subprocess
import sys

import pytest

from presidio_x402_mcp.server import _validate_remote_base_url


class TestAcceptedUrls:
    @pytest.mark.parametrize(
        "url",
        [
            "https://screen.presidio-group.eu",
            "https://screen.presidio-group.eu/",
            "https://screen.presidio-group.eu:8443/base",
            "HTTPS://screen.presidio-group.eu",  # urlparse lowercases the scheme
        ],
    )
    def test_https_is_accepted(self, url):
        assert _validate_remote_base_url(url) == url

    @pytest.mark.parametrize(
        "url",
        [
            "http://localhost:8080",
            "http://127.0.0.1:8080",
            "http://[::1]:8080",
        ],
    )
    def test_loopback_over_http_is_accepted(self, url):
        """Traffic that never leaves the host has no network path to intercept."""
        assert _validate_remote_base_url(url) == url


class TestRejectedUrls:
    @pytest.mark.parametrize(
        "url",
        [
            "http://screen.presidio-group.eu",  # the typo this exists to catch
            "http://10.0.0.5:8080",  # private, but still on a network
            "http://localhost.evil.example.com",  # prefix-match trap
            "http://127.0.0.1.evil.example.com",  # ditto
            "screen.presidio-group.eu",  # no scheme at all
            "ftp://screen.presidio-group.eu",
            "file:///etc/passwd",
            "",
        ],
    )
    def test_non_tls_is_refused(self, url):
        with pytest.raises(ValueError, match="must use https://"):
            _validate_remote_base_url(url)

    def test_error_names_the_variable_and_says_why(self):
        """The operator has to be able to act on this without reading the source."""
        with pytest.raises(ValueError) as exc:
            _validate_remote_base_url("http://screen.presidio-group.eu")
        message = str(exc.value)
        assert "PRESIDIO_X402_MCP_REMOTE_BASE_URL" in message
        assert "pre-redaction PII" in message

    def test_failure_is_loud_not_a_silent_downgrade(self):
        """Falling back to in-process screening would leave the operator believing
        metadata is screened remotely under their configured policy."""
        with pytest.raises(ValueError):
            _validate_remote_base_url("http://screen.presidio-group.eu")


class TestStartupIsFailClosed:
    """The helper is only half the guarantee — the module must actually apply it
    at import, before any tool call can reach the network."""

    @staticmethod
    def _import_with(env_value: str) -> subprocess.CompletedProcess:
        env = dict(os.environ)
        env["PRESIDIO_X402_MCP_REMOTE_BASE_URL"] = env_value
        env["PRESIDIO_X402_MCP_REMOTE_API_KEY"] = "test-key"
        return subprocess.run(
            [sys.executable, "-c", "import presidio_x402_mcp.server"],
            env=env,
            capture_output=True,
            text=True,
        )

    def test_plain_http_endpoint_stops_the_server(self):
        result = self._import_with("http://screen.presidio-group.eu")
        assert result.returncode != 0, "server started against a cleartext endpoint"
        assert "must use https://" in result.stderr

    def test_https_endpoint_starts_normally(self):
        result = self._import_with("https://screen.presidio-group.eu")
        assert result.returncode == 0, result.stderr
