"""Doctrine service (books roadmap Phase 2) — pure-helper unit tests.

DB-backed selection (build_doctrine_cards) is exercised against the live stack;
here we cover the pure formatting/selection helpers and the prompt-injection
contract: empty cards must render empty blocks so the critique/rewrite/polish
prompts stay byte-identical to the pre-doctrine pipeline.
"""

from app.services import doctrine_service


CARDS = [
    {
        "name": "Scene Turn",
        "definition": "The value at stake must flip between scene start and end.",
        "questions": ["Does the value flip?", "Where is the turn?"],
        "tags": ["scene_design", "structure", "short_film"],
        "source": "Writing Short Films (Linda J. Cowgill)",
        "quote": "A scene without a turn is not a scene.",
    },
    {
        "name": "Distinct Voices",
        "definition": "Each character's lines must be attributable without the cue.",
        "questions": ["Cover the cues — can you tell who speaks?"],
        "tags": ["character", "dialogue", "short_film"],
        "source": "Writing the Short Film (Cooper & Dancyger)",
    },
]


class TestFormatBlock:
    def test_empty_cards_render_empty_string(self):
        assert doctrine_service.format_block([]) == ""
        assert doctrine_service.critique_block([]) == ""
        assert doctrine_service.rewrite_block([], ["subtext"]) == ""
        assert doctrine_service.polish_block([]) == ""

    def test_block_contains_name_definition_questions_and_quote(self):
        block = doctrine_service.format_block(CARDS)
        assert "Scene Turn" in block
        assert "value at stake" in block
        assert "- Check: Does the value flip?" in block
        assert '"A scene without a turn is not a scene."' in block
        assert "Cowgill" in block  # source attribution

    def test_max_chars_cap_drops_trailing_cards(self):
        block = doctrine_service.format_block(CARDS, max_chars=150)
        assert "Scene Turn" in block
        assert "Distinct Voices" not in block

    def test_critique_block_instructs_naming_concepts(self):
        block = doctrine_service.critique_block(CARDS)
        assert block.startswith("## Craft doctrine")
        assert "NAME the concept" in block
        assert block.endswith("\n\n")  # composes cleanly before "## Rubric"


class TestSelectForAxes:
    def test_axis_filter_matches_tags(self):
        picked = doctrine_service.select_for_axes(CARDS, ["voice_distinction"])
        assert [c["name"] for c in picked] == ["Distinct Voices"]

    def test_scene_turn_axis_matches_structure_tags(self):
        picked = doctrine_service.select_for_axes(CARDS, ["scene_turn"])
        assert [c["name"] for c in picked] == ["Scene Turn"]

    def test_no_tag_match_falls_back_to_all_cards(self):
        no_tags = [dict(c, tags=["theme"]) for c in CARDS]
        assert doctrine_service.select_for_axes(no_tags, ["subtext"]) == no_tags

    def test_unknown_axis_returns_all(self):
        assert doctrine_service.select_for_axes(CARDS, ["nonexistent"]) == CARDS


class TestTemplateFormatTag:
    def test_short_movie_maps_to_short_film(self):
        assert doctrine_service.format_tag_for_template("short_movie") == "short_film"

    def test_unknown_template_returns_none_and_no_cards(self):
        assert doctrine_service.format_tag_for_template("unknown") is None
        # build_doctrine_cards must short-circuit (no DB hit) for unmapped templates
        assert doctrine_service.build_doctrine_cards("unknown", db=None) == []
