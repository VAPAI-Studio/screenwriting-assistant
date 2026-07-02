# backend/app/services/template_ai_service.py

import json
import logging
from typing import Dict, List, Optional

from ..config import settings
from ..templates import get_template
from . import doctrine_service
from .ai_provider import chat_completion, chat_completion_stream

logger = logging.getLogger(__name__)


def _read_episode_text_by_index(db, project_id) -> str:
    """Reconstruct an episode's screenplay text from ScreenplayContent rows,
    joined STRICTLY by formatted_content.episode_index — never positionally.

    Project memory: ScreenplayContent has NO reliable order; positional joins bit
    the project twice (v6.0 WR-01, v7.0 ph50). created_at is only second-resolution
    on SQLite, so it is used ONLY as a newest-first tiebreaker (first match per
    index wins = newest row for that index), mirroring
    breakdown_service._align_screenplay_to_scenes. Rows lacking episode_index or
    with empty content are skipped. Values are joined in ascending episode_index
    order with a blank line between scenes.
    """
    from ..models.database import ScreenplayContent

    rows = (
        db.query(ScreenplayContent)
        .filter(ScreenplayContent.project_id == str(project_id))
        .order_by(ScreenplayContent.created_at.desc(), ScreenplayContent.id.desc())
        .all()
    )
    by_index: Dict[int, str] = {}
    for r in rows:
        idx = (getattr(r, "formatted_content", None) or {}).get("episode_index")
        if idx is None or not r.content:
            continue
        by_index.setdefault(idx, r.content)  # first wins = newest (rows are newest-first)
    return "\n\n".join(by_index[i] for i in sorted(by_index))


class TemplateAIService:

    def _build_project_context(
        self,
        project_data: Dict,
        template_id: str,
        list_items: Optional[Dict[str, list]] = None,
        project_title: Optional[str] = None,
        bible_context: Optional[str] = None,
    ) -> str:
        """Build comprehensive project context string from all phase data and list items."""
        template = get_template(template_id)
        context_parts = []
        if bible_context:
            context_parts.append(bible_context)
            context_parts.append("---")
        if project_title:
            context_parts.append(f"Project: {project_title}")
        context_parts.append(f"Template: {template['name']}")

        for phase_key, subsections in project_data.items():
            if isinstance(subsections, dict):
                for sub_key, content in subsections.items():
                    if content and isinstance(content, dict):
                        filled = {k: v for k, v in content.items() if v}
                        if filled:
                            context_parts.append(f"\n## {phase_key} > {sub_key}")
                            for field_key, value in filled.items():
                                context_parts.append(f"- {field_key}: {value}")

                    # Render list items for this subsection if any
                    items_key = f"{phase_key}.{sub_key}"
                    if list_items and items_key in list_items:
                        items = list_items[items_key]
                        if items:
                            context_parts.append(f"\n## {phase_key} > {sub_key} (items)")
                            for item in items:
                                item_type = item.get("item_type", "item")
                                name = item.get("name", f"{item_type}")
                                context_parts.append(f"\n### {item_type}: {name}")
                                for k, v in item.items():
                                    if v and k not in ("item_type",):
                                        context_parts.append(f"- {k}: {v}")

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
        elif wizard_type == "scene_wizard":
            return await self._generate_scenes(config, project_context, template)
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

    def _get_wizard_config(self, template: Dict, wizard_key: str) -> Dict:
        """Find wizard_config from template by subsection key."""
        for phase in template.get("phases", []):
            for sub in phase.get("subsections", []):
                if sub.get("key") == wizard_key:
                    return sub.get("wizard_config", {})
        return {}

    def _build_field_instructions(self, field_emphasis: Dict) -> str:
        """Build per-field instructions based on emphasis levels."""
        field_labels = {
            "summary": "One-line scene description",
            "arena": "The location/setting",
            "inciting_incident": "What triggers the scene's conflict",
            "goal": "What the character wants in this scene",
            "subtext": "The emotional undercurrent beneath words and actions",
            "turning_point": "The key moment of change",
            "crisis": "The worst moment / tightest pressure",
            "climax": "How the scene peaks",
            "fallout": "Immediate consequences",
            "push_forward": "How this connects to the next scene",
        }
        lines = []
        for key in ["summary", "arena", "inciting_incident", "goal", "subtext",
                     "turning_point", "crisis", "climax", "fallout", "push_forward"]:
            emphasis = field_emphasis.get(key, "essential").upper()
            desc = field_labels[key]
            lines.append(f"- {key}: {desc} ({emphasis})")
        return "\n".join(lines)

    def _build_character_section(self, characters: list) -> str:
        """Build a formatted character section for the prompt."""
        if not characters:
            return ""
        parts = ["\n## Characters"]
        for char in characters:
            item_type = char.get("item_type", "character")
            name = char.get("name", "Unnamed")
            parts.append(f"\n### {item_type.replace('_', ' ').title()}: {name}")
            for k, v in char.items():
                if v and k not in ("item_type", "name"):
                    parts.append(f"- {k.replace('_', ' ').title()}: {v}")
        return "\n".join(parts)

    async def _generate_scenes(self, config: Dict, project_context: str, template: Dict) -> Dict:
        count_pref = str(config.get("count", "auto"))
        guidance = config.get("custom_guidance", "")
        characters = config.get("_characters", [])
        runtime_target = config.get("runtime_target", "")

        # Get consolidated config from wizard_config
        wizard_config = self._get_wizard_config(template, "scene_wizard")
        template_guidance = wizard_config.get("guidance_default", "")
        beat_mapping = wizard_config.get("beat_mapping_strategy", "")

        # All fields essential
        field_emphasis = {k: "essential" for k in [
            "summary", "arena", "inciting_incident", "goal", "subtext",
            "turning_point", "crisis", "climax", "fallout", "push_forward"
        ]}
        field_instructions = self._build_field_instructions(field_emphasis)
        character_section = self._build_character_section(characters)

        # Build count instruction
        if count_pref == "auto":
            count_instruction = "Determine the optimal number of scenes based on the story beats and runtime target."
        else:
            count_instruction = f"Generate {count_pref} scenes."

        prompt = f"""You are an expert short film screenwriting assistant specializing in scene structure planning.

## Project Context
{project_context}
{character_section}

## Scene Generation Task

### Scene Count
{count_instruction}

{template_guidance}

{"### Beat-to-Scene Mapping Strategy" + chr(10) + beat_mapping if beat_mapping else ""}

{"### Target Runtime: " + runtime_target if runtime_target else ""}

{"### Additional Guidance" + chr(10) + guidance if guidance else ""}

### Scene Field Requirements
Each scene uses these 10 fields. All fields are essential:

{field_instructions}

### Important Guidelines
- Explicitly reference the story beats from the project context. Each scene should map to one or more specific beats.
- Reference characters BY NAME. Show which characters appear in each scene and what they want.
- Each scene's summary should be a clear, visual one-line description.
- The push_forward field should create clear causal or thematic connections between scenes.
- Ensure the overall scene sequence covers the complete story arc from opening hook through resolution.

Return a JSON object with key "scenes" containing an array of scene objects. Each scene object must
have all 10 field keys (summary, arena, inciting_incident, goal, subtext, turning_point, crisis,
climax, fallout, push_forward)."""

        try:
            text = await chat_completion(
                messages=[
                    {"role": "system", "content": "You are an expert short film scene structure planner. Return valid JSON only."},
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

    async def _update_synopsis(
        self, prev_synopsis: str, new_scene_text: str, scene_summary: str
    ) -> str:
        """Regenerate the cumulative "story so far" prose synopsis after a scene.

        The whole synopsis is re-summarized each call (D-03) — never truncated
        mid-fact — and kept under a fixed word cap so it stays bounded on long,
        many-scene scripts. Prose-only output (D-04), routed through the
        provider-abstracted chat_completion (D-02) with json_mode=False.

        On any failure, logs and returns the previous synopsis unchanged so a
        synopsis-update error can never abort the full script-generation run.
        """
        word_cap = 400  # ~300-500 words per D-03; bounded so prompts stay small
        prev_block = (
            f"## Current story-so-far synopsis:\n{prev_synopsis}\n\n"
            if prev_synopsis
            else ""
        )
        prompt = f"""You maintain a running "story so far" synopsis for a screenplay being written scene by scene.

{prev_block}## The scene just written (summary: "{scene_summary}"):
{new_scene_text}

Rewrite the ENTIRE cumulative synopsis as a single continuous prose narrative that
incorporates the scene just written into everything that came before. The synopsis must:
- Carry forward established facts, objects, character states, relationships, and unresolved setups so later scenes stay consistent.
- Be a complete re-summary of the whole story so far (do NOT just append the new scene; integrate it).
- Stay under {word_cap} words. Tighten earlier material if needed rather than cutting facts mid-thought.
- Be prose only — no headings, no bullet lists, no JSON.

Return only the synopsis prose."""

        try:
            text = await chat_completion(
                messages=[
                    {
                        "role": "system",
                        "content": "You are a precise story editor who maintains a concise, factually-consistent running synopsis. Return prose only.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
                max_tokens=700,
                json_mode=False,
            )
            updated = (text or "").strip()
            return updated if updated else prev_synopsis
        except Exception as e:
            logger.error(f"Synopsis update error: {e}")
            return prev_synopsis

    # ------------------------------------------------------------------
    # Phase 3 — per-scene critique + targeted rewrite, and a whole-script
    # polish pass. The rubric axes are aligned to the three quality symptoms
    # the loop targets: flat/on-the-nose dialogue, weak structure/pacing, and
    # generic/identity-less output.
    # ------------------------------------------------------------------
    RUBRIC_AXES = ("subtext", "scene_turn", "escalation", "voice_distinction", "tone_identity")

    async def _critique_scene(
        self,
        scene_text: str,
        ep: Dict,
        prev_scene_text: str,
        project_context: str,
        doctrine: str = "",
    ) -> Optional[Dict]:
        """Score ONE written scene against the 5-axis quality rubric.

        Returns a dict {axis: int(1-5), ..., "notes": {axis: "actionable note"}}
        or None on any failure (caller treats None as "skip rewrite" — the
        critique pass must never abort or degrade generation).
        """
        prev_block = (
            f"## Previous scene (for continuity/voice comparison):\n{prev_scene_text}\n\n"
            if prev_scene_text
            else ""
        )
        prompt = f"""You are a demanding story editor scoring a single screenplay scene against a fixed rubric. Be strict and specific — reward only what is actually on the page.

## Project context (for tone/identity reference)
{project_context}

## Scene intent (what this scene is supposed to do)
{json.dumps(ep, indent=2)}

{prev_block}## The scene as written
{scene_text}

{doctrine}## Rubric — score each axis from 1 (poor) to 5 (excellent)
- subtext: dialogue implies wants/emotion indirectly; nothing is on-the-nose. (1 = characters announce feelings/goals; 5 = meaning lives beneath the words.)
- scene_turn: the value at stake flips between the top and the end of the scene. (1 = static, nothing changes; 5 = a clear, earned turn.)
- escalation: opposed wants pursued through changing tactics; pressure rises. (1 = repetitive/flat; 5 = genuine escalation.)
- voice_distinction: each character's lines are attributable without the cue. (1 = interchangeable voices; 5 = distinct, consistent voices.)
- tone_identity: the scene commits to the story's tone/genre and avoids generic AI clichés. (1 = generic/cliché; 5 = specific and identity-true.)

For each axis give an integer 1-5 and a SHORT actionable note (one sentence) on the single most important fix. If the axis is already strong, the note may say so.

Return ONLY a JSON object of exactly this shape:
{{"subtext": 3, "scene_turn": 3, "escalation": 3, "voice_distinction": 3, "tone_identity": 3, "notes": {{"subtext": "...", "scene_turn": "...", "escalation": "...", "voice_distinction": "...", "tone_identity": "..."}}}}"""

        try:
            text = await chat_completion(
                messages=[
                    {"role": "system", "content": "You are a rigorous screenplay story editor. Return only valid JSON matching the requested shape."},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=1500,
                json_mode=True,
                effort="medium",
            )
            data = json.loads(text)
            # Validate shape: every axis must be an int 1-5.
            for axis in self.RUBRIC_AXES:
                val = data.get(axis)
                if not isinstance(val, int) or not (1 <= val <= 5):
                    logger.warning(f"Critique missing/invalid axis '{axis}': {val!r}")
                    return None
            if not isinstance(data.get("notes"), dict):
                data["notes"] = {}
            return data
        except Exception as e:
            logger.error(f"Scene critique error: {e}")
            return None

    def _weak_axes(self, critique: Dict, threshold: int) -> List[str]:
        """Axes scoring below threshold, worst first."""
        scored = [(axis, critique.get(axis, 5)) for axis in self.RUBRIC_AXES]
        weak = [(axis, val) for axis, val in scored if isinstance(val, int) and val < threshold]
        weak.sort(key=lambda t: t[1])
        return [axis for axis, _ in weak]

    async def _rewrite_scene(
        self,
        scene_text: str,
        critique: Dict,
        weak_axes: List[str],
        ep: Dict,
        i: int,
        total: int,
        project_context: str,
        character_block: str,
        prev_scene_text: str,
        doctrine: str = "",
    ) -> Optional[str]:
        """Rewrite ONE scene addressing the critique's weak axes.

        Returns the rewritten screenplay body (title line already stripped) or
        None on failure (caller keeps the original scene).
        """
        summary = ep.get("summary", f"Scene {i + 1}")
        notes = critique.get("notes", {}) if isinstance(critique.get("notes"), dict) else {}
        fix_lines = "\n".join(
            f"- {axis} (scored {critique.get(axis)}): {notes.get(axis, 'strengthen this dimension')}"
            for axis in weak_axes
        )
        prev_block = (
            f"## Previous scene (match its tone, voice, and continuity):\n{prev_scene_text}\n\n"
            if prev_scene_text
            else ""
        )
        prompt = f"""You are an expert screenwriter revising one scene of a screenplay. A story editor scored the current draft and flagged specific weaknesses. Rewrite the WHOLE scene to fix them — do not patch a line here and there; deliver a stronger full scene that keeps the same story events and continuity.

## Project context
{project_context}
{character_block}

## Scene intent
{json.dumps(ep, indent=2)}

{prev_block}## Current draft (scene {i + 1} of {total})
{scene_text}

{doctrine}## Fix these weaknesses (from the story editor)
{fix_lines}

Keep the same plot events, characters, and place in the sequence. Preserve strict industry-standard screenplay layout (scene heading on its own line, ALL-CAPS character cues, parentheticals on their own line, blank lines between elements). Keep subtext beneath the dialogue — never have a character state a feeling or goal outright.

Output the screenplay NATIVELY as plain text (NOT JSON, no markdown code fences).
The FIRST line MUST be exactly:
TITLE: <a short title for this scene>
Then, beneath it, the full rewritten screenplay body."""

        try:
            text = await chat_completion(
                messages=[
                    {"role": "system", "content": "You are an expert screenwriter who lays out scenes in industry-standard screenplay format. Return the screenplay as native plain text only — no JSON, no markdown code fences."},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=8000,
                json_mode=False,
                thinking=True,
                effort="high",
            )
            parsed = self._parse_native_scene(text, summary, i)
            return parsed["content"]
        except Exception as e:
            logger.error(f"Scene rewrite error (scene {i + 1}): {e}")
            return None

    async def _polish_screenplay(
        self,
        screenplays: List[Dict],
        project_context: str,
        doctrine: str = "",
    ) -> List[Dict]:
        """Whole-screenplay polish pass — the only step that reads the full
        script end to end. Reviews cross-scene transitions, cumulative pacing,
        setup/payoff, and voice consistency, and returns REPLACEMENT bodies only
        for the scenes it chose to retouch (keyed by episode_index).

        Returns the possibly-updated screenplays list. On any failure the
        original list is returned unchanged (polish never aborts a run).
        """
        # Only successfully-generated scenes are eligible (skip failure dicts).
        good = [s for s in screenplays if "error" not in s and s.get("content")]
        if len(good) < 2:
            return screenplays  # nothing cross-scene to polish

        full_script = "\n\n".join(
            f"=== SCENE {s['episode_index'] + 1}: {s.get('title', '')} ===\n{s['content']}"
            for s in sorted(good, key=lambda s: s["episode_index"])
        )
        prompt = f"""You are a script editor doing a final polish pass over a COMPLETE screenplay. You can see every scene at once — something no single-scene pass can. Look for problems that only show up across the whole script:
- weak or repetitive transitions between scenes;
- cumulative pacing (does tension build across the script, or sag in the middle?);
- setups with no payoff, or payoffs with no setup;
- a character whose voice drifts or contradicts across scenes;
- repeated images, lines, or beats that should vary.

## Project context
{project_context}

{doctrine}## Full screenplay
{full_script}

Only retouch scenes that genuinely need it — leave strong scenes alone. For each scene you change, return its episode_index (0-based, matching the SCENE number minus 1) and the full revised screenplay body (native plain text, strict layout, no TITLE line, no code fences).

Return ONLY a JSON object of this shape:
{{"revisions": [{{"episode_index": 0, "content": "INT. ..."}}]}}
If nothing needs changing, return {{"revisions": []}}."""

        try:
            text = await chat_completion(
                messages=[
                    {"role": "system", "content": "You are a rigorous script editor. Return only valid JSON matching the requested shape."},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=16000,
                json_mode=True,
                effort="high",
            )
            data = json.loads(text)
            revisions = data.get("revisions", [])
            if not isinstance(revisions, list):
                return screenplays

            by_index = {}
            for rev in revisions:
                if not isinstance(rev, dict):
                    continue
                idx = rev.get("episode_index")
                content = rev.get("content")
                if isinstance(idx, int) and isinstance(content, str) and content.strip():
                    by_index[idx] = content.strip()

            if not by_index:
                return screenplays

            polished = []
            for s in screenplays:
                new_content = by_index.get(s.get("episode_index"))
                if new_content is not None and "error" not in s:
                    updated = dict(s)
                    updated["content"] = new_content
                    updated["polished"] = True
                    polished.append(updated)
                else:
                    polished.append(s)
            logger.info(f"Polish pass revised {len(by_index)} scene(s)")
            return polished
        except Exception as e:
            logger.error(f"Screenplay polish error: {e}")
            return screenplays

    async def summarize_episode(self, db, project) -> str:
        """Produce a BOUNDED prose continuity summary of an episode's screenplay.

        ESUM-01 (locked D2): a bounded summary for use as continuity context when
        writing LATER episodes — NOT the full prior script. Reads the episode's
        source text from ScreenplayContent by episode_index (never positionally)
        and routes through the provider-abstracted chat_completion with
        json_mode=False (prose, not JSON), mirroring _update_synopsis.

        Caller-commits convention (Phase 67): this method does NOT commit and does
        NOT mutate the project — it returns stripped prose; the trigger writes it.
        Empty source text returns "" (caller decides whether to write).
        """
        WORD_CAP = 250  # bounded — D2: not the full prior script; caps prompt size
        scene_text = _read_episode_text_by_index(db, project.id)
        if not scene_text.strip():
            return ""

        prompt = f"""Summarize this episode's screenplay for use as continuity context when writing LATER episodes of the same series. Capture: what happened (plot beats), changes in character state/relationships, and any setups left unresolved. Be factual and concise.
Stay under {WORD_CAP} words. Prose only — no headings, no bullet lists, no JSON. Do NOT reproduce the script.

Episode: {project.title}
{scene_text}

Return only the summary prose."""

        text = await chat_completion(
            messages=[
                {
                    "role": "system",
                    "content": "You are a precise story editor who writes concise, factual episode summaries for series continuity. Return prose only.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            max_tokens=500,
            json_mode=False,
        )
        return (text or "").strip()

    async def _generate_one_scene(
        self,
        ep: Dict,
        i: int,
        total: int,
        project_context: str,
        character_section: str,
        scene_outline: str,
        runtime_target: str,
        guidance: str,
        synopsis: str,
        prev_scene_text: str,
    ) -> Dict:
        """Generate ONE scene's screenplay via the improved phases 45-48 path.

        This is the single shared per-scene path used by BOTH _generate_scripts
        (the full-batch loop) and regenerate_single_scene (Phase 49 single-scene
        regenerate). The prompt body, LLM call, and native parse are byte-identical
        to the original inline loop body — moving them here MUST NOT change any
        anchor substring, the SCENE_MARKER, the system prompt, json_mode, or the
        returned {title, content, episode_index} shape (D-49-05).

        Returns {title, content, episode_index} on success, or the failure-branch
        dict {episode_index, title (=summary fallback), content "[Generation
        failed: ...]", error} on a chat_completion exception. This helper does NOT
        advance continuity (synopsis/prev_scene_text are read-only inputs); the
        caller owns continuity state.
        """
        summary = ep.get("summary", f"Scene {i + 1}")

        # Continuity block — injected ONLY when prior continuity state exists
        # (D-01/D-05). First/single scene gets nothing → behavior unchanged.
        continuity_block = (
            f"""## Story so far (running synopsis of all earlier scenes):
{synopsis}

## Previous scene (full text — match its tone, voice, and continuity):
{prev_scene_text}
"""
            if (synopsis or prev_scene_text)
            else ""
        )

        # Character block — section + an explicit distinct/consistent-voice
        # instruction. Emitted ONLY when characters exist; the empty/absent path
        # collapses to "" so the prompt is byte-identical to Phase 46 (D-47-04).
        # The anchor substring "distinct, consistent voice" is what the tests assert.
        character_block = (
            f"""{character_section}

## Character Voice
Give each named character a DISTINCT, CONSISTENT voice — distinct vocabulary, rhythm, formality, and verbal tics — so that two characters in the same scene never sound interchangeable. Where a character has no explicit voice cues, establish a voice for them and keep it consistent with how they have already spoken in earlier scenes (visible via the previous-scene text and the running synopsis above).

Before writing, derive a quick voice profile for each character in this scene from the fields above — their register (formal vs. slang), sentence length and rhythm, a verbal tic or two, and the subject they deflect away from. Then hold to it. The test: a reader should be able to tell who is speaking from the line alone, with the character cue removed. Never let two characters phrase things the same way."""
            if character_section
            else ""
        )

        # The "## Screenwriting Craft" block below is UNCONDITIONAL (Phase 48,
        # D-48-04): it appears in EVERY scene prompt — first/single scene and
        # the no-characters path — so it is a plain literal, NOT wrapped in any
        # if/else guard, and is added equally to both the empty- and
        # absent-characters paths (byte-identical contract holds).
        # The anchor substrings the tests assert (test_craft_guidance.py):
        #   "## Screenwriting Craft", "on-the-nose" (and "subtext"),
        #   "economical", "show, don't tell",
        #   "no internal or unfilmable description", "white space".
        # COLLISION GUARD: the craft text must contain NONE of "Story so far",
        # "Previous scene", "distinct, consistent voice", "## Characters",
        # "## Character Voice" (asserted ABSENT by continuity/voice suites).
        #
        # PROMPT CACHING (Phase 1): the prompt is split into a STABLE PREFIX
        # (invariant across every scene of a run — project context, characters,
        # outline, craft + layout rules) carried in the system message, and a
        # VOLATILE TAIL (continuity + this scene's task/data) carried in the
        # user message. The stable prefix is marked cacheable (cache_system) so
        # scenes 2..N read it from cache instead of reprocessing ~5-15KB each.
        # The full prompt text (prefix + tail) still contains every anchor
        # substring the tests assert — only WHERE each lives changed.
        stable_prefix = f"""You are an expert screenwriter.

## Project Context
{project_context}
{character_block}
{f'## Overall Target Runtime: {runtime_target}' if runtime_target else ''}
## Total scenes: {total}

## Full scene outline (for pacing context):
{scene_outline}

## Screenwriting Craft
Apply these craft principles to EACH scene (distinct from the layout rules below):
- Subtext: characters pursue their wants indirectly, so what they SAY rarely equals what they MEAN. Never let a character announce a feeling or a goal outright — that is on-the-nose dialogue and it is banned. Instead use concrete techniques: answer a question with a different question; deflect or change the subject; say the opposite of what is felt; leave a sentence unfinished; let a mundane surface topic (an object, a chore, an errand) carry the real conflict underneath. The emotion should be legible from behavior and evasion, not stated.
- Action economy: keep action lines lean and economical — present tense, concrete verbs, no filler or stage-direction padding.
- Show, don't tell: reveal character and emotion through visible behavior and action, with no internal or unfilmable description (no "she feels…", "he realizes…", "remembers that…"). If an emotion matters, externalize it — a gesture, a look, what a character does with their hands or with a nearby object.
- Every scene must turn: the dramatic value at stake (safe/threatened, trust/betrayal, hope/despair, winning/losing) must flip between the top of the scene and its end. If nothing changes, it is not a scene — find the turn. Enter the scene as late as possible and leave the moment its turn lands; cut the throat-clearing at both ends.
- Conflict and escalation: give the characters present opposed wants and let them pursue those wants through changing tactics — a character who fails with one approach tries a different one, raising the pressure rather than repeating the beat.
- Pacing and white space: vary the rhythm — break dense action into shorter beats and let white space carry tension; never wall-of-text.

## Tone and Identity
This screenplay has a specific identity — read the genre, tone, and (for series) the bible's tone-and-style notes from the Project Context above, and commit to them. Every scene should feel like it belongs to THIS story and no other: let the tone shape word choice, the kind of imagery, the density of the prose, and the pace of the dialogue. Prefer concrete, specific, sensory detail rooted in this world over generic coverage.

Avoid the tells of generic AI-written screenplays. In particular:
- No stock atmosphere clichés: golden-hour light, rain on a window as a mood-setter, a single tear rolling down a cheek, a held breath, a heartbeat pounding — unless the story genuinely earns the specific image.
- No expository dialogue that exists only to inform the audience ("As you know…", characters explaining shared history to each other, on-the-nose recaps).
- No placeholder specificity: name locations and objects concretely instead of "a nondescript room" / "a generic office"; give props and settings texture particular to this world.
- No summarizing narration in the action lines — stay in the concrete present of what the camera sees and hears.

Write a proper screenplay for each scene using strict industry-standard layout:
- The scene heading (INT./EXT. LOCATION - TIME) is on its OWN line.
- Action lines are present-tense, visual, and describe only what can be seen or heard.
- Character cues are in ALL CAPS on their own line above the dialogue.
- Parentheticals (wrylies) go on their OWN line beneath the character cue.
- Dialogue sits beneath the character cue (and any parenthetical).
- Put a BLANK LINE between distinct elements (heading, action, each dialogue block).
- Pace each scene for its role in the overall {runtime_target or 'short film'} runtime.
- Distribute the total runtime naturally across scenes — not all scenes need equal screen time.

Output the screenplay NATIVELY as plain text (NOT JSON, no markdown code fences).
The FIRST line MUST be exactly:
TITLE: <a short title for this scene>
Then, beneath it, write the full screenplay body using the layout rules above."""

        volatile_task = f"""{continuity_block}## YOUR TASK: Write scene {i + 1} of {total}
Scene summary: "{summary}"

## Full scene data:
{json.dumps(ep, indent=2)}

## How to use the scene data
Treat the fields above as the dramatic engine of this scene, not as notes to transcribe:
- goal: what the point-of-view character is actively trying to get in this scene — every beat should serve or obstruct it.
- subtext: the real emotional current under the dialogue — keep it beneath the surface; do NOT have anyone say it aloud.
- turning_point / crisis / climax: the scene must build to and pass through its turn — the value at stake flips here; make that shift land through action and behavior.
- fallout: the immediate cost or consequence the turn leaves behind.
- push_forward: end the scene on a beat that opens a question or pressure the next scene must answer — a hook, not a tidy resolution.
Do not restate these labels in the screenplay; dramatize them.

{f'Custom guidance: {guidance}' if guidance else ''}"""

        try:
            logger.info(f"Generating script for scene {i + 1}/{total}: {summary}")
            text = await chat_completion(
                messages=[
                    {"role": "system", "content": "You are an expert screenwriter who lays out scenes in industry-standard screenplay format. Return the screenplay as native plain text only — no JSON, no markdown code fences."},
                    {"role": "system", "content": stable_prefix},
                    {"role": "user", "content": volatile_task}
                ],
                temperature=0.7,
                max_tokens=8000,
                json_mode=False,
                thinking=True,
                effort="high",
                cache_system=True,
            )

            return self._parse_native_scene(text, summary, i)
        except Exception as e:
            logger.error(f"Script generation error for scene {i + 1}: {e}")
            return {
                "episode_index": i,
                "title": summary,
                "content": f"[Generation failed: {str(e)}]",
                "error": str(e),
            }

    def _parse_native_scene(self, text: str, summary: str, i: int) -> Dict:
        """Parse a native plain-text screenplay response into
        {title, content, episode_index} (D-46-01).

        Shared by _generate_one_scene and _rewrite_scene so both handle a stray
        code fence and an optional leading `TITLE:` line identically. The
        provider does NOT strip code fences in native mode (fence-stripping is
        json_mode-gated in ai_provider.py), so tolerate a stray leading/trailing
        fence here. Never run json.loads on a scene result.
        """
        text = (text or "").strip()
        if text.startswith("```"):
            lines = text.split("\n")
            # Drop the opening fence line (```/```text).
            lines = lines[1:]
            # Drop a trailing closing fence line if present.
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            text = "\n".join(lines).strip()

        # Split a leading `TITLE:` line (case-insensitive, optional whitespace)
        # off the top; the rest is the screenplay body.
        title = ""
        content = text
        split_title_line = False
        first_nl = text.find("\n")
        first_line = text if first_nl == -1 else text[:first_nl]
        if first_line.strip().lower().startswith("title:"):
            split_title_line = True
            title = first_line.split(":", 1)[1].strip()
            rest = "" if first_nl == -1 else text[first_nl + 1:]
            content = rest.lstrip("\n")

        # Never fail a scene over a missing/empty title — fall back to the scene
        # summary (D-46-01). Only re-glue the full text into content when no
        # TITLE line was split off; if a TITLE: line was present but blank, keep
        # the body we already separated (don't re-inject the literal "TITLE:").
        if not title:
            title = summary
            if not split_title_line:
                content = text

        return {
            "title": title,
            "content": content,
            "episode_index": i,
        }

    async def _generate_scripts(self, config: Dict, project_context: str, template: Dict) -> Dict:
        episodes = config.get("episodes", [])
        runtime_target = config.get("runtime_target", "")
        guidance = config.get("custom_guidance", "")
        characters = config.get("_characters", [])

        if not episodes:
            return {"screenplays": [], "error": "No episodes/scenes provided to write scripts for."}

        # Build the character section ONCE (it does not vary per scene). Reuses
        # the empty-list-safe _build_character_section: an absent/empty
        # _characters yields "" so the prompt is byte-identical to Phase 46 (D-47-04).
        character_section = self._build_character_section(characters)

        # Build a brief outline of ALL scenes so each call has structural context
        scene_outline = "\n".join(
            f"  {i + 1}. {ep.get('summary', f'Scene {i + 1}')}"
            for i, ep in enumerate(episodes)
        )

        # Continuity state, rebuilt fresh from scratch each run (D-07). Empty for
        # the first/single scene so no continuity block is injected (D-05).
        synopsis = ""
        prev_scene_text = ""

        critique_enabled = getattr(settings, "SCREENPLAY_CRITIQUE_ENABLED", False)
        threshold = getattr(settings, "SCREENPLAY_CRITIQUE_THRESHOLD", 4)
        rubric_scores = []  # per-scene critique metadata for _meta (Phase 3)

        # Craft doctrine (books Phase 2): format-tagged book concepts fetched by
        # the wizard endpoint and stowed in config. Empty list → every block
        # renders "" and the prompts are byte-identical to the pre-doctrine path.
        doctrine_cards = config.get("_doctrine_cards") or []
        critique_doctrine = doctrine_service.critique_block(doctrine_cards)

        screenplays = []
        for i, ep in enumerate(episodes):
            summary = ep.get("summary", f"Scene {i + 1}")

            # Delegate the per-scene prompt + LLM call + native parse to the
            # single shared helper (Phase 49). Behavior-identical to the prior
            # inline loop body (D-49-05).
            scene = await self._generate_one_scene(
                ep=ep,
                i=i,
                total=len(episodes),
                project_context=project_context,
                character_section=character_section,
                scene_outline=scene_outline,
                runtime_target=runtime_target,
                guidance=guidance,
                synopsis=synopsis,
                prev_scene_text=prev_scene_text,
            )

            # Phase 3: critique the fresh scene and, if any rubric axis is weak,
            # rewrite it once. Gated behind the flag; any critique/rewrite failure
            # leaves the original scene untouched (never aborts a run). Runs BEFORE
            # continuity advances so the improved text feeds later scenes.
            if critique_enabled and "error" not in scene:
                critique = await self._critique_scene(
                    scene["content"], ep, prev_scene_text, project_context,
                    doctrine=critique_doctrine,
                )
                if critique is not None:
                    weak = self._weak_axes(critique, threshold)
                    entry = {"episode_index": i, "scores": {a: critique.get(a) for a in self.RUBRIC_AXES}}
                    if weak:
                        character_block = self._build_character_section(characters)
                        rewritten = await self._rewrite_scene(
                            scene_text=scene["content"],
                            critique=critique,
                            weak_axes=weak,
                            ep=ep,
                            i=i,
                            total=len(episodes),
                            project_context=project_context,
                            character_block=character_block,
                            prev_scene_text=prev_scene_text,
                            doctrine=doctrine_service.rewrite_block(doctrine_cards, weak),
                        )
                        if rewritten:
                            scene = dict(scene)
                            scene["content"] = rewritten
                            scene["rewritten"] = True
                            entry["rewrote_axes"] = weak
                    rubric_scores.append(entry)

            screenplays.append(scene)

            # Advance continuity state ONLY on success — a failed scene must
            # not poison prev_scene_text or the synopsis (D-05). A failure dict
            # carries an "error" key.
            if "error" not in scene:
                prev_scene_text = scene["content"]
                synopsis = await self._update_synopsis(synopsis, prev_scene_text, summary)

        # Phase 3: whole-screenplay polish pass — the only step that reads the
        # full script end to end (cross-scene transitions, cumulative pacing,
        # setup/payoff, voice drift). Gated; returns the list unchanged on failure.
        if getattr(settings, "SCREENPLAY_POLISH_ENABLED", False):
            screenplays = await self._polish_screenplay(
                screenplays, project_context,
                doctrine=doctrine_service.polish_block(doctrine_cards),
            )

        result = {"screenplays": screenplays, "synopsis": synopsis}
        if rubric_scores:
            result["rubric_scores"] = rubric_scores
        return result

    async def regenerate_single_scene(
        self,
        config: Dict,
        project_context: str,
        episode_index: int,
        synopsis: str,
        prev_scene_text: str,
    ) -> Dict:
        """Regenerate ONE scene by episode_index via the improved phases 45-48 path.

        Reuses _generate_one_scene so the regenerate prompt is byte-identical to
        the batch prompt for that index (D-49-01). The caller supplies the
        continuity context (the running synopsis up to that scene + the
        immediately-preceding scene's stored text). This method does NOT advance
        or rewrite the global synopsis — a single-scene regenerate is a quality
        spot-check, not a full re-thread (D-49-05).

        Returns the {title, content, episode_index} dict (or the failure-branch
        dict on a chat_completion exception). Raises ValueError if episode_index
        is out of range.
        """
        episodes = config.get("episodes", [])
        if not (0 <= episode_index < len(episodes)):
            raise ValueError(
                f"episode_index {episode_index} out of range (0..{len(episodes) - 1})"
            )

        runtime_target = config.get("runtime_target", "")
        guidance = config.get("custom_guidance", "")
        characters = config.get("_characters", [])

        # Build character_section + scene_outline exactly as _generate_scripts
        # does so the regenerate prompt matches the batch prompt for this index.
        character_section = self._build_character_section(characters)
        scene_outline = "\n".join(
            f"  {idx + 1}. {ep.get('summary', f'Scene {idx + 1}')}"
            for idx, ep in enumerate(episodes)
        )

        return await self._generate_one_scene(
            ep=episodes[episode_index],
            i=episode_index,
            total=len(episodes),
            project_context=project_context,
            character_section=character_section,
            scene_outline=scene_outline,
            runtime_target=runtime_target,
            guidance=guidance,
            synopsis=synopsis,
            prev_scene_text=prev_scene_text,
        )

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
            f"- {f['key']} ({f['label']}): {f.get('placeholder', f['label'])}" for f in empty_fields
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
        item_type: Optional[str] = None,
    ):
        """Phase 1: Stream conversational response for action mode. Yields text chunks."""
        fields_desc = "\n".join(
            f"- {f.get('key')}: {f.get('label', f.get('key'))} ({f.get('type', 'text')})"
            for f in field_definitions
        )
        current_desc = json.dumps(
            {k: v for k, v in current_content.items() if v}, indent=2
        ) if current_content else "{}"

        create_section = ""
        if item_type:
            create_section = f"""
## Creating New {item_type.replace('_', ' ').title()}s
You may also create new {item_type.replace('_', ' ')}s. For each new {item_type.replace('_', ' ')} you will create,
describe it conversationally using the available fields above. Be specific about the content of each field."""

        action_stream_prompt = f"""{system_prompt}

## Project Context
{project_context}

## Current Section Fields
Available fields you can modify:
{fields_desc}

## Current Values
{current_desc}
{create_section}
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
        item_type: Optional[str] = None,
    ) -> Dict:
        """Phase 2: Extract field_updates (and optionally list_item_creates) via JSON-mode call."""
        fields_desc = "\n".join(
            f"- {f.get('key')}: {f.get('label', f.get('key'))} ({f.get('type', 'text')})"
            for f in field_definitions
        )
        current_desc = json.dumps(
            {k: v for k, v in current_content.items() if v}, indent=2
        ) if current_content else "{}"

        if item_type:
            item_label = item_type.replace('_', ' ')
            task_instructions = f"""Based on what the assistant described, return a JSON object with:
- "field_updates": an object mapping field keys to their new string values (for subsection-level edits). Use {{}} if none.
- "list_item_creates": an array of objects, each containing field keys mapped to string values for a NEW {item_label} to create. Use [] if none.

Only include items the assistant explicitly described creating."""
        else:
            task_instructions = """Based on what the assistant described, return a JSON object with exactly one key:
- "field_updates": an object mapping field keys to their new string values.
Use an empty object {} if no changes were described.
Only include fields that the assistant explicitly mentioned changing."""

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
{task_instructions}"""

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
            return {
                "field_updates": result.get("field_updates", {}),
                "list_item_creates": result.get("list_item_creates", []),
            }
        except Exception as e:
            logger.error(f"Action extract updates error: {e}")
            return {"field_updates": {}, "list_item_creates": []}

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
