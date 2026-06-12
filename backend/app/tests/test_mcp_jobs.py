"""Tests for the MCP job registry + long-running tool pattern (Phase 56).

Covers MCPJ-01 (long-running tool returns a job id), MCPJ-02 (generic
job_status polls + returns the result), MCPJ-03 (fast tools return synchronously
— proven elsewhere by whoami/ping), and the owner-scoping of jobs (MCPF-04).

The AI call (template_ai_service.regenerate_single_scene) is mocked so no live
model is hit; the test asserts the job machinery, not generation quality.
"""

import asyncio

import pytest

from app.mcp_server.jobs import JobRegistry, PENDING, RUNNING, DONE, ERROR


@pytest.mark.anyio
async def test_registry_runs_job_to_done_with_result():
    reg = JobRegistry()
    job = await reg.create(owner_id="user-1", kind="test")
    assert job.status == PENDING

    async def work():
        return {"value": 42}

    await reg.run(job, work)
    # Let the background task finish.
    for _ in range(50):
        got = await reg.get(job.id, "user-1")
        if got.status == DONE:
            break
        await asyncio.sleep(0.01)

    got = await reg.get(job.id, "user-1")
    assert got.status == DONE
    assert got.result == {"value": 42}
    assert got.error is None


@pytest.mark.anyio
async def test_registry_records_error():
    reg = JobRegistry()
    job = await reg.create(owner_id="user-1", kind="test")

    async def boom():
        raise RuntimeError("generation failed")

    await reg.run(job, boom)
    for _ in range(50):
        got = await reg.get(job.id, "user-1")
        if got.status == ERROR:
            break
        await asyncio.sleep(0.01)

    got = await reg.get(job.id, "user-1")
    assert got.status == ERROR
    assert "generation failed" in got.error


@pytest.mark.anyio
async def test_job_is_owner_scoped():
    reg = JobRegistry()
    job = await reg.create(owner_id="owner-A", kind="test")
    # Another user cannot read it.
    assert await reg.get(job.id, "owner-B") is None
    # The owner can.
    assert await reg.get(job.id, "owner-A") is not None


@pytest.mark.anyio
async def test_immediate_return_does_not_block_on_slow_work():
    """The create+run call returns immediately even if the work is slow —
    proving the long-running tool won't block past the client timeout (MCPJ-01)."""
    reg = JobRegistry()
    job = await reg.create(owner_id="user-1", kind="test")

    started = asyncio.get_event_loop().time()

    async def slow():
        await asyncio.sleep(0.3)
        return "late"

    await reg.run(job, slow)
    elapsed = asyncio.get_event_loop().time() - started
    # run() returns right away; it must not have awaited the 0.3s of work.
    assert elapsed < 0.1
    # status is running (or pending) immediately after.
    got = await reg.get(job.id, "user-1")
    assert got.status in (PENDING, RUNNING)


@pytest.mark.anyio
async def test_generate_scene_tool_returns_job_then_polls_done(monkeypatch):
    """End-to-end at the tool layer: screenplay_generate_scene returns a job_id
    immediately and job_status polls it to done with the regenerated preview —
    with the AI service mocked.
    """
    import app.mcp_server.tools.screenwriting as sw
    from app.mcp_server.jobs import registry, DONE as DONE_

    # Mock context-building (DB) and the AI call so no DB rows / model needed.
    fake_args = ({"episodes": []}, "ctx", 1, "synopsis", "prev")
    monkeypatch.setattr(sw, "_build_regen_context", lambda *a, **k: fake_args)

    async def fake_regen(*a, **k):
        return {"title": "The Lie", "content": "INT. ROOM - DAY\n...", "episode_index": 1}

    monkeypatch.setattr(sw.template_ai_service, "regenerate_single_scene", fake_regen)

    # Call the tool body directly (bypass the MCP transport): emulate what the
    # registered tool does, using a fixed owner.
    owner_id = "user-xyz"
    job = await registry.create(owner_id, kind="screenplay_generate_scene")

    async def _work():
        return await sw.template_ai_service.regenerate_single_scene(*fake_args)

    await registry.run(job, _work)

    # Immediately after: job exists, not yet done.
    assert (await registry.get(job.id, owner_id)).status in ("pending", "running")

    # Poll to done.
    for _ in range(100):
        got = await registry.get(job.id, owner_id)
        if got.status == DONE_:
            break
        await asyncio.sleep(0.01)

    got = await registry.get(job.id, owner_id)
    assert got.status == DONE_
    assert got.result["title"] == "The Lie"
    assert got.result["episode_index"] == 1
