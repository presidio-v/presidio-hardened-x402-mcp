"""Tests for screen_payment_metadata tool — in-process and HTTP-proxy modes."""

from __future__ import annotations

import httpx
import pytest
import respx

from presidio_x402_mcp import server as srv
from presidio_x402_mcp.server import screen_payment_metadata


class TestInProcess:
    @pytest.mark.anyio
    async def test_clean_payload_returns_no_findings(self):
        result = await screen_payment_metadata(
            resource_url="https://api.example.com/v1/data",
            description="monthly subscription",
            reason="enterprise plan",
        )
        assert result["entities_found"] == []
        assert result["mode"] == "in_process"
        assert result["redacted_resource_url"] == "https://api.example.com/v1/data"

    @pytest.mark.anyio
    async def test_email_in_url_detected_and_tagged_to_resource_url(self):
        result = await screen_payment_metadata(
            resource_url="https://api.example.com/u/jane@example.com",
            description="",
            reason="",
        )
        assert any(
            f["entity_type"] == "EMAIL_ADDRESS" and f["field"] == "resource_url"
            for f in result["entities_found"]
        )
        assert "jane@example.com" not in result["redacted_resource_url"]
        assert "<EMAIL_ADDRESS>" in result["redacted_resource_url"]

    @pytest.mark.anyio
    async def test_email_in_description_tagged_to_description_field(self):
        result = await screen_payment_metadata(
            resource_url="https://api.example.com/x",
            description="contact alice@test.org for invoice",
            reason="",
        )
        assert any(
            f["entity_type"] == "EMAIL_ADDRESS" and f["field"] == "description"
            for f in result["entities_found"]
        )

    @pytest.mark.anyio
    async def test_ssn_detected_in_description(self):
        result = await screen_payment_metadata(
            resource_url="https://api.example.com/x",
            description="SSN: 123-45-6789",
            reason="",
        )
        assert any(f["entity_type"] == "US_SSN" for f in result["entities_found"])

    @pytest.mark.anyio
    async def test_oversize_resource_url_rejected(self):
        with pytest.raises(ValueError, match="resource_url exceeds"):
            await screen_payment_metadata(
                resource_url="https://x.com/" + "a" * 3000,
                description="",
                reason="",
            )

    @pytest.mark.anyio
    async def test_oversize_description_rejected(self):
        with pytest.raises(ValueError, match="description exceeds"):
            await screen_payment_metadata(
                resource_url="https://x.com/x",
                description="x" * 5000,
                reason="",
            )

    @pytest.mark.anyio
    async def test_entities_whitelist_narrows_results(self):
        result = await screen_payment_metadata(
            resource_url="https://api.example.com/x",
            description="email: bob@example.com phone: 555-123-4567",
            reason="",
            entities=["EMAIL_ADDRESS"],
        )
        types = {f["entity_type"] for f in result["entities_found"]}
        assert "EMAIL_ADDRESS" in types
        assert "PHONE_NUMBER" not in types


class TestRemoteMode:
    def setup_method(self):
        srv._REMOTE_BASE_URL = "https://screen.test.local"
        srv._REMOTE_API_KEY = "test-key"
        srv._REMOTE_ENABLED = True

    def teardown_method(self):
        srv._REMOTE_BASE_URL = None
        srv._REMOTE_API_KEY = None
        srv._REMOTE_ENABLED = False

    @pytest.mark.anyio
    @respx.mock
    async def test_remote_success_returns_wire_response_with_field_attribution(self):
        respx.post("https://screen.test.local/v1/screen").mock(
            return_value=httpx.Response(
                200,
                json={
                    "redacted_resource_url": "https://api.foo.com/u/<EMAIL_ADDRESS>",
                    "redacted_description": "test",
                    "redacted_reason": "",
                    "entities_found": [
                        {
                            "entity_type": "EMAIL_ADDRESS",
                            "field": "resource_url",
                            "count": 1,
                        },
                    ],
                    "screening_id": "sc_x",
                    "tier": "free",
                    "audit_token": None,
                    "screened_at": "2026-05-31T00:00:00.000Z",
                },
            )
        )
        result = await screen_payment_metadata(
            resource_url="https://api.foo.com/u/jane@example.com",
            description="test",
            reason="",
        )
        assert result["mode"] == "remote"
        assert result["redacted_resource_url"] == "https://api.foo.com/u/<EMAIL_ADDRESS>"
        assert result["entities_found"][0]["field"] == "resource_url"

    @pytest.mark.anyio
    @respx.mock
    async def test_remote_401_returns_auth_error(self):
        respx.post("https://screen.test.local/v1/screen").mock(
            return_value=httpx.Response(401, json={"error_code": "INVALID_API_KEY"})
        )
        result = await screen_payment_metadata(
            resource_url="https://api.foo.com/x", description="", reason=""
        )
        assert result["error"] == "auth_error"
        assert result["mode"] == "remote"

    @pytest.mark.anyio
    @respx.mock
    async def test_remote_429_returns_rate_limit_with_retry_after(self):
        respx.post("https://screen.test.local/v1/screen").mock(
            return_value=httpx.Response(
                429,
                headers={"Retry-After": "60"},
                json={"error_code": "RATE_LIMIT_EXCEEDED"},
            )
        )
        result = await screen_payment_metadata(
            resource_url="https://api.foo.com/x", description="", reason=""
        )
        assert result["error"] == "rate_limit"
        assert result["retry_after"] == 60
        assert result["mode"] == "remote"

    @pytest.mark.anyio
    @respx.mock
    async def test_remote_5xx_returns_unavailable(self):
        respx.post("https://screen.test.local/v1/screen").mock(return_value=httpx.Response(503))
        result = await screen_payment_metadata(
            resource_url="https://api.foo.com/x", description="", reason=""
        )
        assert result["error"] == "unavailable"
        assert result["mode"] == "remote"

    @pytest.mark.anyio
    @respx.mock
    async def test_remote_network_error_returns_unavailable(self):
        respx.post("https://screen.test.local/v1/screen").mock(
            side_effect=httpx.ConnectError("conn refused")
        )
        result = await screen_payment_metadata(
            resource_url="https://api.foo.com/x", description="", reason=""
        )
        assert result["error"] == "unavailable"
        assert result["mode"] == "remote"


class TestPercentEncodedPII:
    """The parent floor of 0.11.1 exists for this.

    Through parent v0.11.0 the filter missed percent-encoded PII entirely, so an
    address arriving as `alice%40example.com` in a resource URL was handed back
    to the agent unredacted. `resource_url` is by construction a URL, which makes
    it the likeliest place for that encoding to show up. These tests fail against
    any parent below 0.11.1.
    """

    @pytest.mark.anyio
    @pytest.mark.parametrize(
        "url",
        [
            "https://api.example.com/u/alice.martin%40example.com/exports",
            "https://api.example.com/records?user=alice.martin%40example.com",
            "https://api.example.com/u/alice%2Emartin%40example%2Ecom",
            "https://api.example.com/u/alice.martin%2540example.com",
        ],
    )
    async def test_percent_encoded_email_is_detected_and_redacted(self, url):
        result = await screen_payment_metadata(resource_url=url, description="", reason="")
        assert any(
            f["entity_type"] == "EMAIL_ADDRESS" and f["field"] == "resource_url"
            for f in result["entities_found"]
        ), f"percent-encoded address survived screening: {url}"
        assert "alice" not in result["redacted_resource_url"]

    @pytest.mark.anyio
    async def test_benign_escapes_are_not_rewritten(self):
        """Decoding is for matching only — the agent gets its own bytes back.

        `%2F` is not `/`; rewriting escapes would change the URL's meaning.
        """
        url = "https://api.example.com/a%2Fb/search?q=hello%20world"
        result = await screen_payment_metadata(resource_url=url, description="", reason="")
        assert result["entities_found"] == []
        assert result["redacted_resource_url"] == url
