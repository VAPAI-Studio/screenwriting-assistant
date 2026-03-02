import asyncio
import json
import logging
from typing import List, Dict, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from ..config import settings
from ..models.database import (
    Agent, Section, Project, Framework, SectionType,
    ChatSession, ChatMessage,
)
from .rag_service import rag_service
from .ai_provider import chat_completion

logger = logging.getLogger(__name__)

# Human-readable names for section types and frameworks
SECTION_DESCRIPTIONS = {
    SectionType.INCITING_INCIDENT: "Inciting Incident",
    SectionType.PLOT_POINT_1: "Plot Point 1 (End of Act 1)",
    SectionType.MIDPOINT: "Midpoint",
    SectionType.PLOT_POINT_2: "Plot Point 2 (End of Act 2)",
    SectionType.CLIMAX: "Climax",
    SectionType.RESOLUTION: "Resolution",
}

FRAMEWORK_NAMES = {
    Framework.THREE_ACT: "Three-Act Structure",
    Framework.SAVE_THE_CAT: "Save the Cat (Blake Snyder)",
    Framework.HERO_JOURNEY: "Hero's Journey (Joseph Campbell)",
}


class AgentService:

    # ──────────────────────────────────────────────
    # Prompt building helpers
    # ──────────────────────────────────────────────

    def _format_concept_cards(self, concepts: List[Dict]) -> str:
        """Format concepts into readable cards for the system prompt."""
        if not concepts:
            return "No specific concepts available for this section."

        cards = []
        for c in concepts:
            card = f"### {c['name']}"
            card += f"\n**Definition:** {c['definition']}"
            if c.get("page_range"):
                card += f"\n**Source:** {c.get('chapter_source', 'Unknown')}, pages {c['page_range']}"
            if c.get("examples"):
                examples = "; ".join(
                    f"{ex.get('film', '?')}: {ex.get('description', '')}"
                    for ex in c["examples"][:3]
                )
                card += f"\n**Examples:** {examples}"
            if c.get("actionable_questions"):
                questions = "\n".join(f"  - {q}" for q in c["actionable_questions"][:4])
                card += f"\n**Evaluate against:**\n{questions}"
            cards.append(card)

        return "\n\n".join(cards)

    def _format_relationships(self, relationships: List[Dict]) -> str:
        if not relationships:
            return "No concept relationships available."
        lines = []
        for r in relationships:
            lines.append(f"- {r['source']} → {r['relationship']} → {r['target']}: {r.get('description', '')}")
        return "\n".join(lines)

    def _format_chunks(self, chunks: List[Dict]) -> str:
        if not chunks:
            return "No supporting book excerpts available."
        parts = []
        for i, chunk in enumerate(chunks, 1):
            source = f"[{chunk.get('book_title', 'Unknown')}"
            if chunk.get("chapter_title"):
                source += f", Ch: {chunk['chapter_title']}"
            if chunk.get("page_number"):
                source += f", p.{chunk['page_number']}"
            source += "]"
            parts.append(f"--- Excerpt {i} {source} ---\n{chunk['content'][:800]}")
        return "\n\n".join(parts)

    def _format_project_context(self, project: Project) -> str:
        lines = [f"**Project:** {project.title}"]
        for section in sorted(project.sections, key=lambda s: s.type.value):
            section_name = SECTION_DESCRIPTIONS.get(section.type, section.type.value)
            notes = (section.user_notes or "").strip()
            if notes:
                lines.append(f"\n### {section_name}\n{notes[:500]}")
            else:
                lines.append(f"\n### {section_name}\n(No content yet)")
        return "\n".join(lines)

    def _build_system_prompt(
        self,
        agent: Agent,
        concepts: List[Dict],
        relationships: List[Dict],
        chunks: List[Dict],
        framework: Framework,
        section_type: SectionType,
        project: Project,
    ) -> str:
        """Build a complete system prompt grounded in KG data."""
        prompt = agent.system_prompt_template.format(
            concept_cards=self._format_concept_cards(concepts),
            concept_relationships=self._format_relationships(relationships),
            book_chunks=self._format_chunks(chunks),
            framework=FRAMEWORK_NAMES.get(framework, framework.value),
            section_type=SECTION_DESCRIPTIONS.get(section_type, section_type.value),
            project_context=self._format_project_context(project),
        )

        if agent.personality:
            prompt += f"\n\nYour communication style: {agent.personality}"

        return prompt

    # ──────────────────────────────────────────────
    # Review mode
    # ──────────────────────────────────────────────

    async def review_section(
        self,
        agent: Agent,
        section: Section,
        project: Project,
        db: Session,
    ) -> Dict:
        """Structured review of a section using KG-grounded knowledge."""
        try:
            # Step 1: Get relevant concepts from KG (concept-first retrieval)
            concepts = rag_service.get_relevant_concepts(
                section_type=section.type.value,
                agent_id=agent.id,
                db=db,
            )

            # Step 2: Get concept relationships
            concept_ids = [c["id"] for c in concepts]
            relationships = rag_service.get_concept_relationships(concept_ids, db)

            # Step 3: Get supporting chunks
            chunks = rag_service.get_supporting_chunks(concept_ids, agent.id, db)

            # Step 4: Build system prompt
            system_prompt = self._build_system_prompt(
                agent=agent,
                concepts=concepts,
                relationships=relationships,
                chunks=chunks,
                framework=project.framework,
                section_type=section.type,
                project=project,
            )

            # Step 5: Call AI
            text = await chat_completion(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Analyze this screenplay section:\n\n{section.user_notes or '(empty)'}"},
                ],
                temperature=0.7,
                max_tokens=settings.MAX_TOKENS,
                json_mode=True,
            )

            result = json.loads(text)

            # Build book references from concepts used
            book_refs = []
            for c in concepts[:5]:
                ref = {"concept_name": c["name"]}
                if c.get("chapter_source"):
                    ref["chapter"] = c["chapter_source"]
                if c.get("page_range"):
                    ref["page"] = c["page_range"]
                book_refs.append(ref)

            return {
                "agent_id": str(agent.id),
                "agent_name": agent.name,
                "agent_color": agent.color,
                "agent_icon": agent.icon,
                "issues": result.get("issues", []),
                "suggestions": result.get("suggestions", []),
                "book_references": book_refs,
                "status": "completed",
            }

        except Exception as e:
            logger.error(f"Agent {agent.name} review failed: {e}", exc_info=True)
            return {
                "agent_id": str(agent.id),
                "agent_name": agent.name,
                "agent_color": agent.color,
                "agent_icon": agent.icon,
                "issues": [],
                "suggestions": [],
                "book_references": [],
                "status": "error",
                "error": str(e),
            }

    # ──────────────────────────────────────────────
    # Chat mode
    # ──────────────────────────────────────────────

    async def chat(
        self,
        session: ChatSession,
        user_message: str,
        db: Session,
    ) -> Dict:
        """Conversational follow-up using semantic retrieval from KG."""
        agent = session.agent
        project = session.project

        # Semantic search for relevant concepts + chunks
        search_results = await rag_service.semantic_search(
            query_text=user_message,
            agent_id=agent.id,
            db=db,
        )

        concepts = search_results.get("concepts", [])
        chunks = search_results.get("chunks", [])

        # Build chat system prompt (simpler than review, more conversational)
        concept_context = self._format_concept_cards(concepts)
        chunk_context = self._format_chunks(chunks)
        project_context = self._format_project_context(project)

        system_prompt = f"""You are {agent.name}, a screenwriting consultant.
{agent.description or ''}

Your personality: {agent.personality or 'Helpful and knowledgeable.'}

You have deep knowledge from your reference books. Use the following knowledge to inform your responses:

## Relevant Concepts
{concept_context}

## Supporting Book Excerpts
{chunk_context}

## Writer's Project
{project_context}

## Instructions
- Answer the writer's question using your book knowledge
- Always cite specific concepts and book references when relevant
- Be conversational but substantive
- If the writer asks about their screenplay, reference specific sections from their project
- Include book references in your response naturally (e.g., "As McKee discusses in Chapter X...")
- End your response with a JSON block containing book references used:
  {{"book_references": [{{"concept_name": "...", "chapter": "...", "page": "..."}}]}}"""

        # Load chat history
        history_messages = [
            {"role": msg.role, "content": msg.content}
            for msg in session.messages[-20:]  # Last 20 messages for context
        ]

        messages = [
            {"role": "system", "content": system_prompt},
            *history_messages,
            {"role": "user", "content": user_message},
        ]

        assistant_content = await chat_completion(
            messages=messages,
            temperature=0.7,
            max_tokens=settings.MAX_TOKENS,
        )

        # Try to extract book_references JSON from the response
        book_refs = []
        try:
            # Look for JSON block at the end
            if '{"book_references"' in assistant_content:
                json_start = assistant_content.rfind('{"book_references"')
                json_str = assistant_content[json_start:]
                parsed = json.loads(json_str)
                book_refs = parsed.get("book_references", [])
                # Remove JSON block from displayed content
                assistant_content = assistant_content[:json_start].strip()
        except (json.JSONDecodeError, ValueError):
            pass

        # Store messages
        user_msg = ChatMessage(
            session_id=session.id,
            role="user",
            content=user_message,
            message_type="chat",
        )
        db.add(user_msg)

        assistant_msg = ChatMessage(
            session_id=session.id,
            role="assistant",
            content=assistant_content,
            message_type="chat",
            book_references=book_refs,
            concepts_used=[c["id"] for c in concepts[:5]],
        )
        db.add(assistant_msg)
        db.commit()

        return {
            "content": assistant_content,
            "book_references": book_refs,
            "message_id": str(assistant_msg.id),
        }

    # ──────────────────────────────────────────────
    # Multi-agent parallel review
    # ──────────────────────────────────────────────

    async def run_multi_agent_review(
        self,
        agents: List[Agent],
        section: Section,
        project: Project,
        db: Session,
    ) -> List[Dict]:
        """Run all agents in parallel on a section."""
        tasks = [
            asyncio.wait_for(
                self.review_section(agent, section, project, db),
                timeout=settings.AGENT_REVIEW_TIMEOUT,
            )
            for agent in agents
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        agent_results = []
        for agent, result in zip(agents, results):
            if isinstance(result, Exception):
                logger.error(f"Agent {agent.name} failed: {result}")
                agent_results.append({
                    "agent_id": str(agent.id),
                    "agent_name": agent.name,
                    "agent_color": agent.color,
                    "agent_icon": agent.icon,
                    "issues": [],
                    "suggestions": [],
                    "book_references": [],
                    "status": "error",
                    "error": "Agent timed out or encountered an error",
                })
            else:
                agent_results.append(result)

        return agent_results


agent_service = AgentService()
