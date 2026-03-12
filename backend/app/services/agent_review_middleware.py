# backend/app/services/agent_review_middleware.py

"""
Agent Review Middleware — intercepts wizard generation output and routes
it through mapped agents for parallel review.

REVW-02: Parallel fan-out via asyncio.gather with session-per-task
REVW-04: Zero-agent pass-through bypass
REVW-01 (partial): Entry point and metadata — injection into wizards.py
         deferred to Phase 6

Merge is currently a STUB (returns first review's feedback).
Plan 05-02 replaces with real AI merge call.
"""

import asyncio
import collections
import json
import logging
from typing import Any, Callable, Dict, List, Optional

from sqlalchemy.orm import Session

from ..config import settings
from ..models.database import Agent, AgentPipelineMap
from .ai_provider import chat_completion

logger = logging.getLogger(__name__)

SessionFactory = Callable[[], Session]


class AgentReviewMiddleware:

    async def review_step_output(
        self,
        phase: str,
        subsection_key: str,
        raw_output: Any,
        owner_id: str,
        session_factory: SessionFactory,
        wizard_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Main entry point: look up mapped agents, fan out reviews, merge results."""
        # Lookup agents using a dedicated session
        db = session_factory()
        try:
            agents_data = self._lookup_mapped_agents(owner_id, phase, subsection_key, db)
        finally:
            db.close()

        # REVW-04: Zero-agent pass-through
        if not agents_data:
            return {
                "output": raw_output,
                "agents_consulted": [],
                "review_applied": False,
            }

        # REVW-02: Parallel fan-out
        reviews = await self._fan_out_reviews(
            agents_data, raw_output, phase, subsection_key, session_factory
        )

        # Filter successful reviews
        successful = [r for r in reviews if r is not None]

        if not successful:
            return {
                "output": raw_output,
                "agents_consulted": [],
                "review_applied": False,
            }

        # STUB merge — Plan 05-02 replaces with real AI merge call
        logger.warning("Using stub merge -- Plan 05-02 replaces with AI merge call")
        refined_output = successful[0]["feedback"]

        # Build agents_consulted metadata
        agents_consulted = [
            {
                "agent_id": r["agent_id"],
                "name": r["agent_name"],
            }
            for r in successful
        ]

        return {
            "output": refined_output,
            "agents_consulted": agents_consulted,
            "review_applied": True,
        }

    def _lookup_mapped_agents(
        self,
        owner_id: str,
        phase: str,
        subsection_key: str,
        db: Session,
    ) -> List[Dict[str, Any]]:
        """Query AgentPipelineMap for active agents mapped to this step."""
        mappings = (
            db.query(AgentPipelineMap)
            .filter(
                AgentPipelineMap.owner_id == str(owner_id),
                AgentPipelineMap.phase == phase,
                AgentPipelineMap.subsection_key == subsection_key,
            )
            .order_by(AgentPipelineMap.confidence.desc())
            .all()
        )

        if not mappings:
            return []

        agent_ids = [str(m.agent_id) for m in mappings]
        agents = (
            db.query(Agent)
            .filter(
                Agent.id.in_(agent_ids),
                Agent.is_active == True,
            )
            .all()
        )

        # Capture ORM attributes into plain dicts before async work
        # to avoid DetachedInstanceError (Phase 2/4 pattern)
        agents_data = []
        for agent in agents:
            agent_type_val = agent.agent_type
            if hasattr(agent_type_val, "value"):
                agent_type_val = agent_type_val.value
            agents_data.append({
                "id": str(agent.id),
                "name": agent.name,
                "system_prompt_template": agent.system_prompt_template,
                "personality": agent.personality,
                "agent_type": str(agent_type_val) if agent_type_val else "book_based",
            })

        return agents_data

    async def _fan_out_reviews(
        self,
        agents_data: List[Dict[str, Any]],
        raw_output: Any,
        phase: str,
        subsection_key: str,
        session_factory: SessionFactory,
    ) -> List[Optional[Dict[str, Any]]]:
        """Fan out reviews to N agents concurrently, each with its own session."""
        tasks = []
        for agent_data in agents_data:
            task = asyncio.wait_for(
                self._review_agent_with_session(
                    agent_data, raw_output, phase, subsection_key, session_factory
                ),
                timeout=settings.AGENT_REVIEW_TIMEOUT,
            )
            tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Filter out exceptions
        filtered = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.warning(
                    "Agent review failed for %s: %s",
                    agents_data[i]["name"],
                    str(result),
                )
                filtered.append(None)
            else:
                filtered.append(result)

        return filtered

    async def _review_agent_with_session(
        self,
        agent_data: Dict[str, Any],
        raw_output: Any,
        phase: str,
        subsection_key: str,
        session_factory: SessionFactory,
    ) -> Dict[str, Any]:
        """Session-per-task wrapper for individual agent review."""
        db = session_factory()
        try:
            feedback = await self._single_agent_review(
                agent_name=agent_data["name"],
                agent_prompt=agent_data["system_prompt_template"],
                agent_personality=agent_data.get("personality"),
                agent_type=agent_data.get("agent_type", "book_based"),
                raw_output=raw_output,
                phase=phase,
                subsection_key=subsection_key,
            )
            return {
                "agent_id": agent_data["id"],
                "agent_name": agent_data["name"],
                "feedback": feedback,
            }
        finally:
            db.close()

    async def _single_agent_review(
        self,
        agent_name: str,
        agent_prompt: str,
        agent_personality: Optional[str],
        agent_type: str,
        raw_output: Any,
        phase: str,
        subsection_key: str,
    ) -> Dict[str, Any]:
        """Call chat_completion with agent-specific system prompt and raw_output."""
        system_prompt = self._build_pipeline_system_prompt(
            agent_name=agent_name,
            agent_template=agent_prompt,
            agent_personality=agent_personality,
            agent_type=agent_type,
            phase=phase,
            subsection_key=subsection_key,
        )

        raw_json = json.dumps(raw_output) if not isinstance(raw_output, str) else raw_output

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Review this AI-generated output and provide structured feedback:\n\n{raw_json}"},
        ]

        response = await chat_completion(
            messages=messages,
            temperature=0.7,
            max_tokens=settings.MAX_TOKENS,
            json_mode=True,
        )

        try:
            return json.loads(response)
        except (json.JSONDecodeError, TypeError):
            return {"issues": [], "suggestions": [response], "refined_fields": {}}

    def _build_pipeline_system_prompt(
        self,
        agent_name: str,
        agent_template: str,
        agent_personality: Optional[str],
        agent_type: str,
        phase: str,
        subsection_key: str,
    ) -> str:
        """Build system prompt for pipeline review context."""
        # Safe format_map with defaultdict for missing template variables
        safe_vars = collections.defaultdict(str, {
            "phase": phase,
            "subsection_key": subsection_key,
            "agent_type": agent_type,
        })

        try:
            personalized_template = agent_template.format_map(safe_vars)
        except (KeyError, ValueError):
            personalized_template = agent_template

        parts = [personalized_template]

        if agent_personality:
            parts.append(f"\nPersonality: {agent_personality}")

        parts.append(
            f"\n\nYou are reviewing AI-generated output for the {phase}/{subsection_key} step. "
            "Provide structured feedback as JSON with keys: issues, suggestions, refined_fields."
        )

        return "\n".join(parts)


# Module singleton
agent_review_middleware = AgentReviewMiddleware()
