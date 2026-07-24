# backend/app/tests/test_seasons_api.py

"""Phase 4 (capa de temporada): seasons, episode slots, episodes-from-slots,
season map wizard apply, slot-plan bible injection, and plan_stale hooks.

AI calls are ALWAYS mocked (AsyncMock) — deterministic and offline.
"""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from app.models.database import (
    EpisodeSlot as EpisodeSlotModel,
    PhaseData as PhaseDataModel,
    Project as ProjectModel,
    Season as SeasonModel,
    WizardRun as WizardRunModel,
)
from app.services.template_ai_service import template_ai_service
from app.utils.bible_context import build_bible_context
from app.utils.episode_summary import mark_linked_slot_plan_stale


def _create_show(client, headers, title="Season Test Show", continuity="connected"):
    resp = client.post(
        "/api/shows/",
        json={"title": title, "continuity_mode": continuity},
        headers=headers,
    )
    assert resp.status_code == 201
    return resp.json()["id"]


def _create_season(client, headers, show_id, **body):
    resp = client.post(f"/api/shows/{show_id}/seasons", json=body, headers=headers)
    assert resp.status_code == 201
    return resp.json()


def _create_slot(client, headers, season_id, **body):
    resp = client.post(f"/api/seasons/{season_id}/slots", json=body, headers=headers)
    assert resp.status_code == 201
    return resp.json()


class TestSeasonsCRUD:
    def test_create_season_auto_number(self, client, mock_auth_headers):
        show_id = _create_show(client, mock_auth_headers)
        s1 = _create_season(client, mock_auth_headers, show_id)
        s2 = _create_season(client, mock_auth_headers, show_id)
        assert s1["number"] == 1
        assert s2["number"] == 2
        assert s1["title"] == "Season 1"
        assert s1["status"] == "planning"

    def test_create_season_number_conflict(self, client, mock_auth_headers):
        show_id = _create_show(client, mock_auth_headers)
        _create_season(client, mock_auth_headers, show_id, number=1)
        resp = client.post(
            f"/api/shows/{show_id}/seasons", json={"number": 1}, headers=mock_auth_headers
        )
        assert resp.status_code == 409

    def test_list_seasons_ordered(self, client, mock_auth_headers):
        show_id = _create_show(client, mock_auth_headers)
        _create_season(client, mock_auth_headers, show_id, number=2)
        _create_season(client, mock_auth_headers, show_id, number=1)
        resp = client.get(f"/api/shows/{show_id}/seasons", headers=mock_auth_headers)
        assert resp.status_code == 200
        assert [s["number"] for s in resp.json()] == [1, 2]

    def test_get_season_detail_with_slots(self, client, mock_auth_headers):
        show_id = _create_show(client, mock_auth_headers)
        season = _create_season(client, mock_auth_headers, show_id)
        _create_slot(client, mock_auth_headers, season["id"], slot_number=2, title="Two")
        _create_slot(client, mock_auth_headers, season["id"], slot_number=1, title="One")
        resp = client.get(f"/api/seasons/{season['id']}", headers=mock_auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert [s["slot_number"] for s in data["slots"]] == [1, 2]
        assert data["slots"][0]["title"] == "One"

    def test_update_season(self, client, mock_auth_headers):
        show_id = _create_show(client, mock_auth_headers)
        season = _create_season(client, mock_auth_headers, show_id)
        resp = client.put(
            f"/api/seasons/{season['id']}",
            json={"arc_summary": "The fall of the crew.", "status": "active"},
            headers=mock_auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["arc_summary"] == "The fall of the crew."
        assert resp.json()["status"] == "active"

    def test_delete_season_unlinks_episode(self, client, mock_auth_headers, db_session):
        show_id = _create_show(client, mock_auth_headers)
        season = _create_season(client, mock_auth_headers, show_id)
        slot = _create_slot(client, mock_auth_headers, season["id"])
        ep = client.post(
            f"/api/slots/{slot['id']}/create-episode",
            json={"title": "Survivor Episode", "template": "episode"},
            headers=mock_auth_headers,
        ).json()

        resp = client.delete(f"/api/seasons/{season['id']}", headers=mock_auth_headers)
        assert resp.status_code == 200

        project = db_session.query(ProjectModel).filter(ProjectModel.id == ep["id"]).first()
        assert project is not None  # the episode survives
        assert project.season_id is None
        assert (
            db_session.query(SeasonModel).filter(SeasonModel.id == season["id"]).first() is None
        )

    def test_season_not_found(self, client, mock_auth_headers):
        resp = client.get(
            "/api/seasons/00000000-0000-0000-0000-000000000000", headers=mock_auth_headers
        )
        assert resp.status_code == 404


class TestSlotsCRUD:
    def test_create_slot_auto_number(self, client, mock_auth_headers):
        show_id = _create_show(client, mock_auth_headers)
        season = _create_season(client, mock_auth_headers, show_id)
        s1 = _create_slot(client, mock_auth_headers, season["id"])
        s2 = _create_slot(client, mock_auth_headers, season["id"])
        assert s1["slot_number"] == 1
        assert s2["slot_number"] == 2
        assert s1["plan_stale"] is False
        assert s1["project_id"] is None

    def test_create_slot_number_conflict(self, client, mock_auth_headers):
        show_id = _create_show(client, mock_auth_headers)
        season = _create_season(client, mock_auth_headers, show_id)
        _create_slot(client, mock_auth_headers, season["id"], slot_number=1)
        resp = client.post(
            f"/api/seasons/{season['id']}/slots",
            json={"slot_number": 1},
            headers=mock_auth_headers,
        )
        assert resp.status_code == 409

    def test_update_slot_plan_fields(self, client, mock_auth_headers):
        show_id = _create_show(client, mock_auth_headers)
        season = _create_season(client, mock_auth_headers, show_id)
        slot = _create_slot(client, mock_auth_headers, season["id"])
        resp = client.put(
            f"/api/slots/{slot['id']}",
            json={
                "title": "The Heist",
                "logline": "The crew robs the vault.",
                "arc_function": "midpoint reversal",
                "character_states": {"Mara": "suspects Leo"},
                "cliffhanger": "The vault is empty.",
            },
            headers=mock_auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["title"] == "The Heist"
        assert data["character_states"] == {"Mara": "suspects Leo"}
        assert data["cliffhanger"] == "The vault is empty."

    def test_update_slot_clears_plan_stale(self, client, mock_auth_headers, db_session):
        show_id = _create_show(client, mock_auth_headers)
        season = _create_season(client, mock_auth_headers, show_id)
        slot = _create_slot(client, mock_auth_headers, season["id"])
        db_slot = db_session.query(EpisodeSlotModel).filter(
            EpisodeSlotModel.id == slot["id"]
        ).first()
        db_slot.plan_stale = True
        db_session.commit()

        resp = client.put(
            f"/api/slots/{slot['id']}", json={"plan_stale": False}, headers=mock_auth_headers
        )
        assert resp.status_code == 200
        assert resp.json()["plan_stale"] is False

    def test_delete_slot(self, client, mock_auth_headers):
        show_id = _create_show(client, mock_auth_headers)
        season = _create_season(client, mock_auth_headers, show_id)
        slot = _create_slot(client, mock_auth_headers, season["id"])
        resp = client.delete(f"/api/slots/{slot['id']}", headers=mock_auth_headers)
        assert resp.status_code == 200
        detail = client.get(f"/api/seasons/{season['id']}", headers=mock_auth_headers).json()
        assert detail["slots"] == []


class TestEpisodeFromSlot:
    def test_create_episode_links_and_scaffolds(self, client, mock_auth_headers, db_session):
        show_id = _create_show(client, mock_auth_headers)
        season = _create_season(client, mock_auth_headers, show_id)
        slot = _create_slot(client, mock_auth_headers, season["id"], title="Pilot Plan")

        resp = client.post(
            f"/api/slots/{slot['id']}/create-episode",
            json={"template": "episode"},
            headers=mock_auth_headers,
        )
        assert resp.status_code == 201
        ep = resp.json()
        assert ep["title"] == "Pilot Plan"  # falls back to the slot's working title
        assert ep["show_id"] == show_id
        assert ep["episode_number"] == 1

        db_slot = db_session.query(EpisodeSlotModel).filter(
            EpisodeSlotModel.id == slot["id"]
        ).first()
        assert str(db_slot.project_id) == ep["id"]

        project = db_session.query(ProjectModel).filter(ProjectModel.id == ep["id"]).first()
        assert str(project.season_id) == season["id"]

        # phase_data scaffolded like create_episode / create_project_v2
        pd_count = db_session.query(PhaseDataModel).filter(
            PhaseDataModel.project_id == ep["id"]
        ).count()
        assert pd_count > 0

    def test_create_episode_twice_fails(self, client, mock_auth_headers):
        show_id = _create_show(client, mock_auth_headers)
        season = _create_season(client, mock_auth_headers, show_id)
        slot = _create_slot(client, mock_auth_headers, season["id"])
        first = client.post(
            f"/api/slots/{slot['id']}/create-episode", json={}, headers=mock_auth_headers
        )
        assert first.status_code == 201
        second = client.post(
            f"/api/slots/{slot['id']}/create-episode", json={}, headers=mock_auth_headers
        )
        assert second.status_code == 400

    def test_episode_number_offsets_prior_seasons(self, client, mock_auth_headers):
        """Global narrative numbering: S2 slot 2 -> episode_number = |S1 slots| + 2."""
        show_id = _create_show(client, mock_auth_headers)
        s1 = _create_season(client, mock_auth_headers, show_id, number=1)
        for _ in range(3):
            _create_slot(client, mock_auth_headers, s1["id"])
        s2 = _create_season(client, mock_auth_headers, show_id, number=2)
        _create_slot(client, mock_auth_headers, s2["id"], slot_number=1)
        slot = _create_slot(client, mock_auth_headers, s2["id"], slot_number=2)

        resp = client.post(
            f"/api/slots/{slot['id']}/create-episode", json={}, headers=mock_auth_headers
        )
        assert resp.status_code == 201
        assert resp.json()["episode_number"] == 5  # 3 (S1) + 2

    def test_out_of_order_creation_keeps_narrative_order(self, client, mock_auth_headers):
        show_id = _create_show(client, mock_auth_headers)
        season = _create_season(client, mock_auth_headers, show_id)
        slot1 = _create_slot(client, mock_auth_headers, season["id"], slot_number=1)
        slot5 = _create_slot(client, mock_auth_headers, season["id"], slot_number=5)

        ep5 = client.post(
            f"/api/slots/{slot5['id']}/create-episode", json={}, headers=mock_auth_headers
        ).json()
        ep1 = client.post(
            f"/api/slots/{slot1['id']}/create-episode", json={}, headers=mock_auth_headers
        ).json()
        assert ep5["episode_number"] == 5
        assert ep1["episode_number"] == 1


class TestSeasonMapWizard:
    def test_run_requires_exactly_one_scope(self, client, mock_auth_headers):
        resp = client.post(
            "/api/wizards/run",
            json={"wizard_type": "season_map_wizard", "phase": "story", "config": {}},
            headers=mock_auth_headers,
        )
        assert resp.status_code == 422

    def test_season_run_rejects_other_wizard_types(self, client, mock_auth_headers):
        show_id = _create_show(client, mock_auth_headers)
        season = _create_season(client, mock_auth_headers, show_id)
        resp = client.post(
            "/api/wizards/run",
            json={
                "season_id": season["id"],
                "wizard_type": "scene_wizard",
                "phase": "story",
                "config": {},
            },
            headers=mock_auth_headers,
        )
        assert resp.status_code == 400

    def test_project_run_rejects_season_map_wizard(self, client, mock_auth_headers):
        show_id = _create_show(client, mock_auth_headers)
        season = _create_season(client, mock_auth_headers, show_id)
        slot = _create_slot(client, mock_auth_headers, season["id"])
        ep = client.post(
            f"/api/slots/{slot['id']}/create-episode", json={}, headers=mock_auth_headers
        ).json()
        resp = client.post(
            "/api/wizards/run",
            json={
                "project_id": ep["id"],
                "wizard_type": "season_map_wizard",
                "phase": "story",
                "config": {},
            },
            headers=mock_auth_headers,
        )
        assert resp.status_code == 400

    def test_season_run_creates_season_scoped_run(self, client, mock_auth_headers):
        """POST /wizards/run with season_id creates the run; the background task
        itself is patched out (it opens its own DB session — exercised via the
        service test below and apply tests instead)."""
        show_id = _create_show(client, mock_auth_headers)
        season = _create_season(client, mock_auth_headers, show_id)
        with patch(
            "app.api.endpoints.wizards._run_season_map_background", new=AsyncMock()
        ) as mock_bg:
            resp = client.post(
                "/api/wizards/run",
                json={
                    "season_id": season["id"],
                    "wizard_type": "season_map_wizard",
                    "phase": "story",
                    "config": {"episode_count": 4, "premise": "A heist gone long."},
                },
                headers=mock_auth_headers,
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["season_id"] == season["id"]
        assert data["project_id"] is None
        assert data["wizard_type"] == "season_map_wizard"
        assert mock_bg.called
        # Poll endpoint resolves ownership through Season -> Show
        poll = client.get(f"/api/wizards/{data['id']}", headers=mock_auth_headers)
        assert poll.status_code == 200

    def _completed_run(self, db_session, season_id, result):
        run = WizardRunModel(
            season_id=season_id,
            wizard_type="season_map_wizard",
            phase="story",
            config={},
            result=result,
            status="completed",
        )
        db_session.add(run)
        db_session.commit()
        db_session.refresh(run)
        return run

    def test_apply_writes_arc_and_slots(self, client, mock_auth_headers, db_session):
        show_id = _create_show(client, mock_auth_headers)
        season = _create_season(client, mock_auth_headers, show_id)
        run = self._completed_run(db_session, season["id"], {
            "arc_summary": "Rise and fall.",
            "slots": [
                {"slot_number": 1, "title": "Pilot", "logline": "It begins.",
                 "arc_function": "setup", "character_states": {"Mara": "hopeful"},
                 "cliffhanger": "A knock at the door."},
                {"slot_number": 2, "title": "Fallout", "logline": "It breaks.",
                 "arc_function": "escalation", "character_states": {}, "cliffhanger": ""},
            ],
        })
        resp = client.post(f"/api/wizards/{run.id}/apply", headers=mock_auth_headers)
        assert resp.status_code == 200
        assert resp.json()["slots_written"] == 2

        detail = client.get(f"/api/seasons/{season['id']}", headers=mock_auth_headers).json()
        assert detail["arc_summary"] == "Rise and fall."
        assert [s["slot_number"] for s in detail["slots"]] == [1, 2]
        assert detail["slots"][0]["character_states"] == {"Mara": "hopeful"}

    def test_apply_never_touches_linked_slots(self, client, mock_auth_headers, db_session):
        """HARD RULE: linked slots survive re-apply untouched; free slots are
        replaced wholesale (absent numbers deleted)."""
        show_id = _create_show(client, mock_auth_headers)
        season = _create_season(client, mock_auth_headers, show_id)
        linked = _create_slot(
            client, mock_auth_headers, season["id"], slot_number=1,
            title="Locked Pilot", logline="Canon.",
        )
        client.post(
            f"/api/slots/{linked['id']}/create-episode", json={}, headers=mock_auth_headers
        )
        _create_slot(client, mock_auth_headers, season["id"], slot_number=2, title="Old Free")
        _create_slot(client, mock_auth_headers, season["id"], slot_number=3, title="Doomed")

        run = self._completed_run(db_session, season["id"], {
            "arc_summary": "",
            "slots": [
                # slot 1 is linked: the entry must be ignored
                {"slot_number": 1, "title": "HIJACKED", "logline": "x",
                 "arc_function": "", "character_states": {}, "cliffhanger": ""},
                {"slot_number": 2, "title": "New Free", "logline": "fresh",
                 "arc_function": "payoff", "character_states": {}, "cliffhanger": ""},
                # no slot 3 entry -> the free slot 3 gets deleted
            ],
        })
        resp = client.post(f"/api/wizards/{run.id}/apply", headers=mock_auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["slots_written"] == 1
        assert body["slots_locked"] == 1
        assert body["slots_deleted"] == 1

        detail = client.get(f"/api/seasons/{season['id']}", headers=mock_auth_headers).json()
        by_number = {s["slot_number"]: s for s in detail["slots"]}
        assert set(by_number) == {1, 2}
        assert by_number[1]["title"] == "Locked Pilot"  # untouched
        assert by_number[2]["title"] == "New Free"      # replaced

    def test_generate_season_map_service(self, db_session):
        """generate_season_map: json_mode call, locked numbers excluded, slots
        sorted and coerced."""
        raw = {
            "arc_summary": "The long con.",
            "slots": [
                {"slot_number": "3", "title": "C", "logline": "c", "arc_function": "",
                 "character_states": {"Leo": "burned"}, "cliffhanger": ""},
                {"slot_number": 2, "title": "LOCKED-DUPE", "logline": "x",
                 "arc_function": "", "character_states": {}, "cliffhanger": ""},
                {"slot_number": 1, "title": "A", "logline": "a", "arc_function": "setup",
                 "character_states": "not-a-dict", "cliffhanger": "boom"},
                {"slot_number": None, "title": "bad", "logline": "", "arc_function": "",
                 "character_states": {}, "cliffhanger": ""},
            ],
        }
        import json as _json
        mock = AsyncMock(return_value=_json.dumps(raw))
        with patch("app.services.template_ai_service.chat_completion", mock):
            result = asyncio.run(template_ai_service.generate_season_map(
                {"episode_count": 3, "_locked_slots": [{"slot_number": 2, "title": "Locked"}]},
                "Show: Test",
            ))
        assert result["arc_summary"] == "The long con."
        assert [s["slot_number"] for s in result["slots"]] == [1, 3]
        assert result["slots"][0]["character_states"] == {}  # coerced
        assert result["slots"][1]["character_states"] == {"Leo": "burned"}
        assert mock.call_args.kwargs["json_mode"] is True


class TestSlotPlanInjection:
    def _linked_setup(self, client, headers, db_session, **slot_fields):
        show_id = _create_show(client, headers)
        season = _create_season(client, headers, show_id)
        slot = _create_slot(client, headers, season["id"], **slot_fields)
        ep = client.post(
            f"/api/slots/{slot['id']}/create-episode", json={}, headers=headers
        ).json()
        project = db_session.query(ProjectModel).filter(ProjectModel.id == ep["id"]).first()
        return show_id, season, slot, project

    def test_slot_plan_injected_into_bible_context(self, client, mock_auth_headers, db_session):
        _, _, _, project = self._linked_setup(
            client, mock_auth_headers, db_session,
            logline="The crew robs the vault.",
            arc_function="midpoint reversal",
            character_states={"Mara": "suspects Leo"},
            cliffhanger="The vault is empty.",
        )
        ctx = build_bible_context(db_session, project)
        assert ctx is not None
        assert "This Episode in the Season Map (slot 1)" in ctx
        assert "The crew robs the vault." in ctx
        assert "midpoint reversal" in ctx
        assert "Mara: suspects Leo" in ctx
        assert "The vault is empty." in ctx

    def test_empty_plan_emits_no_slot_block(self, client, mock_auth_headers, db_session):
        _, _, _, project = self._linked_setup(client, mock_auth_headers, db_session)
        ctx = build_bible_context(db_session, project)
        # Empty bible + empty plan -> no context at all
        assert ctx is None or "Season Map" not in ctx

    def test_season_arc_supersedes_bible_arc(self, client, mock_auth_headers, db_session):
        show_id, season, _, project = self._linked_setup(client, mock_auth_headers, db_session)
        client.put(
            f"/api/shows/{show_id}/bible",
            json={"bible_season_arc": "OLD SHOW-LEVEL ARC"},
            headers=mock_auth_headers,
        )
        client.put(
            f"/api/seasons/{season['id']}",
            json={"arc_summary": "NEW SEASON ARC"},
            headers=mock_auth_headers,
        )
        ctx = build_bible_context(db_session, project)
        assert "NEW SEASON ARC" in ctx
        assert "OLD SHOW-LEVEL ARC" not in ctx

    def test_bible_arc_used_when_season_arc_empty(self, client, mock_auth_headers, db_session):
        show_id, _, _, project = self._linked_setup(client, mock_auth_headers, db_session)
        client.put(
            f"/api/shows/{show_id}/bible",
            json={"bible_season_arc": "SHOW-LEVEL ARC"},
            headers=mock_auth_headers,
        )
        ctx = build_bible_context(db_session, project)
        assert "SHOW-LEVEL ARC" in ctx


class TestPlanStale:
    def test_mark_helper_flags_linked_slot(self, client, mock_auth_headers, db_session):
        show_id = _create_show(client, mock_auth_headers)
        season = _create_season(client, mock_auth_headers, show_id)
        slot = _create_slot(client, mock_auth_headers, season["id"])
        ep = client.post(
            f"/api/slots/{slot['id']}/create-episode", json={}, headers=mock_auth_headers
        ).json()

        mark_linked_slot_plan_stale(db_session, ep["id"])
        db_session.commit()
        db_slot = db_session.query(EpisodeSlotModel).filter(
            EpisodeSlotModel.id == slot["id"]
        ).first()
        assert db_slot.plan_stale is True

    def test_mark_helper_noop_for_unslotted_project(self, client, mock_auth_headers, db_session):
        show_id = _create_show(client, mock_auth_headers)
        ep = client.post(
            f"/api/shows/{show_id}/episodes",
            json={"title": "Legacy Episode", "template": "episode"},
            headers=mock_auth_headers,
        ).json()
        # Must not raise
        mark_linked_slot_plan_stale(db_session, ep["id"])
        db_session.commit()

    def test_summary_endpoint_marks_slot_stale(self, client, mock_auth_headers, db_session):
        show_id = _create_show(client, mock_auth_headers)
        season = _create_season(client, mock_auth_headers, show_id)
        slot = _create_slot(client, mock_auth_headers, season["id"])
        ep = client.post(
            f"/api/slots/{slot['id']}/create-episode", json={}, headers=mock_auth_headers
        ).json()

        with patch.object(
            template_ai_service, "summarize_episode", new=AsyncMock(return_value="What happened.")
        ):
            resp = client.post(
                f"/api/projects/{ep['id']}/episode-summary", headers=mock_auth_headers
            )
        assert resp.status_code == 200
        db_slot = db_session.query(EpisodeSlotModel).filter(
            EpisodeSlotModel.id == slot["id"]
        ).first()
        assert db_slot.plan_stale is True


class TestReconcile:
    def test_reconcile_requires_linked_episode(self, client, mock_auth_headers):
        show_id = _create_show(client, mock_auth_headers)
        season = _create_season(client, mock_auth_headers, show_id)
        slot = _create_slot(client, mock_auth_headers, season["id"])
        resp = client.post(f"/api/slots/{slot['id']}/reconcile", headers=mock_auth_headers)
        assert resp.status_code == 400

    def test_reconcile_requires_summary(self, client, mock_auth_headers):
        show_id = _create_show(client, mock_auth_headers)
        season = _create_season(client, mock_auth_headers, show_id)
        slot = _create_slot(client, mock_auth_headers, season["id"])
        client.post(f"/api/slots/{slot['id']}/create-episode", json={}, headers=mock_auth_headers)
        resp = client.post(f"/api/slots/{slot['id']}/reconcile", headers=mock_auth_headers)
        assert resp.status_code == 400
        assert "summary" in resp.json()["detail"].lower()

    def test_reconcile_returns_proposal(self, client, mock_auth_headers, db_session):
        show_id = _create_show(client, mock_auth_headers)
        season = _create_season(client, mock_auth_headers, show_id)
        slot = _create_slot(
            client, mock_auth_headers, season["id"],
            logline="Planned logline", cliffhanger="Planned out",
        )
        ep = client.post(
            f"/api/slots/{slot['id']}/create-episode", json={}, headers=mock_auth_headers
        ).json()
        project = db_session.query(ProjectModel).filter(ProjectModel.id == ep["id"]).first()
        project.episode_summary = "Mara stole the ledger and burned the safehouse."
        db_session.commit()

        proposal = {
            "title": "The Ledger",
            "logline": "Mara steals the ledger.",
            "arc_function": "point of no return",
            "character_states": {"Mara": "on the run"},
            "cliffhanger": "The safehouse burns.",
        }
        with patch.object(
            template_ai_service, "reconcile_slot_plan", new=AsyncMock(return_value=proposal)
        ) as mock_rec:
            resp = client.post(f"/api/slots/{slot['id']}/reconcile", headers=mock_auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["proposal"] == proposal
        assert "ledger" in data["episode_summary"].lower()
        # Preview only: the slot itself is untouched
        db_session.expire_all()
        db_slot = db_session.query(EpisodeSlotModel).filter(
            EpisodeSlotModel.id == slot["id"]
        ).first()
        assert db_slot.logline == "Planned logline"
        assert mock_rec.call_args.kwargs["episode_summary"] == project.episode_summary


class TestManualEpisodeAssignment:
    """PUT /slots/{id} with project_id — adopt an existing episode into the map."""

    def _episode(self, client, headers, show_id, title="Loose Episode"):
        resp = client.post(
            f"/api/shows/{show_id}/episodes",
            json={"title": title, "template": "episode"},
            headers=headers,
        )
        assert resp.status_code == 201
        return resp.json()

    def test_assign_and_unlink(self, client, mock_auth_headers, db_session):
        show_id = _create_show(client, mock_auth_headers)
        season = _create_season(client, mock_auth_headers, show_id)
        slot = _create_slot(client, mock_auth_headers, season["id"])
        ep = self._episode(client, mock_auth_headers, show_id)

        resp = client.put(
            f"/api/slots/{slot['id']}", json={"project_id": ep["id"]}, headers=mock_auth_headers
        )
        assert resp.status_code == 200
        assert resp.json()["project_id"] == ep["id"]
        # Linking also adopts the episode into the season (same as create-from-slot).
        proj = db_session.query(ProjectModel).filter(ProjectModel.id == ep["id"]).first()
        assert str(proj.season_id) == season["id"]

        # Explicit null unlinks.
        resp = client.put(
            f"/api/slots/{slot['id']}", json={"project_id": None}, headers=mock_auth_headers
        )
        assert resp.status_code == 200
        assert resp.json()["project_id"] is None

    def test_assign_rejects_other_shows_episode(self, client, mock_auth_headers):
        show_a = _create_show(client, mock_auth_headers, title="Show A")
        show_b = _create_show(client, mock_auth_headers, title="Show B")
        season = _create_season(client, mock_auth_headers, show_a)
        slot = _create_slot(client, mock_auth_headers, season["id"])
        ep_b = self._episode(client, mock_auth_headers, show_b)
        resp = client.put(
            f"/api/slots/{slot['id']}", json={"project_id": ep_b["id"]}, headers=mock_auth_headers
        )
        assert resp.status_code == 400

    def test_assign_rejects_already_slotted_episode(self, client, mock_auth_headers):
        show_id = _create_show(client, mock_auth_headers)
        season = _create_season(client, mock_auth_headers, show_id)
        slot1 = _create_slot(client, mock_auth_headers, season["id"])
        slot2 = _create_slot(client, mock_auth_headers, season["id"])
        ep = self._episode(client, mock_auth_headers, show_id)
        assert client.put(
            f"/api/slots/{slot1['id']}", json={"project_id": ep["id"]}, headers=mock_auth_headers
        ).status_code == 200
        resp = client.put(
            f"/api/slots/{slot2['id']}", json={"project_id": ep["id"]}, headers=mock_auth_headers
        )
        assert resp.status_code == 409
