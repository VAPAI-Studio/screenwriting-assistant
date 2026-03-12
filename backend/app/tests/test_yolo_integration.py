"""
Phase 8 — YOLO Integration token budget controls.

Tests for MAX_AGENTS_PER_PIPELINE_STEP and AGENT_RELEVANCE_THRESHOLD
configuration values and their SQL-level gating in _lookup_mapped_agents.
"""

import uuid

import pytest
from unittest.mock import patch

from app.config import settings
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


def _make_pipeline_map(
    db_session, owner_id, agent_id,
    phase="idea", subsection_key="idea_wizard",
    confidence=0.9,
):
    """Helper to create an AgentPipelineMap row with configurable confidence."""
    mapping = AgentPipelineMap(
        id=str(uuid.uuid4()),
        owner_id=owner_id,
        agent_id=str(agent_id),
        phase=phase,
        subsection_key=subsection_key,
        confidence=confidence,
        rationale="Test mapping",
        pipeline_dirty=False,
    )
    db_session.add(mapping)
    db_session.flush()
    return mapping


def test_config_values_exist():
    """settings.MAX_AGENTS_PER_PIPELINE_STEP exists as int (default 3),
    settings.AGENT_RELEVANCE_THRESHOLD exists as float (default 0.3)."""
    assert hasattr(settings, "MAX_AGENTS_PER_PIPELINE_STEP")
    assert isinstance(settings.MAX_AGENTS_PER_PIPELINE_STEP, int)
    assert settings.MAX_AGENTS_PER_PIPELINE_STEP == 3

    assert hasattr(settings, "AGENT_RELEVANCE_THRESHOLD")
    assert isinstance(settings.AGENT_RELEVANCE_THRESHOLD, float)
    assert settings.AGENT_RELEVANCE_THRESHOLD == 0.3


def test_max_agents_per_step_limits_lookup(db_session, owner_id, make_agent):
    """Create 5 agents mapped to same step with confidence 0.5-0.9.
    With MAX_AGENTS_PER_PIPELINE_STEP=2, _lookup_mapped_agents returns
    exactly 2 agents (the 2 highest confidence)."""
    confidences = [0.5, 0.6, 0.7, 0.8, 0.9]
    agents = []
    for i, conf in enumerate(confidences):
        agent = make_agent(name=f"Agent {i}")
        _make_pipeline_map(
            db_session, owner_id, agent.id,
            phase="idea", subsection_key="idea_wizard",
            confidence=conf,
        )
        agents.append(agent)
    db_session.flush()

    with patch.object(settings, "MAX_AGENTS_PER_PIPELINE_STEP", 2), \
         patch.object(settings, "AGENT_RELEVANCE_THRESHOLD", 0.0):
        result = agent_review_middleware._lookup_mapped_agents(
            owner_id, "idea", "idea_wizard", db_session
        )

    assert len(result) == 2
    # Should be the 2 highest confidence agents (0.9 and 0.8)
    names = {r["name"] for r in result}
    assert "Agent 4" in names  # confidence 0.9
    assert "Agent 3" in names  # confidence 0.8


def test_relevance_threshold_filters_agents(db_session, owner_id, make_agent):
    """Create 3 agents: confidence 0.8, 0.5, 0.1.
    With AGENT_RELEVANCE_THRESHOLD=0.3, _lookup_mapped_agents returns
    2 agents (0.8 and 0.5), excluding the 0.1 agent."""
    conf_map = [(0.8, "High Agent"), (0.5, "Mid Agent"), (0.1, "Low Agent")]
    for conf, name in conf_map:
        agent = make_agent(name=name)
        _make_pipeline_map(
            db_session, owner_id, agent.id,
            phase="idea", subsection_key="idea_wizard",
            confidence=conf,
        )
    db_session.flush()

    with patch.object(settings, "AGENT_RELEVANCE_THRESHOLD", 0.3), \
         patch.object(settings, "MAX_AGENTS_PER_PIPELINE_STEP", 10):
        result = agent_review_middleware._lookup_mapped_agents(
            owner_id, "idea", "idea_wizard", db_session
        )

    assert len(result) == 2
    names = {r["name"] for r in result}
    assert "High Agent" in names
    assert "Mid Agent" in names
    assert "Low Agent" not in names


def test_gating_combined(db_session, owner_id, make_agent):
    """Create 5 agents with confidence 0.9, 0.7, 0.5, 0.2, 0.1.
    With threshold=0.3 and max=2, returns exactly 2 agents (0.9 and 0.7)."""
    conf_map = [
        (0.9, "Agent A"),
        (0.7, "Agent B"),
        (0.5, "Agent C"),
        (0.2, "Agent D"),
        (0.1, "Agent E"),
    ]
    for conf, name in conf_map:
        agent = make_agent(name=name)
        _make_pipeline_map(
            db_session, owner_id, agent.id,
            phase="idea", subsection_key="idea_wizard",
            confidence=conf,
        )
    db_session.flush()

    with patch.object(settings, "AGENT_RELEVANCE_THRESHOLD", 0.3), \
         patch.object(settings, "MAX_AGENTS_PER_PIPELINE_STEP", 2):
        result = agent_review_middleware._lookup_mapped_agents(
            owner_id, "idea", "idea_wizard", db_session
        )

    assert len(result) == 2
    names = {r["name"] for r in result}
    assert "Agent A" in names  # confidence 0.9
    assert "Agent B" in names  # confidence 0.7
    assert "Agent C" not in names  # confidence 0.5 but max=2 reached
    assert "Agent D" not in names  # below threshold
    assert "Agent E" not in names  # below threshold
