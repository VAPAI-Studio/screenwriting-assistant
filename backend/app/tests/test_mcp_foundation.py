"""Integration test for the mounted MCP server (Phase 55, MCPF-01..04).

Drives the in-process FastAPI app (with /mcp mounted) via the official mcp SDK
client over an httpx ASGI transport — no live server needed. Because the MCP
StreamableHTTPSessionManager.run() can only be entered once per instance (the
real server enters the app lifespan exactly once for its lifetime), all
assertions run inside a single lifespan entry:

  (a) the app boots under the composed lifespan with no task-group error,
  (b) a call with NO bearer is rejected,
  (c) a valid sa_ bearer round-trips initialize + tools/list + whoami,
  (d) request_count on the seeded key increments after an authenticated call.
"""

import hashlib
import uuid

import httpx
import pytest

from app.main import app, lifespan
from app.db import SessionLocal
from app.models.database import ApiKey as ApiKeyModel, User as UserModel


def _seed_key(token: str):
    """Create a User + active sa_ ApiKey in the app DB. Returns (user_id, key_id, email)."""
    db = SessionLocal()
    try:
        uid = str(uuid.uuid4())
        email = f"mcp_{uid[:8]}@example.com"
        db.add(UserModel(
            id=uid, email=email,
            hashed_password="fakehash", display_name="MCP Owner",
        ))
        db.flush()
        key = ApiKeyModel(
            user_id=uid, name="MCP Test Key", key_prefix=token[:8],
            key_hash=hashlib.sha256(token.encode()).hexdigest(),
        )
        db.add(key)
        db.commit()
        db.refresh(key)
        return uid, key.id, email
    finally:
        db.close()


def _read_request_count(key_id):
    db = SessionLocal()
    try:
        k = db.query(ApiKeyModel).filter(ApiKeyModel.id == key_id).first()
        return k.request_count if k else None
    finally:
        db.close()


def _http_client(token):
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://mcptest",
        headers=headers,
        timeout=httpx.Timeout(30.0),
    )


@pytest.mark.anyio
async def test_mcp_foundation_end_to_end():
    from mcp.client.streamable_http import streamable_http_client
    from mcp import ClientSession

    import app.main as main_mod

    valid_token = f"sa_found_{uuid.uuid4().hex}"
    uid, key_id, email = _seed_key(valid_token)

    # conftest sets SKIP_MCP_LIFESPAN=1 for plain REST tests; this test needs the
    # real MCP manager running, so force it on for this single lifespan entry.
    # Restore it in finally so test modules running AFTER this one don't re-enter
    # the (single-use) MCP manager and hit "run() can only be called once".
    prev_skip = main_mod.SKIP_MCP_LIFESPAN
    main_mod.SKIP_MCP_LIFESPAN = False
    try:
        # Enter the app lifespan ONCE (starts the MCP session manager task group —
        # Pitfall 4). All assertions run inside this single entry.
        async with lifespan(app):
            # (c) valid sa_ bearer → initialize + tools/list + whoami
            async with _http_client(valid_token) as hc:
                async with streamable_http_client(url="http://mcptest/mcp/", http_client=hc) as (r, w, _):
                    async with ClientSession(r, w) as session:
                        await session.initialize()
                        tools = await session.list_tools()
                        tool_names = [t.name for t in tools.tools]
                        assert "whoami" in tool_names and "ping" in tool_names  # (a) + tools/list

                        before = _read_request_count(key_id)
                        result = await session.call_tool("whoami", {})
                        text = "".join(
                            b.text for b in result.content if getattr(b, "type", None) == "text"
                        )
                        assert email in text  # (c) whoami returns the seeded owner

                        after = _read_request_count(key_id)
                        assert after == before + 1  # (d) request_count incremented via /mcp

            # (b) missing bearer is rejected — the session/tool call must fail
            with pytest.raises(Exception):
                async with _http_client(None) as hc:
                    async with streamable_http_client(url="http://mcptest/mcp/", http_client=hc) as (r, w, _):
                        async with ClientSession(r, w) as session:
                            await session.initialize()
                            await session.call_tool("whoami", {})
    finally:
        main_mod.SKIP_MCP_LIFESPAN = prev_skip
