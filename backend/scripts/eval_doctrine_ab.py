#!/usr/bin/env python
"""A/B craft-doctrine evaluation (books roadmap — Fase 2 validation).

Generates the SAME sample project twice with the SAME model and the quality
loop ON in both runs; the ONLY difference is the doctrine:

  SIN DOCTRINA : config without _doctrine_cards  (critique/rewrite/polish
                 prompts render the empty doctrine block — pre-Phase-2 path)
  CON DOCTRINA : config["_doctrine_cards"] = build_doctrine_cards(...) from
                 the local library DB (the real wizard path)

The judge is _critique_scene with its default doctrine="" on a FIXED judge
model, so both variants are scored by an identical, doctrine-free evaluator.

STANDALONE script — real, paid API calls. Requires the local docker DB up
(the doctrine cards come from the book library). Run:

    cd backend
    PYTHONPATH=. venv/bin/python scripts/eval_doctrine_ab.py
    # options:
    PYTHONPATH=. venv/bin/python scripts/eval_doctrine_ab.py \
        --model claude-opus-4-8 --judge-model claude-opus-4-8 \
        --template short_movie --dump

Caveat (same as eval_screenplay.py): the rubric can saturate near 5/5. When
the table ties, read the pages with --dump — doctrine gains often show up as
named-concept notes, sharper subtext and turns, not as +1 on an axis.
"""
import argparse
import asyncio
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

# Reuses eval_screenplay's .env loading (module-level), sample project & judge.
from scripts.eval_screenplay import (  # noqa: E402
    SAMPLE_CONFIG, SAMPLE_CONTEXT, _averages, _print_table, _score_screenplays,
)

from app.config import settings  # noqa: E402
from app.db import SessionLocal  # noqa: E402
from app.services import doctrine_service  # noqa: E402
from app.services.template_ai_service import template_ai_service  # noqa: E402


async def _generate(model: str, doctrine_cards):
    """Generate the sample screenplay; loop ON; doctrine cards as given."""
    orig = (settings.ANTHROPIC_MODEL,
            settings.SCREENPLAY_CRITIQUE_ENABLED,
            settings.SCREENPLAY_POLISH_ENABLED)
    settings.ANTHROPIC_MODEL = model
    settings.SCREENPLAY_CRITIQUE_ENABLED = True
    settings.SCREENPLAY_POLISH_ENABLED = True
    config = dict(SAMPLE_CONFIG)
    if doctrine_cards:
        config["_doctrine_cards"] = doctrine_cards
    try:
        return await template_ai_service._generate_scripts(config, SAMPLE_CONTEXT, {})
    finally:
        (settings.ANTHROPIC_MODEL,
         settings.SCREENPLAY_CRITIQUE_ENABLED,
         settings.SCREENPLAY_POLISH_ENABLED) = orig


def _loop_activity(result):
    """(rewrote_scene_indexes, polished_scene_indexes) from a generation result."""
    rewrote = [e["episode_index"] for e in result.get("rubric_scores", [])
               if "rewrote_axes" in e]
    polished = [s["episode_index"] for s in result["screenplays"] if s.get("polished")]
    return rewrote, polished


async def main():
    ap = argparse.ArgumentParser(description="A/B doctrine-in-generation eval")
    ap.add_argument("--model", default="claude-opus-4-8",
                    help="generator model for BOTH variants")
    ap.add_argument("--judge-model", default="claude-opus-4-8")
    ap.add_argument("--template", default="short_movie",
                    help="template id whose format doctrine to load")
    ap.add_argument("--dump", action="store_true",
                    help="print the full generated scenes for both variants")
    args = ap.parse_args()

    db = SessionLocal()
    try:
        cards = doctrine_service.build_doctrine_cards(args.template, db)
    finally:
        db.close()
    if not cards:
        sys.exit(f"No doctrine cards for template '{args.template}' — is the "
                 "library loaded and the docker DB up? Aborting: A/B would be vacuous.")
    print(f"Doctrine: {len(cards)} cards for template '{args.template}' "
          f"({sum(1 for c in cards if c.get('quote'))} with quotes)")
    for c in cards:
        print(f"  - {c['name']}  [{c['source']}]")

    episodes = SAMPLE_CONFIG["episodes"]

    print(f"\nSIN DOCTRINA generating with {args.model} (loop ON) ...")
    sin = await _generate(args.model, None)
    print(f"CON DOCTRINA generating with {args.model} (loop ON) ...")
    con = await _generate(args.model, cards)

    print(f"Judging both with {args.judge_model} (doctrine-free judge) ...")
    sin_scores = await _score_screenplays(sin["screenplays"], episodes, args.judge_model)
    con_scores = await _score_screenplays(con["screenplays"], episodes, args.judge_model)

    s_means, s_overall = _averages(sin_scores)
    c_means, c_overall = _averages(con_scores)
    # _print_table labels columns BASELINE/IMPROVED; here they mean SIN/CON doctrina.
    print("\n(BASELINE = sin doctrina, IMPROVED = con doctrina)")
    _print_table(s_means, s_overall, c_means, c_overall)

    for label, result in (("SIN", sin), ("CON", con)):
        rewrote, polished = _loop_activity(result)
        print(f"{label} doctrina — rewrote: {rewrote or 'none'}, polished: {polished or 'none'}")

    if args.dump:
        for label, data in (("SIN DOCTRINA", sin), ("CON DOCTRINA", con)):
            print("\n" + "#" * 68 + f"\n# {label}\n" + "#" * 68)
            for s in data["screenplays"]:
                print(f"\n--- scene {s['episode_index']}: {s.get('title', '')} ---")
                print(s.get("content", ""))


if __name__ == "__main__":
    asyncio.run(main())
