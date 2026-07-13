"""Tests for the screenplay file import endpoint.

POST /api/phase-data/{project_id}/screenplay/import — upload a PDF/TXT
screenplay, split it into scenes by sluglines, and persist through the
canonical screenplay_editor PATCH path (PhaseData + ScreenplayContent
reconcile + staleness).
"""

import io
import uuid as _uuid

from app.models.database import PhaseData, Project, ScreenplayContent


def _make_pdf(lines) -> bytes:
    """Build a minimal valid one-page PDF with the given text lines (Courier).
    Keeps the pdf branch testable without a PDF-writing dependency."""
    content = b"BT /F1 12 Tf 50 750 Td 14 TL " + b" ".join(
        b"(" + l.encode() + b") Tj T*" for l in lines
    ) + b" ET"
    objs = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length " + str(len(content)).encode() + b" >>\nstream\n" + content + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Courier >>",
    ]
    out = io.BytesIO()
    out.write(b"%PDF-1.4\n")
    offsets = []
    for i, o in enumerate(objs, 1):
        offsets.append(out.tell())
        out.write(f"{i} 0 obj\n".encode() + o + b"\nendobj\n")
    xref = out.tell()
    out.write(f"xref\n0 {len(objs) + 1}\n0000000000 65535 f \n".encode())
    for off in offsets:
        out.write(f"{off:010d} 00000 n \n".encode())
    out.write(
        f"trailer\n<< /Size {len(objs) + 1} /Root 1 0 R >>\n"
        f"startxref\n{xref}\n%%EOF".encode()
    )
    return out.getvalue()

# Matches the user returned by mock-token auth in development.
MOCK_USER_ID = "12345678-1234-5678-1234-567812345678"

TWO_SCENE_TEXT = (
    "INT. CASTLE - NIGHT\n\n"
    "The KNIGHT draws a sword.\n\n"
    "EXT. FOREST - DAY\n\n"
    "The KNIGHT rides on.\n"
)


def _make_project(db_session, owner_id=MOCK_USER_ID):
    project_id = str(_uuid.uuid4())
    db_session.add(Project(id=project_id, owner_id=owner_id, title="Imported Film"))
    db_session.commit()
    return project_id


def _import_txt(client, project_id, headers, text=TWO_SCENE_TEXT, filename="script.txt"):
    return client.post(
        f"/api/phase-data/{project_id}/screenplay/import",
        files={"file": (filename, text.encode("utf-8"), "text/plain")},
        headers=headers,
    )


class TestScreenplayImport:
    def test_txt_import_splits_and_persists(self, client, db_session, mock_auth_headers):
        """A .txt upload is split by sluglines and lands in PhaseData +
        ScreenplayContent exactly like a manual editor save."""
        project_id = _make_project(db_session)

        response = _import_txt(client, project_id, mock_auth_headers)
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["scene_count"] == 2
        assert body["scenes"][0] == {"episode_index": 0, "title": "INT. CASTLE - NIGHT"}
        assert body["scenes"][1] == {"episode_index": 1, "title": "EXT. FOREST - DAY"}

        pd = (
            db_session.query(PhaseData)
            .filter(
                PhaseData.project_id == project_id,
                PhaseData.phase == "write",
                PhaseData.subsection_key == "screenplay_editor",
            )
            .first()
        )
        assert pd is not None
        assert len(pd.content["screenplays"]) == 2

        rows = (
            db_session.query(ScreenplayContent)
            .filter(ScreenplayContent.project_id == project_id)
            .all()
        )
        assert len(rows) == 2

    def test_pdf_import_extracts_and_splits(self, client, db_session, mock_auth_headers):
        """A real .pdf upload goes through PyPDF2 extraction and lands as scenes."""
        project_id = _make_project(db_session)
        pdf = _make_pdf([
            "INT. CASA - DIA", "",
            "MARIA enters with a letter.", "",
            "EXT. CALLE - NOCHE", "",
            "Rain falls.",
        ])
        response = client.post(
            f"/api/phase-data/{project_id}/screenplay/import",
            files={"file": ("guion.pdf", pdf, "application/pdf")},
            headers=mock_auth_headers,
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["scene_count"] == 2
        assert body["scenes"][0]["title"] == "INT. CASA - DIA"
        assert body["scenes"][1]["title"] == "EXT. CALLE - NOCHE"

    def test_import_marks_breakdown_and_shotlist_stale(
        self, client, db_session, mock_auth_headers
    ):
        """Staleness is existence-gated: with a prior breakdown element and shot
        present, an import flips both flags."""
        from app.models.database import BreakdownElement, Shot

        project_id = _make_project(db_session)
        db_session.add(BreakdownElement(
            project_id=project_id, name="KNIGHT", category="character",
        ))
        db_session.add(Shot(project_id=project_id, shot_number=1, fields={}))
        db_session.commit()

        response = _import_txt(client, project_id, mock_auth_headers)
        assert response.status_code == 200, response.text

        project = db_session.query(Project).filter(Project.id == project_id).first()
        db_session.refresh(project)
        assert project.breakdown_stale is True
        assert project.shotlist_stale is True

    def test_repeated_import_replaces_scenes(self, client, db_session, mock_auth_headers):
        """Idempotency: re-importing replaces the scene set, no accumulation."""
        project_id = _make_project(db_session)
        assert _import_txt(client, project_id, mock_auth_headers).status_code == 200

        response = _import_txt(
            client, project_id, mock_auth_headers, text="INT. CAVE - DAY\n\nAlone.\n"
        )
        assert response.status_code == 200
        assert response.json()["scene_count"] == 1

        rows = (
            db_session.query(ScreenplayContent)
            .filter(ScreenplayContent.project_id == project_id)
            .all()
        )
        assert len(rows) == 1

    def test_unsupported_extension_is_rejected(self, client, db_session, mock_auth_headers):
        project_id = _make_project(db_session)
        response = _import_txt(
            client, project_id, mock_auth_headers, filename="script.docx"
        )
        assert response.status_code == 400
        assert ".pdf or .txt" in response.json()["detail"]

    def test_empty_file_is_rejected(self, client, db_session, mock_auth_headers):
        project_id = _make_project(db_session)
        response = _import_txt(client, project_id, mock_auth_headers, text="   \n  ")
        assert response.status_code == 400

    def test_other_users_project_404s(self, client, db_session, mock_auth_headers):
        project_id = _make_project(db_session, owner_id=str(_uuid.uuid4()))
        response = _import_txt(client, project_id, mock_auth_headers)
        assert response.status_code == 404
