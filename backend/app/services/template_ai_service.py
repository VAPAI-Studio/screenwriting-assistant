# backend/app/services/template_ai_service.py

import json
import logging
from typing import Dict, List, Optional

from ..config import settings
from ..templates import get_template
from .ai_provider import chat_completion, chat_completion_stream

logger = logging.getLogger(__name__)


class TemplateAIService:

    def _build_project_context(self, project_data: Dict, template_id: str) -> str:
        """Build comprehensive project context string from all phase data."""
        template = get_template(template_id)
        context_parts = [f"Template: {template['name']}"]

        for phase_key, subsections in project_data.items():
            if isinstance(subsections, dict):
                for sub_key, content in subsections.items():
                    if content and isinstance(content, dict):
                        filled = {k: v for k, v in content.items() if v}
                        if filled:
                            context_parts.append(f"\n## {phase_key} > {sub_key}")
                            for field_key, value in filled.items():
                                context_parts.append(f"- {field_key}: {value}")

        return "\n".join(context_parts)

    async def wizard_generate(
        self,
        wizard_type: str,
        config: Dict,
        project_context: str,
        template_id: str
    ) -> Dict:
        """Run a wizard generation (beats, episodes, scenes, scripts)."""
        template = get_template(template_id)

        if wizard_type == "idea_wizard":
            return await self._generate_idea(config, project_context, template)
        elif wizard_type == "episode_wizard":
            return await self._generate_episodes(config, project_context, template)
        elif wizard_type == "scene_wizard":
            return await self._generate_scenes(config, project_context, template)
        elif wizard_type == "beat_wizard":
            return await self._generate_beats(config, project_context, template)
        elif wizard_type == "script_writer_wizard":
            return await self._generate_scripts(config, project_context, template)
        else:
            raise ValueError(f"Unknown wizard type: {wizard_type}")

    async def _generate_idea(self, config: Dict, project_context: str, template: Dict) -> Dict:
        """Take partial idea fields and generate a fully fleshed-out idea."""
        genre = config.get("genre", "")
        initial_idea = config.get("initial_idea", "")
        tone = config.get("tone", "")
        target_audience = config.get("target_audience", "")
        runtime_target = config.get("runtime_target", "")
        guidance = config.get("custom_guidance", "")

        current_values = {
            k: v for k, v in {
                "genre": genre, "initial_idea": initial_idea, "tone": tone,
                "target_audience": target_audience, "runtime_target": runtime_target,
            }.items() if v
        }

        prompt = f"""You are an expert screenwriting development partner.

## Project Context
{project_context}

## Current Idea Fields
{json.dumps(current_values, indent=2) if current_values else "No fields filled in yet."}

{f'Custom guidance: {guidance}' if guidance else ''}

## Task
Based on whatever the user has provided (even if it's very little), generate a fully developed story idea. Fill in or expand ALL of the following fields:

- genre: The genre(s) of the story
- initial_idea: A compelling 2-3 paragraph story concept that captures the core premise, central conflict, and what makes it unique
- tone: The overall tone and mood
- target_audience: Who this story is for and why it will appeal to them

If the user already provided values, enhance and expand them rather than replacing. If fields are empty, create compelling content that fits with whatever else has been provided.

Return a JSON object with exactly these keys: "genre", "initial_idea", "tone", "target_audience"."""

        try:
            text = await chat_completion(
                messages=[
                    {"role": "system", "content": "You are an expert screenwriting development partner. Return valid JSON only."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.8,
                max_tokens=2000,
                json_mode=True,
            )
            result = json.loads(text)
            return {"fields": result}
        except Exception as e:
            logger.error(f"Idea generation error: {e}")
            return {"fields": {}, "error": str(e)}

    async def _generate_episodes(self, config: Dict, project_context: str, template: Dict) -> Dict:
        count = config.get("count", 50)
        approach = config.get("approach", "classic")
        guidance = config.get("custom_guidance", "")

        prompt = f"""You are an expert micro-drama screenwriting assistant.

## Project Context
{project_context}

## Task
Generate {count} episode outlines for this micro-drama series.

Approach: {approach}
{f'Custom guidance: {guidance}' if guidance else ''}

Each episode MUST have these 11 fields:
- summary: One-line episode description
- arena: The setting/location for this episode
- inciting_incident: What triggers the episode's conflict
- goal: What the protagonist wants in this episode
- subtext: The emotional undercurrent
- opposition: What stands in the way
- plan: The protagonist's strategy
- progressive_complication: How things get worse
- turning_point: The key moment of change
- crisis: The worst moment / impossible choice
- climax: How the episode resolves (with a CLIFFHANGER)

Return a JSON object with key "episodes" containing an array of episode objects.
Every episode must end on a cliffhanger that demands the next episode."""

        try:
            text = await chat_completion(
                messages=[
                    {"role": "system", "content": "You are an expert micro-drama screenwriter. Return valid JSON only."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.8,
                max_tokens=4000,
                json_mode=True,
            )
            result = json.loads(text)
            return {"episodes": result.get("episodes", [])}
        except Exception as e:
            logger.error(f"Episode generation error: {e}")
            return {"episodes": [], "error": str(e)}

    async def _generate_scenes(self, config: Dict, project_context: str, template: Dict) -> Dict:
        approach = config.get("approach", "minimal")
        guidance = config.get("custom_guidance", "")

        prompt = f"""You are an expert short film screenwriting assistant.

## Project Context
{project_context}

## Task
Generate scenes for this short film.

Approach: {approach}
{f'Custom guidance: {guidance}' if guidance else ''}

Each scene MUST have these 10 fields:
- summary: One-line scene description
- arena: The location/setting
- inciting_incident: What triggers the scene's conflict
- goal: What the character wants
- subtext: The emotional undercurrent
- turning_point: The key moment of change
- crisis: The worst moment
- climax: How the scene peaks
- fallout: Immediate consequences
- push_forward: How this connects to the next scene

Return a JSON object with key "scenes" containing an array of scene objects."""

        try:
            text = await chat_completion(
                messages=[
                    {"role": "system", "content": "You are an expert short film screenwriter. Return valid JSON only."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.8,
                max_tokens=4000,
                json_mode=True,
            )
            result = json.loads(text)
            return {"scenes": result.get("scenes", [])}
        except Exception as e:
            logger.error(f"Scene generation error: {e}")
            return {"scenes": [], "error": str(e)}

    async def _generate_beats(self, config: Dict, project_context: str, template: Dict) -> Dict:
        story_input = config.get("story_input", "")

        prompt = f"""You are an expert screenwriting assistant.

## Project Context
{project_context}

## Story Idea
{story_input}

## Task
Analyze this story idea and generate complete story beats. Fill in any gaps to form a complete story outline.

Return a JSON object with key "beats" containing the story beats as key-value pairs matching the template's story arc structure."""

        try:
            text = await chat_completion(
                messages=[
                    {"role": "system", "content": "You are an expert screenwriter. Return valid JSON only."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.8,
                max_tokens=4000,
                json_mode=True,
            )
            result = json.loads(text)
            return result
        except Exception as e:
            logger.error(f"Beat generation error: {e}")
            return {"beats": {}, "error": str(e)}

    async def _generate_scripts(self, config: Dict, project_context: str, template: Dict) -> Dict:
        episodes = config.get("episodes", [])
        duration = config.get("target_duration", 120)
        guidance = config.get("custom_guidance", "")

        prompt = f"""You are an expert screenwriter.

## Project Context
{project_context}

## Task
Write screenplay content for the following episodes/scenes.
Target duration per episode: {duration} seconds.
{f'Custom guidance: {guidance}' if guidance else ''}

## Episodes to write:
{json.dumps(episodes, indent=2)}

For each episode, write a proper screenplay with:
- Scene headings (INT./EXT. LOCATION - TIME)
- Action lines
- Character dialogue
- Parentheticals where needed

Return a JSON object with key "screenplays" containing an array of objects, each with "episode_index" and "content" (the screenplay text)."""

        try:
            text = await chat_completion(
                messages=[
                    {"role": "system", "content": "You are an expert screenwriter. Return valid JSON only."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=4000,
                json_mode=True,
            )
            result = json.loads(text)
            return result
        except Exception as e:
            logger.error(f"Script generation error: {e}")
            return {"screenplays": [], "error": str(e)}

    async def fill_blanks(
        self,
        current_content: Dict,
        subsection_config: Dict,
        project_context: str
    ) -> Dict:
        """Fill empty fields in a subsection or item based on project context."""
        all_fields = []
        if "fields" in subsection_config:
            all_fields = subsection_config["fields"]
        elif "field_groups" in subsection_config:
            for group in subsection_config["field_groups"]:
                all_fields.extend(group.get("fields", []))
        elif "cards" in subsection_config:
            all_fields = subsection_config["cards"]

        empty_fields = [f for f in all_fields if not current_content.get(f.get("key", ""))]
        if not empty_fields:
            return {"content": current_content, "message": "All fields are already filled."}

        field_descriptions = "\n".join(
            f"- {f['label']}: {f.get('placeholder', f['label'])}" for f in empty_fields
        )

        prompt = f"""You are an expert screenwriting assistant.

## Project Context
{project_context}

## Existing Content
{json.dumps({k: v for k, v in current_content.items() if v}, indent=2)}

## Task
Fill in the following empty fields based on the project context and existing content:
{field_descriptions}

Return a JSON object with the field keys as keys and the generated content as string values."""

        try:
            text = await chat_completion(
                messages=[
                    {"role": "system", "content": "You are an expert screenwriter. Return valid JSON only."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=2000,
                json_mode=True,
            )
            result = json.loads(text)
            return {"content": result}
        except Exception as e:
            logger.error(f"Fill blanks error: {e}")
            return {"content": {}, "error": str(e)}

    async def give_notes(
        self,
        current_content: Dict,
        subsection_config: Dict,
        project_context: str
    ) -> Dict:
        """Provide AI feedback on filled content."""
        prompt = f"""You are an expert screenwriting coach.

## Project Context
{project_context}

## Content to Review
{json.dumps(current_content, indent=2)}

## Task
Review this content and provide specific, actionable notes. Focus on:
- Story structure and coherence
- Character depth and consistency
- Dramatic tension and stakes
- Pacing and engagement
- Any missing elements or weak points

Return a JSON object with key "notes" containing an array of note strings."""

        try:
            text = await chat_completion(
                messages=[
                    {"role": "system", "content": "You are an expert screenwriting coach. Return valid JSON only."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=2000,
                json_mode=True,
            )
            result = json.loads(text)
            return {"notes": result.get("notes", [])}
        except Exception as e:
            logger.error(f"Give notes error: {e}")
            return {"notes": [], "error": str(e)}

    async def chat_respond(
        self,
        user_message: str,
        chat_history: List[Dict],
        system_prompt: str,
        project_context: str
    ) -> str:
        """Generate a contextual chat response."""
        messages = [
            {"role": "system", "content": f"{system_prompt}\n\n## Project Context\n{project_context}"}
        ]
        for msg in chat_history[-20:]:
            messages.append({"role": msg["role"], "content": msg["content"]})
        messages.append({"role": "user", "content": user_message})

        try:
            return await chat_completion(
                messages=messages,
                temperature=0.8,
                max_tokens=2000,
            )
        except Exception as e:
            logger.error(f"Chat error: {e}")
            return "I'm having trouble generating a response right now. Please try again."

    async def chat_respond_stream(
        self,
        user_message: str,
        chat_history: List[Dict],
        system_prompt: str,
        project_context: str
    ):
        """Generate a streaming contextual chat response. Yields text chunks."""
        messages = [
            {"role": "system", "content": f"{system_prompt}\n\n## Project Context\n{project_context}"}
        ]
        for msg in chat_history[-20:]:
            messages.append({"role": msg["role"], "content": msg["content"]})
        messages.append({"role": "user", "content": user_message})

        async for chunk in chat_completion_stream(
            messages=messages,
            temperature=0.8,
            max_tokens=2000,
        ):
            yield chunk

    async def chat_action_stream_message(
        self,
        user_message: str,
        chat_history: List[Dict],
        system_prompt: str,
        project_context: str,
        field_definitions: List[Dict],
        current_content: Dict,
    ):
        """Phase 1: Stream conversational response for action mode. Yields text chunks."""
        fields_desc = "\n".join(
            f"- {f.get('key')}: {f.get('label', f.get('key'))} ({f.get('type', 'text')})"
            for f in field_definitions
        )
        current_desc = json.dumps(
            {k: v for k, v in current_content.items() if v}, indent=2
        ) if current_content else "{}"

        action_stream_prompt = f"""{system_prompt}

## Project Context
{project_context}

## Current Section Fields
Available fields you can modify:
{fields_desc}

## Current Values
{current_desc}

## Instructions
You are in ACTION mode. The user wants you to modify their story fields.
Explain conversationally what changes you will make and why. Be specific about
which fields you will update and what the new values will be.
Do NOT output JSON — respond naturally as a writing partner."""

        messages = [{"role": "system", "content": action_stream_prompt}]
        for msg in chat_history[-20:]:
            messages.append({"role": msg["role"], "content": msg["content"]})
        messages.append({"role": "user", "content": user_message})

        async for chunk in chat_completion_stream(
            messages=messages,
            temperature=0.7,
            max_tokens=2000,
        ):
            yield chunk

    async def chat_action_extract_updates(
        self,
        user_message: str,
        assistant_message: str,
        field_definitions: List[Dict],
        current_content: Dict,
    ) -> Dict:
        """Phase 2: Extract field_updates from the streamed message via JSON-mode call."""
        fields_desc = "\n".join(
            f"- {f.get('key')}: {f.get('label', f.get('key'))} ({f.get('type', 'text')})"
            for f in field_definitions
        )
        current_desc = json.dumps(
            {k: v for k, v in current_content.items() if v}, indent=2
        ) if current_content else "{}"

        extraction_prompt = f"""Extract field updates from this conversation.

## Available fields:
{fields_desc}

## Current values:
{current_desc}

## User asked:
{user_message}

## Assistant responded:
{assistant_message}

## Task:
Based on what the assistant described, return a JSON object with exactly one key:
- "field_updates": an object mapping field keys to their new string values.
Use an empty object {{}} if no changes were described.
Only include fields that the assistant explicitly mentioned changing."""

        try:
            text = await chat_completion(
                messages=[
                    {"role": "system", "content": "Extract field updates as JSON. Return valid JSON only."},
                    {"role": "user", "content": extraction_prompt}
                ],
                temperature=0.3,
                max_tokens=2000,
                json_mode=True,
            )
            result = json.loads(text)
            return result.get("field_updates", {})
        except Exception as e:
            logger.error(f"Action extract updates error: {e}")
            return {}

    async def chat_with_action(
        self,
        user_message: str,
        chat_history: List[Dict],
        system_prompt: str,
        project_context: str,
        field_definitions: List[Dict],
        current_content: Dict,
    ) -> Dict:
        """Chat that can also modify fields. Returns message + field_updates."""
        fields_desc = "\n".join(
            f"- {f.get('key')}: {f.get('label', f.get('key'))} ({f.get('type', 'text')})"
            for f in field_definitions
        )
        current_desc = json.dumps(
            {k: v for k, v in current_content.items() if v}, indent=2
        ) if current_content else "{}"

        action_prompt = f"""{system_prompt}

## Project Context
{project_context}

## Current Section Fields
Available fields you can modify:
{fields_desc}

## Current Values
{current_desc}

## Instructions
You are in ACTION mode. Respond conversationally to the user AND update fields when appropriate.
You MUST return valid JSON with exactly two keys:
- "message": your conversational response (string)
- "field_updates": an object with field keys and new values to apply. Use an empty object {{}} if no changes are needed.

Only update fields the user asks about or that naturally follow from the conversation. Never overwrite fields the user didn't mention unless they ask you to fill everything."""

        messages = [{"role": "system", "content": action_prompt}]
        for msg in chat_history[-20:]:
            messages.append({"role": msg["role"], "content": msg["content"]})
        messages.append({"role": "user", "content": user_message})

        text = ""
        try:
            text = await chat_completion(
                messages=messages,
                temperature=0.7,
                max_tokens=3000,
                json_mode=True,
            )
            logger.info(f"Action mode raw response (first 500 chars): {text[:500]}")
            result = json.loads(text)
            return {
                "message": result.get("message", ""),
                "field_updates": result.get("field_updates", {}),
            }
        except json.JSONDecodeError as e:
            logger.error(f"Chat with action JSON parse error: {e}\nRaw text: {text[:1000]}")
            # Try to salvage the response as plain text
            return {
                "message": f"[JSON parse error — raw AI response]: {text[:500]}",
                "field_updates": {},
            }
        except Exception as e:
            logger.error(f"Chat with action error: {type(e).__name__}: {e}", exc_info=True)
            return {
                "message": f"[Error: {type(e).__name__}]: {str(e)}",
                "field_updates": {},
            }

    async def analyze_structure(
        self,
        items: List[Dict],
        template_id: str,
        project_context: str
    ) -> Dict:
        """Analyze episode/scene list structure."""
        prompt = f"""You are an expert screenwriting structure analyst.

## Project Context
{project_context}

## Items to Analyze
{json.dumps(items, indent=2)}

## Task
Analyze the structural integrity of this episode/scene list. Look for:
- Pacing issues (too fast, too slow, uneven)
- Missing story beats
- Narrative arc completeness
- Cliffhanger effectiveness (for series)
- Character development progression
- Tonal consistency

Return a JSON object with:
- "overall_score": 1-10 rating
- "strengths": array of strength observations
- "issues": array of structural issues found
- "suggestions": array of specific improvement suggestions"""

        try:
            text = await chat_completion(
                messages=[
                    {"role": "system", "content": "You are an expert screenwriting structure analyst. Return valid JSON only."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=3000,
                json_mode=True,
            )
            return json.loads(text)
        except Exception as e:
            logger.error(f"Analyze structure error: {e}")
            return {"overall_score": 0, "strengths": [], "issues": [], "suggestions": [], "error": str(e)}


# Singleton
template_ai_service = TemplateAIService()
