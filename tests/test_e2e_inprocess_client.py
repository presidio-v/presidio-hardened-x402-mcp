"""End-to-end test via the SDK's in-process MCP client.

Uses ``mcp.Client``, which accepts an ``MCPServer`` instance directly and
routes the session over the SDK's in-memory transport — no subprocess,
no stdio.
"""

from __future__ import annotations

import json

import pytest
from mcp import Client

from presidio_x402_mcp.server import mcp


class TestInProcessClient:
    @pytest.mark.anyio
    async def test_lists_three_tools(self):
        async with Client(mcp) as client:
            result = await client.list_tools()
            names = {t.name for t in result.tools}
            assert names == {
                "screen_payment_metadata",
                "check_payment_policy",
                "check_payment_replay",
            }

    @pytest.mark.anyio
    async def test_call_screen_redacts_email_via_client(self):
        async with Client(mcp) as client:
            result = await client.call_tool(
                "screen_payment_metadata",
                arguments={
                    "resource_url": "https://api.example.com/u/jane@example.com",
                    "description": "monthly fee",
                    "reason": "",
                },
            )
            assert result.is_error is False
            body = json.loads(result.content[0].text)
            assert "<EMAIL_ADDRESS>" in body["redacted_resource_url"]
            assert any(f["entity_type"] == "EMAIL_ADDRESS" for f in body["entities_found"])
