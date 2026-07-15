# backend/app/tests/test_vapai_ghost_episode.py

"""
Regression: a persisted vapai_episode_id that no longer exists in vapai (the
episode was deleted/recreated on vapai's side) must NOT be trusted — the script
would land on a ghost episode, leaving the real one empty. Both series paths must
verify the id against vapai's live episode list and reconcile by number.

Seen in production: episode stored vapai_episode_id 2aa7b46d… but vapai's real
episode 1 was 75a00a9b…; "Enviar serie" created the script on the ghost id.

The MCP transport helpers (_open_session/_call_tool/_call_tool_list) are mocked
so we assert routing (which episode_id the script is created against), no network.
"""

from unittest.mock import patch, AsyncMock

import pytest

from app.services.vapai_service import VapaiService


REAL_EP = {"id": "75a00a9b-real", "number": 1, "title": "Ep One"}
GHOST_ID = "2aa7b46d-ghost"  # persisted but no longer in vapai


def _mock_session():
    return object()  # opaque; the tool calls are mocked, session is unused


@pytest.mark.asyncio
async def test_send_series_reconciles_ghost_episode_id():
    svc = VapaiService()
    created_scripts = []

    async def fake_call_tool(session, name, args):
        if name == "create_script":
            created_scripts.append(args)
            return {"id": "script-1"}
        if name == "update_project":
            return {"id": args["project_id"]}
        if name == "create_episode":
            return {"id": "newly-created", "number": args["number"]}
        return {"id": "x"}

    async def fake_call_tool_list(session, name, args):
        if name == "list_episodes":
            return [REAL_EP]  # ghost id is NOT here
        return []

    with patch.object(svc, "_require_config"), \
         patch.object(svc, "_open_session", new=AsyncMock(return_value=_mock_session())), \
         patch.object(svc, "_call_tool", new=AsyncMock(side_effect=fake_call_tool)), \
         patch.object(svc, "_call_tool_list", new=AsyncMock(side_effect=fake_call_tool_list)):
        result = await svc.send_series(
            series_title="My Series",
            bible_text="Ana - lead",
            episodes=[{
                "episode_number": 1,
                "title": "Ep One",
                "fountain_text": "INT. ROOM - DAY\nAna enters.",
                "vapai_episode_id": GHOST_ID,  # stale/ghost
            }],
            existing_project_id="series-proj",
        )

    # The script must be created against the REAL episode, never the ghost id.
    assert len(created_scripts) == 1
    assert created_scripts[0]["episode_id"] == REAL_EP["id"]
    assert created_scripts[0]["episode_id"] != GHOST_ID
    assert result["episodes"][0]["vapai_episode_id"] == REAL_EP["id"]


@pytest.mark.asyncio
async def test_send_episode_within_series_reconciles_ghost_episode_id():
    svc = VapaiService()
    created_scripts = []

    async def fake_call_tool(session, name, args):
        if name == "create_script":
            created_scripts.append(args)
            return {"id": "script-1"}
        if name == "update_project":
            return {"id": args["project_id"]}
        if name == "create_episode":
            return {"id": "newly-created", "number": args["number"]}
        return {"id": "x"}

    async def fake_call_tool_list(session, name, args):
        if name == "list_episodes":
            return [REAL_EP]
        return []

    with patch.object(svc, "_require_config"), \
         patch.object(svc, "_open_session", new=AsyncMock(return_value=_mock_session())), \
         patch.object(svc, "_call_tool", new=AsyncMock(side_effect=fake_call_tool)), \
         patch.object(svc, "_call_tool_list", new=AsyncMock(side_effect=fake_call_tool_list)):
        result = await svc.send_episode_within_series(
            series_title="My Series",
            bible_text="Ana - lead",
            episode_number=1,
            episode_title="Ep One",
            fountain_text="INT. ROOM - DAY\nAna enters.",
            existing_project_id="series-proj",
            existing_episode_id=GHOST_ID,  # stale/ghost
        )

    assert len(created_scripts) == 1
    assert created_scripts[0]["episode_id"] == REAL_EP["id"]
    assert result["vapai_episode_id"] == REAL_EP["id"]


@pytest.mark.asyncio
async def test_valid_persisted_episode_id_is_reused():
    """A persisted id that DOES still exist is reused (no needless re-match)."""
    svc = VapaiService()
    created_scripts = []

    async def fake_call_tool(session, name, args):
        if name == "create_script":
            created_scripts.append(args)
            return {"id": "script-1"}
        return {"id": "x"}

    async def fake_call_tool_list(session, name, args):
        return [REAL_EP]

    with patch.object(svc, "_require_config"), \
         patch.object(svc, "_open_session", new=AsyncMock(return_value=_mock_session())), \
         patch.object(svc, "_call_tool", new=AsyncMock(side_effect=fake_call_tool)), \
         patch.object(svc, "_call_tool_list", new=AsyncMock(side_effect=fake_call_tool_list)):
        await svc.send_episode_within_series(
            series_title="My Series",
            bible_text="",
            episode_number=1,
            episode_title="Ep One",
            fountain_text="INT. ROOM - DAY\nAna.",
            existing_project_id="series-proj",
            existing_episode_id=REAL_EP["id"],  # valid
        )

    assert created_scripts[0]["episode_id"] == REAL_EP["id"]
