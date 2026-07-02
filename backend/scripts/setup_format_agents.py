"""Create/refresh the per-format TAG_BASED agents (Phase 1 close-out).

Idempotent: skips agents whose name already exists. TAG_BASED agents filter
concepts by tag across ALL the owner's books, so new books join a format's
doctrine automatically — no manual book linking ever again.

Also links the Save the Cat books to the existing Snyder agent (BOOK_BASED)
and deletes the empty McKee placeholder agent.

Run from backend/ with the API up:
    API_URL=http://localhost:8001 ./venv/bin/python scripts/setup_format_agents.py
"""

import os

import requests

API_URL = os.environ.get("API_URL", "http://localhost:8001")
HEADERS = {"Authorization": f"Bearer {os.environ.get('API_TOKEN', 'mock-token')}"}

FORMAT_AGENTS = [
    {
        "name": "Doctor de cortos",
        "description": "Especialista en cortometrajes — estructura comprimida, economía narrativa.",
        "agent_type": "tag_based",
        "tags_filter": ["short_film"],
        "system_prompt_template": (
            "You are a short-film story consultant. Ground every note in the craft "
            "concepts provided from the user's short-film canon (Cowgill, Cooper & "
            "Dancyger). Short films live or die on economy: one idea, compressed "
            "structure, a single decisive turn. Cite the concept you are applying.\n\n"
            "{context}"
        ),
    },
    {
        "name": "Doctor de sketch",
        "description": "Especialista en sketch — premisa, game of the scene, escalación, blow.",
        "agent_type": "tag_based",
        "tags_filter": ["sketch", "comedy"],
        "system_prompt_template": (
            "You are a sketch-comedy consultant trained on the UCB manual and Joe "
            "Toplyn's methods. Analyze every sketch through: the PREMISE (the one "
            "unusual thing), the GAME (the repeatable comedic pattern), ESCALATION "
            "(heightening beat by beat), and the BLOW (getting out at the peak). "
            "Cite the concept you are applying.\n\n"
            "{context}"
        ),
    },
    {
        "name": "Doctor de series",
        "description": "Especialista en series — story engine, arco de temporada, episodios.",
        "agent_type": "tag_based",
        "tags_filter": ["series"],
        "system_prompt_template": (
            "You are a TV-series development consultant grounded in Yorke, Rabkin, "
            "Pamela Douglas and Save the Cat Writes for TV. Evaluate pilots and "
            "episodes for: a repeatable story engine, series questions (ongoing "
            "process) vs movie questions (closed answers), franchise alignment of "
            "concept/conflict/theme, and each episode's place in the season arc. "
            "Cite the concept you are applying.\n\n"
            "{context}"
        ),
    },
]

# BOOK_BASED links: agent-name substring -> book-title substrings
BOOK_LINKS = {
    "Snyder": ["Save the Cat!", "Save the Cat! Writes for TV"],
}

DELETE_AGENTS = ["McKee (Story)"]  # cáscara vacía; McKee no entra al RAG


def main():
    agents = requests.get(f"{API_URL}/api/agents/", headers=HEADERS, timeout=30).json()
    books = requests.get(f"{API_URL}/api/books/", headers=HEADERS, timeout=30).json()
    by_name = {a["name"]: a for a in agents}

    for spec in FORMAT_AGENTS:
        if spec["name"] in by_name:
            print(f"— '{spec['name']}' ya existe, salteando")
            continue
        r = requests.post(f"{API_URL}/api/agents/", headers=HEADERS, json=spec, timeout=30)
        r.raise_for_status()
        print(f"✔ creado: {spec['name']} (tags={spec['tags_filter']})")

    for agent_key, title_keys in BOOK_LINKS.items():
        agent = next((a for a in agents if agent_key in a["name"]), None)
        if not agent:
            print(f"⚠ agente '{agent_key}' no encontrado, salteo vínculos")
            continue
        for tk in title_keys:
            book = next((b for b in books if b["title"] == tk), None)
            if not book:
                print(f"⚠ libro '{tk}' no encontrado")
                continue
            r = requests.post(
                f"{API_URL}/api/agents/{agent['id']}/books/{book['id']}",
                headers=HEADERS, timeout=30,
            )
            print(f"{'✔' if r.ok else '⚠'} {agent['name']} ← {tk} ({r.status_code})")

    for name in DELETE_AGENTS:
        agent = by_name.get(name)
        if agent:
            r = requests.delete(f"{API_URL}/api/agents/{agent['id']}", headers=HEADERS, timeout=30)
            print(f"{'✔' if r.ok else '⚠'} borrado: {name} ({r.status_code})")

    print("\nAgentes finales:")
    for a in requests.get(f"{API_URL}/api/agents/", headers=HEADERS, timeout=30).json():
        print(f"  [{a['agent_type']}] {a['name']}  tags={a.get('tags_filter')} books={a.get('book_count')}")


if __name__ == "__main__":
    main()
