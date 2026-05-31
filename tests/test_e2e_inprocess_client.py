"""End-to-end test via the SDK's in-process MCP test client.

Uses ``mcp.shared.memory.create_connected_server_and_client_session`` to
connect a ClientSession to the FastMCP server over in-memory anyio streams —
no subprocess, no stdio.
"""

from __future__ import annotations

import json

import pytest
from mcp.shared.memory import create_connected_server_and_client_session

from presidio_x402_mcp.server import mcp


class TestInProcessClient:
    @pytest.mark.anyio
    async def test_lists_three_tools(self):
        async with create_connected_server_and_client_session(mcp) as client:
            result = await client.list_tools()
            names = {t.name for t in result.tools}
            assert names == {
                "screen_payment_metadata",
                "check_payment_policy",
                "check_payment_replay",
            }

    @pytest.mark.anyio
    async def test_call_screen_redacts_email_via_client(self):
        async with create_connected_server_and_client_session(mcp) as client:
            result = await client.call_tool(
                "screen_payment_metadata",
                arguments={
                    "resource_url": "https://api.example.com/u/jane@example.com",
                    "description": "monthly fee",
                    "reason": "",
                },
            )
            # v1.27.2 exposes camelCase attribute names; v2 will switch to snake_case.
            assert result.isError is False
            body = json.loads(result.content[0].text)
            assert "<EMAIL_ADDRESS>" in body["redacted_resource_url"]
            assert any(f["entity_type"] == "EMAIL_ADDRESS" for f in body["entities_found"])
