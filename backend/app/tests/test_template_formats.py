"""
Phase 3 — Templates por formato.

Guards the multi-template contract:
- every template JSON loads, carries a `format` field matching a concept
  format tag, and exposes the wizard subsections the backend keys on
  (WIZARD_RESULT_SCHEMAS / template_ai_service assume these exact keys);
- TemplateType enum and template files stay in sync;
- doctrine routing reads the template's `format` field;
- pipeline composer targets are the deduped union across all templates.
"""

from app.models.database import TemplateType
from app.services import doctrine_service
from app.services.pipeline_composer import pipeline_composer
from app.templates import get_template, list_templates

# Backend code paths that key on these exact subsection keys:
# agent_review_middleware.WIZARD_RESULT_SCHEMAS, template_ai_service
# (_get_wizard_config("scene_wizard")), wizards endpoint, socratic context.
REQUIRED_WIZARD_KEYS = {"idea_wizard", "scene_wizard", "script_writer_wizard"}
REQUIRED_PHASE_IDS = ["idea", "story", "scenes", "write"]
KNOWN_FORMAT_TAGS = {"short_film", "sketch", "series", "feature", "ad"}


def _subsection_keys(template: dict) -> set:
    return {
        sub["key"]
        for phase in template.get("phases", [])
        for sub in phase.get("subsections", [])
    }


class TestTemplateConfigs:
    def test_enum_and_files_in_sync(self):
        """Every TemplateType value has a JSON file and vice versa."""
        listed = {t["id"] for t in list_templates()}
        enum_values = {t.value for t in TemplateType}
        assert listed == enum_values

    def test_every_template_has_valid_format(self):
        for meta in list_templates():
            template = get_template(meta["id"])
            assert template.get("format") in KNOWN_FORMAT_TAGS, (
                f"template {meta['id']} has format={template.get('format')!r}"
            )

    def test_list_templates_exposes_format(self):
        for meta in list_templates():
            assert meta.get("format") in KNOWN_FORMAT_TAGS

    def test_every_template_has_required_wizards_and_phases(self):
        for meta in list_templates():
            template = get_template(meta["id"])
            phase_ids = [p["id"] for p in template.get("phases", [])]
            assert phase_ids == REQUIRED_PHASE_IDS, f"template {meta['id']}: {phase_ids}"
            missing = REQUIRED_WIZARD_KEYS - _subsection_keys(template)
            assert not missing, f"template {meta['id']} missing wizards: {missing}"

    def test_write_phase_ref_resolves(self):
        """$ref to shared/write_phase.json resolves for all templates."""
        for meta in list_templates():
            template = get_template(meta["id"])
            write = next(p for p in template["phases"] if p["id"] == "write")
            assert "$ref" not in write
            assert "script_writer_wizard" in {s["key"] for s in write["subsections"]}

    def test_characters_subsection_exists(self):
        """wizards._get_character_data queries phase=story, subsection=characters."""
        for meta in list_templates():
            template = get_template(meta["id"])
            story = next(p for p in template["phases"] if p["id"] == "story")
            assert "characters" in {s["key"] for s in story["subsections"]}


class TestDoctrineFormatRouting:
    def test_format_read_from_template_json(self):
        assert doctrine_service.format_tag_for_template("short_movie") == "short_film"
        assert doctrine_service.format_tag_for_template("sketch") == "sketch"
        assert doctrine_service.format_tag_for_template("episode") == "series"

    def test_unknown_template_still_none(self):
        assert doctrine_service.format_tag_for_template("unknown") is None


class TestComposerTargets:
    def test_targets_are_union_deduped(self):
        targets = pipeline_composer._get_wizard_targets()
        keys = [(t["phase"], t["subsection_key"]) for t in targets]
        assert len(keys) == len(set(keys)), "duplicate composer targets"
        # All templates share the same three wizards today, so the union
        # collapses to exactly these steps.
        assert set(keys) == {
            ("idea", "idea_wizard"),
            ("scenes", "scene_wizard"),
            ("write", "script_writer_wizard"),
        }
