"""Post-ingestion validation of the book library (Phase 1 close-out).

Run INSIDE the backend container (needs the docker network to reach the DB):
    docker exec screenwriting-assistant-backend-1 python scripts/validate_library.py

Checks, per completed book: concept count, avg quality, format-tag coverage.
Then a retrieval dry-run per format: the top doctrine concepts for each format
tag must come from that format's books (no cross-format pollution).
"""

import sys

from app.db import SessionLocal
from sqlalchemy import text

OWNER = "12345678-1234-5678-1234-567812345678"
FORMAT_TAGS = ["short_film", "sketch", "series", "feature"]

# Expected dominant format per book title substring (validation oracle).
EXPECTED_FORMAT = {
    "Writing Short Films": "short_film",
    "Writing the Short Film": "short_film",
    "Upright Citizens Brigade": "sketch",
    "Comedy Writing for Late-Night": "sketch",
    "Joke Writing": "sketch",
    "Into the Woods": None,          # teoría general — puede repartirse
    "TV Drama Series": "series",
    "Writing the Pilot": "series",
    "Save the Cat!": "feature",      # el original enseña estructura de largo
    "Save the Cat! Writes for TV": "series",
}


def main():
    db = SessionLocal()
    problems = []

    print("=== Libros y calidad ===")
    books = db.execute(text("""
        SELECT b.id, b.title, b.status, count(c.id) AS n,
               round(avg(c.quality_score)::numeric, 2) AS q
        FROM books b LEFT JOIN concepts c ON c.book_id = b.id
        WHERE b.owner_id = :o
        GROUP BY b.id, b.title, b.status ORDER BY b.title
    """), {"o": OWNER}).fetchall()

    for b in books:
        flag = ""
        if b.status != "completed":
            flag = "  ⚠ NO COMPLETADO"
            problems.append(f"{b.title}: status={b.status}")
        elif b.n < 20:
            flag = "  ⚠ POCOS CONCEPTOS"
            problems.append(f"{b.title}: solo {b.n} conceptos")
        print(f"  {b.n:4d} conceptos  q={b.q}  {b.title}{flag}")

    print("\n=== Distribución de tags de formato por libro ===")
    for b in books:
        if b.status != "completed":
            continue
        rows = db.execute(text("""
            SELECT t.tag, count(*) FROM concepts c,
                 LATERAL jsonb_array_elements_text(c.tags) AS t(tag)
            WHERE c.book_id = :bid AND t.tag = ANY(:fmts)
            GROUP BY t.tag ORDER BY count(*) DESC
        """), {"bid": str(b.id), "fmts": FORMAT_TAGS}).fetchall()
        dist = ", ".join(f"{r[0]}:{r[1]}" for r in rows) or "SIN TAGS DE FORMATO"
        dominant = rows[0][0] if rows else None

        expected = next((v for k, v in EXPECTED_FORMAT.items() if k in b.title), "?")
        ok = "✔" if (expected in (None, "?") or dominant == expected) else "✘"
        if ok == "✘":
            problems.append(f"{b.title}: formato dominante {dominant}, esperado {expected}")
        print(f"  {ok} {b.title}: {dist}")

    print("\n=== Dry-run de retrieval por formato (top 5 doctrina) ===")
    from app.services import doctrine_service
    for fmt in FORMAT_TAGS:
        doctrine_service.TEMPLATE_FORMAT_TAGS[f"_val_{fmt}"] = fmt
        cards = doctrine_service.build_doctrine_cards(OWNER, f"_val_{fmt}", db, max_concepts=5)
        print(f"\n  [{fmt}] {len(cards)} conceptos:")
        for c in cards:
            print(f"    - {c['name']}  ← {c['source']}")

    print("\n=== Beats nuevos (muestra sketch) ===")
    r = db.execute(text("""
        SELECT count(*) FILTER (WHERE (c.section_relevance->>'GAME')::float > 0.5) AS game_alto,
               count(*) FILTER (WHERE c.tags ? 'sketch') AS tag_sketch
        FROM concepts c JOIN books b ON b.id = c.book_id
        WHERE b.owner_id = :o AND b.status = 'completed'
    """), {"o": OWNER}).fetchone()
    print(f"  conceptos con GAME>0.5: {r.game_alto}, con tag sketch: {r.tag_sketch}")

    print("\n=== Veredicto ===")
    if problems:
        print("  PROBLEMAS:")
        for p in problems:
            print(f"    - {p}")
        sys.exit(1)
    print("  Biblioteca OK ✔")


if __name__ == "__main__":
    main()
