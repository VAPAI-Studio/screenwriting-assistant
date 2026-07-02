#!/usr/bin/env python
"""
A/B screenplay-quality evaluation (Phase 4).

Generates the SAME project two ways and scores both with the 5-axis rubric,
using a FIXED judge model so you compare screenplays, not judges:

  BASELINE : ANTHROPIC_MODEL=claude-sonnet-4-6, temperature 0.7, no quality loop
             (approximates the pre-improvement single-pass pipeline)
  IMPROVED : ANTHROPIC_MODEL=claude-opus-4-8, adaptive thinking + effort,
             per-scene critique+rewrite and the whole-script polish pass

The judge is the rubric in template_ai_service._critique_scene, always run on
claude-opus-4-8 so both variants are scored by the same evaluator.

This is a STANDALONE script (not a pytest test) — it makes real, paid API calls.
Run it manually:

    cd backend
    PYTHONPATH=. venv/bin/python scripts/eval_screenplay.py
    # options:
    PYTHONPATH=. venv/bin/python scripts/eval_screenplay.py --baseline-model claude-sonnet-4-6 \
        --improved-model claude-opus-4-8 --judge-model claude-opus-4-8

Reads ANTHROPIC_API_KEY from backend/.env (or the environment). The .env
ANTHROPIC_MODEL is ignored — each variant sets its own model.

INTERPRETING THE RESULT — two caveats:
  1. Rubric saturation. The craft guidance (Phase 2) is baked into the scene
     prompt and cannot be turned off by a flag, so BOTH variants use it. With
     that guidance in place, even the baseline model tends to score 4-5 on most
     axes and the numeric table can tie. The delta measures model + quality-loop
     only, NOT the Phase-2 prompt gains (which apply to both). When the table
     ties near 5/5, read the actual pages: run with --dump and compare them, or
     use the side-by-side compare in the app for a human verdict.
  2. Judge/generator overlap. When --improved-model and --judge-model are the
     same, the judge shares a model family with the improved generator. Keep the
     judge fixed across both variants (it is, by default) so at least the
     comparison is apples-to-apples.
"""
import argparse
import asyncio
import os
import sys
from pathlib import Path

# Make `app` importable and load .env (but never let .env pin the model).
BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))
_env = BACKEND / ".env"
if _env.exists():
    for _line in _env.read_text().splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _v = _line.split("=", 1)
            if _k.strip() == "ANTHROPIC_MODEL":
                continue  # each variant sets its own model
            os.environ.setdefault(_k.strip(), _v.strip())

from app.config import settings  # noqa: E402
from app.services.template_ai_service import template_ai_service  # noqa: E402


# A small, self-contained sample project (standalone short film, no DB needed).
SAMPLE_CONTEXT = (
    "## idea > idea_wizard\n"
    "- genre: Grounded drama\n"
    "- tone: Restrained, melancholic, naturalistic — no melodrama\n"
    "- initial_idea: A woman closes out her late father's failing hardware store "
    "over one afternoon, deciding what to keep.\n"
)

SAMPLE_CONFIG = {
    "runtime_target": "10-minute short film",
    "_characters": [
        {"item_type": "protagonist", "name": "LENA",
         "core_trait": "controlled; keeps grief behind a flat affect",
         "fatal_flaw": "cannot ask for what she needs",
         "dialogue_style": "clipped, understated, answers questions with questions"},
        {"item_type": "supporting", "name": "MARCUS",
         "role": "the father's old employee, wants to keep the store open",
         "dialogue_style": "warm, digressive, tells stories to avoid the point"},
    ],
    "episodes": [
        {"summary": "Lena unlocks the shuttered store and finds Marcus already inside, restocking",
         "goal": "get Marcus to accept the store is closing",
         "subtext": "she can't say she misses her father",
         "turning_point": "Marcus reveals her father kept her childhood drawings in the register",
         "crisis": "acknowledge the grief or stay in control",
         "climax": "she pockets one drawing and keeps working",
         "fallout": "Marcus stops restocking",
         "push_forward": "a customer's knock at the locked door"},
        {"summary": "A regular customer wants one last item; Lena and Marcus disagree on whether to sell",
         "goal": "close the transaction and the day",
         "subtext": "selling the last item makes the ending real",
         "turning_point": "the customer turns out to have known her father",
         "crisis": "give the item away or hold the line",
         "climax": "she gives it away for free",
         "fallout": "Marcus finally hands over his keys",
         "push_forward": "the lights go off, the two stand in the dark store"},
    ],
}

AXES = template_ai_service.RUBRIC_AXES


async def _score_screenplays(screenplays, episodes, judge_model):
    """Score each generated scene with the rubric judge (fixed judge_model)."""
    orig_model = settings.ANTHROPIC_MODEL
    settings.ANTHROPIC_MODEL = judge_model
    try:
        per_scene = []
        prev = ""
        for s in screenplays:
            if "error" in s or not s.get("content"):
                continue
            ep = episodes[s["episode_index"]] if s["episode_index"] < len(episodes) else {}
            critique = await template_ai_service._critique_scene(
                s["content"], ep, prev, SAMPLE_CONTEXT
            )
            if critique:
                per_scene.append(critique)
            prev = s["content"]
        return per_scene
    finally:
        settings.ANTHROPIC_MODEL = orig_model


async def _generate(model, *, loop_enabled):
    """Generate the sample screenplay under a given model + loop setting."""
    orig = (settings.ANTHROPIC_MODEL,
            settings.SCREENPLAY_CRITIQUE_ENABLED,
            settings.SCREENPLAY_POLISH_ENABLED)
    settings.ANTHROPIC_MODEL = model
    settings.SCREENPLAY_CRITIQUE_ENABLED = loop_enabled
    settings.SCREENPLAY_POLISH_ENABLED = loop_enabled
    try:
        return await template_ai_service._generate_scripts(
            dict(SAMPLE_CONFIG), SAMPLE_CONTEXT, {}
        )
    finally:
        (settings.ANTHROPIC_MODEL,
         settings.SCREENPLAY_CRITIQUE_ENABLED,
         settings.SCREENPLAY_POLISH_ENABLED) = orig


def _averages(per_scene):
    """Mean score per axis + overall, across scored scenes."""
    if not per_scene:
        return {axis: 0.0 for axis in AXES}, 0.0
    means = {}
    for axis in AXES:
        vals = [c[axis] for c in per_scene if isinstance(c.get(axis), int)]
        means[axis] = sum(vals) / len(vals) if vals else 0.0
    overall = sum(means.values()) / len(AXES)
    return means, overall


def _print_table(baseline_means, baseline_overall, improved_means, improved_overall):
    print("\n" + "=" * 68)
    print(f"{'AXIS':<20}{'BASELINE':>12}{'IMPROVED':>12}{'DELTA':>12}")
    print("-" * 68)
    for axis in AXES:
        b, im = baseline_means[axis], improved_means[axis]
        print(f"{axis:<20}{b:>12.2f}{im:>12.2f}{im - b:>+12.2f}")
    print("-" * 68)
    print(f"{'OVERALL':<20}{baseline_overall:>12.2f}{improved_overall:>12.2f}"
          f"{improved_overall - baseline_overall:>+12.2f}")
    print("=" * 68)
    print("(scores are 1-5 per axis, judged by the same rubric model on both variants)\n")


async def main():
    ap = argparse.ArgumentParser(description="A/B screenplay quality eval")
    ap.add_argument("--baseline-model", default="claude-sonnet-4-6")
    ap.add_argument("--improved-model", default="claude-opus-4-8")
    ap.add_argument("--judge-model", default="claude-opus-4-8")
    ap.add_argument("--dump", action="store_true",
                    help="print the full generated scenes for both variants "
                         "(the rubric can saturate near 5/5 — read the pages too)")
    args = ap.parse_args()

    episodes = SAMPLE_CONFIG["episodes"]

    print(f"BASELINE generating with {args.baseline_model} (loop OFF) ...")
    baseline = await _generate(args.baseline_model, loop_enabled=False)
    print(f"IMPROVED generating with {args.improved_model} (loop ON) ...")
    improved = await _generate(args.improved_model, loop_enabled=True)

    print(f"Judging both with {args.judge_model} ...")
    baseline_scores = await _score_screenplays(baseline["screenplays"], episodes, args.judge_model)
    improved_scores = await _score_screenplays(improved["screenplays"], episodes, args.judge_model)

    b_means, b_overall = _averages(baseline_scores)
    i_means, i_overall = _averages(improved_scores)
    _print_table(b_means, b_overall, i_means, i_overall)

    # Also surface which improved scenes the loop rewrote, if any.
    rewrote = [e["episode_index"] for e in improved.get("rubric_scores", []) if "rewrote_axes" in e]
    if rewrote:
        print(f"Improved pipeline rewrote scene(s): {rewrote}")
    polished = [s["episode_index"] for s in improved["screenplays"] if s.get("polished")]
    if polished:
        print(f"Improved pipeline polished scene(s): {polished}")

    if args.dump:
        for label, data in (("BASELINE", baseline), ("IMPROVED", improved)):
            print("\n" + "#" * 68 + f"\n# {label}\n" + "#" * 68)
            for s in data["screenplays"]:
                print(f"\n--- scene {s['episode_index']}: {s.get('title','')} ---")
                print(s.get("content", ""))


if __name__ == "__main__":
    asyncio.run(main())
