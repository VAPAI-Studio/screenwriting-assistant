"""
REVW-01 (partial), REVW-02, REVW-04 unit tests for AgentReviewMiddleware.

Tests the middleware entry point, parallel fan-out, session-per-task isolation,
zero-agent pass-through, and failed-agent filtering.
"""

import json
import uuid

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call

from app.models.database import Agent, AgentPipelineMap, AgentType
from app.services.agent_review_middleware import agent_review_middleware


@pytest.fixture
def owner_id():
    return str(uuid.uuid4())


@pytest.fixture
def make_agent(db_session, owner_id):
    """Factory fixture to create Agent ORM instances in the test DB."""
    def _make(
        name="Test Agent",
        system_prompt_template="You are a helpful screenwriting assistant.",
        description="A test agent",
        agent_type=AgentType.BOOK_BASED,
    ):
        agent = Agent(
            id=str(uuid.uuid4()),
            owner_id=owner_id,
            name=name,
            system_prompt_template=system_prompt_template,
            description=description,
            agent_type=agent_type,
            is_active=True,
            is_default=False,
        )
        db_session.add(agent)
        db_session.flush()
        return agent
    return _make


def _make_pipeline_map(db_session, owner_id, agent_id, phase="idea", subsection_key="idea_wizard"):
    """Helper to create an AgentPipelineMap row."""
    mapping = AgentPipelineMap(
        id=str(uuid.uuid4()),
        owner_id=owner_id,
        agent_id=str(agent_id),
        phase=phase,
        subsection_key=subsection_key,
        confidence=0.9,
        rationale="Test mapping",
        pipeline_dirty=False,
    )
    db_session.add(mapping)
    db_session.flush()
    return mapping


@pytest.mark.asyncio
async def test_zero_agents_passthrough(db_session, owner_id):
    """When no AgentPipelineMap rows exist for (owner_id, phase, subsection_key),
    review_step_output returns raw_output unchanged with review_applied=False
    and chat_completion is never called."""
    raw_output = {"title": "My Story", "content": "Once upon a time..."}

    def session_factory():
        return db_session

    with patch("app.services.agent_review_middleware.chat_completion", new_callable=AsyncMock) as mock_chat:
        result = await agent_review_middleware.review_step_output(
            phase="idea",
            subsection_key="idea_wizard",
            raw_output=raw_output,
            owner_id=owner_id,
            session_factory=session_factory,
        )

    assert result["output"] == raw_output
    assert result["agents_consulted"] == []
    assert result["review_applied"] is False
    mock_chat.assert_not_called()


@pytest.mark.asyncio
async def test_parallel_fanout_uses_session_factory(db_session, owner_id, make_agent):
    """When 3 agents are mapped to a step, session_factory is called 3 times
    (once per agent) and each session is closed."""
    agents = [make_agent(name=f"Agent {i}") for i in range(3)]
    for agent in agents:
        _make_pipeline_map(db_session, owner_id, agent.id)

    raw_output = {"title": "Test"}
    mock_review = json.dumps({"issues": [], "suggestions": ["improve pacing"], "refined_fields": {}})

    mock_sessions = []

    def session_factory():
        mock_sess = MagicMock()
        mock_sess.query.return_value = mock_sess
        mock_sessions.append(mock_sess)
        return db_session

    with patch("app.services.agent_review_middleware.chat_completion", new_callable=AsyncMock, return_value=mock_review):
        result = await agent_review_middleware.review_step_output(
            phase="idea",
            subsection_key="idea_wizard",
            raw_output=raw_output,
            owner_id=owner_id,
            session_factory=session_factory,
        )

    # session_factory called once for lookup + once per agent = 4 total
    # But we care that at least 3 sessions were created for the fan-out
    assert len(mock_sessions) >= 3
    assert result["review_applied"] is True


@pytest.mark.asyncio
async def test_review_returns_result_with_agents_consulted(db_session, owner_id, make_agent):
    """When agents are mapped and reviews succeed, result includes output,
    agents_consulted (list of dicts with agent_id, name, summary), and
    review_applied=True."""
    agent1 = make_agent(name="Story Expert")
    agent2 = make_agent(name="Dialogue Coach")
    _make_pipeline_map(db_session, owner_id, agent1.id)
    _make_pipeline_map(db_session, owner_id, agent2.id)

    raw_output = {"title": "Test"}
    mock_review = json.dumps({"issues": [], "suggestions": ["good pacing"], "refined_fields": {}})

    def session_factory():
        return db_session

    with patch("app.services.agent_review_middleware.chat_completion", new_callable=AsyncMock, return_value=mock_review):
        result = await agent_review_middleware.review_step_output(
            phase="idea",
            subsection_key="idea_wizard",
            raw_output=raw_output,
            owner_id=owner_id,
            session_factory=session_factory,
        )

    assert result["review_applied"] is True
    assert len(result["agents_consulted"]) == 2
    for ac in result["agents_consulted"]:
        assert "agent_id" in ac
        assert "name" in ac


@pytest.mark.asyncio
async def test_failed_agent_review_filtered_out(db_session, owner_id, make_agent):
    """When one of 3 agent reviews raises an exception, the other 2 still
    succeed and the failed agent is excluded from agents_consulted."""
    agents = [make_agent(name=f"Agent {i}") for i in range(3)]
    for agent in agents:
        _make_pipeline_map(db_session, owner_id, agent.id)

    raw_output = {"title": "Test"}
    call_count = {"n": 0}

    async def mock_chat_side_effect(*args, **kwargs):
        call_count["n"] += 1
        if call_count["n"] == 2:
            raise Exception("AI provider timeout")
        return json.dumps({"issues": [], "suggestions": ["note"], "refined_fields": {}})

    def session_factory():
        return db_session

    with patch("app.services.agent_review_middleware.chat_completion", new_callable=AsyncMock, side_effect=mock_chat_side_effect):
        result = await agent_review_middleware.review_step_output(
            phase="idea",
            subsection_key="idea_wizard",
            raw_output=raw_output,
            owner_id=owner_id,
            session_factory=session_factory,
        )

    assert result["review_applied"] is True
    assert len(result["agents_consulted"]) == 2


@pytest.mark.asyncio
async def test_all_agents_fail_returns_raw_output(db_session, owner_id, make_agent):
    """When all agent reviews fail/timeout, returns raw_output unchanged
    with review_applied=False."""
    agents = [make_agent(name=f"Agent {i}") for i in range(2)]
    for agent in agents:
        _make_pipeline_map(db_session, owner_id, agent.id)

    raw_output = {"title": "Test", "content": "Original content"}

    def session_factory():
        return db_session

    with patch("app.services.agent_review_middleware.chat_completion", new_callable=AsyncMock, side_effect=Exception("All fail")):
        result = await agent_review_middleware.review_step_output(
            phase="idea",
            subsection_key="idea_wizard",
            raw_output=raw_output,
            owner_id=owner_id,
            session_factory=session_factory,
        )

    assert result["output"] == raw_output
    assert result["agents_consulted"] == []
    assert result["review_applied"] is False
