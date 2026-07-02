"""One-shot batch upload of craft books through the API.

Uploads each book in MANIFEST via POST /api/books/upload and waits for its
background processing (chunks -> embeddings -> knowledge graph) to finish
before uploading the next one, so we never hammer the LLM with several books
in parallel. Safe to re-run: titles already present on the server are skipped,
and a failed/paused book can be resumed from its chapter checkpoint with
POST /api/books/{id}/resume instead of re-uploading.

Usage:
    python backend/scripts/batch_upload_books.py           # upload + process all
    API_URL=http://localhost:8000 python backend/scripts/batch_upload_books.py

Requires the backend running with OPENAI_API_KEY (embeddings) and the
Anthropic key (extraction) configured.
"""

import os
import sys
import time

import requests

API_URL = os.environ.get("API_URL", "http://localhost:8000")
TOKEN = os.environ.get("API_TOKEN", "mock-token")
HEADERS = {"Authorization": f"Bearer {TOKEN}"}
POLL_SECONDS = 20

DESKTOP = os.path.expanduser("~/Desktop")

DOWNLOADS = os.path.expanduser("~/Downloads")

# (file_path, title, author) — title is the display/citation name, keep it clean.
MANIFEST = [
    # --- PILOTO: un solo libro con Sonnet 5 para medir costo/tiempo antes del batch completo.
    (f"{DOWNLOADS}/libros a procesar/William Rabkin - Writing the Pilot_ Creating the Series (2017, moon & sun & whiskey inc.) - libgen.li.epub",
     "Writing the Pilot: Creating the Series", "William Rabkin"),
    # --- Resto del batch (descomentar tras validar el piloto) ---
    # Cortos: reprocesar con la nueva indexación (beats de sketch/serie + tags de formato).
    # Antes de correr, borrar las versiones viejas ("Linda J. Cowgill — ..." y
    # "Pat Cooper & Ken Dancyger — ...") desde la UI o con DELETE /api/books/{id}.
    (f"{DOWNLOADS}/Writing Short Films_ Structure and Content for Screenwriters - PDF Room.pdf",
     "Writing Short Films", "Linda J. Cowgill"),
    (f"{DOWNLOADS}/Patricia Cooper, Ken Dancyger, - Writing the Short Film, Third Edition Writing & Journalism (2004) - libgen.li.pdf",
     "Writing the Short Film", "Patricia Cooper & Ken Dancyger"),
    # Sketch:
    (f"{DOWNLOADS}/libros a procesar/dokumen.pub_upright-citizens-brigade-comedy-improvisation-manual-9798373982573.pdf",
     "The Upright Citizens Brigade Comedy Improvisation Manual",
     "Matt Besser, Ian Roberts & Matt Walsh"),
    (f"{DOWNLOADS}/libros a procesar/Joe Toplyn - Comedy Writing for Late-Night TV_ How to Write Monologue Jokes, Desk Pieces, Sketches, Parodies, Audience Pieces, Remotes, and (2014, Twenty Lane Media, LLC) - libgen.li.pdf",
     "Comedy Writing for Late-Night TV", "Joe Toplyn"),
    (f"{DOWNLOADS}/libros a procesar/Sally Holloway - The Serious Guide to Joke Writing_ How To Say Something Funny About Anything (2010, Bookshaker) - libgen.li.epub",
     "The Serious Guide to Joke Writing", "Sally Holloway"),
    # Serie:
    (f"{DOWNLOADS}/libros a procesar/John Yorke - Into the Woods. A five-act journey into story (2014, The Overlook Press) - libgen.li.epub",
     "Into the Woods", "John Yorke"),
    (f"{DOWNLOADS}/libros a procesar/Douglas, Pamela - Writing the TV Drama Series 3rd edition_ How to Succeed as a Professional Writer in TV (2011, Michael Wiese Productions) - libgen.li.epub",
     "Writing the TV Drama Series", "Pamela Douglas"),
    # Save the Cat (recomendados: original + Writes for TV; Strikes Back y Goes to
    # the Movies son redundantes con el original; Horror solo si hacen género):
    (f"{DOWNLOADS}/libros save the cat/Snyder, Blake - Save the Cat! The Last Book on Screenwriting You'll Ever Need (2005, Michael Wiese Productions) - libgen.li.epub",
     "Save the Cat!", "Blake Snyder"),
    (f"{DOWNLOADS}/libros save the cat/Jamie Nash - Save the Cat!® Writes for TV_ The Last Book on Creating Binge-Worthy Content You'll Ever Need (2021, Save the Cat! Press) - libgen.li.epub",
     "Save the Cat! Writes for TV", "Jamie Nash"),
    # (f"{DOWNLOADS}/libros save the cat/Save the Cat!® Writes Horror_ The Ultimate Guide to Creating -- Nash, Jamie -- 2025 -- Save the Cat! Press -- 248732dc35cbb38528254c90455d1e11 -- Anna’s Archive.epub",
    #  "Save the Cat! Writes Horror", "Jamie Nash"),
    # Thesauri (segunda tanda, si el retrieval lo pide):
    # (f"{DESKTOP}/conflict thesaurus/Conflict Thesaurus Volume 1.epub",
    #  "The Conflict Thesaurus Vol. 1", "Angela Ackerman & Becca Puglisi"),
    # (f"{DESKTOP}/conflict thesaurus/Conflict Thesaurus Volume 2.epub",
    #  "The Conflict Thesaurus Vol. 2", "Angela Ackerman & Becca Puglisi"),
]


def existing_titles() -> dict:
    resp = requests.get(f"{API_URL}/api/books/", headers=HEADERS, timeout=30)
    resp.raise_for_status()
    return {b["title"]: b for b in resp.json()}


def upload(path: str, title: str, author: str) -> str:
    with open(path, "rb") as f:
        resp = requests.post(
            f"{API_URL}/api/books/upload",
            headers=HEADERS,
            files={"file": (os.path.basename(path), f)},
            data={"title": title, "author": author},
            timeout=120,
        )
    resp.raise_for_status()
    return resp.json()["id"]


def wait_for_completion(book_id: str, title: str) -> bool:
    """Poll until COMPLETED/FAILED/PAUSED. Returns True on success."""
    last_line = ""
    while True:
        resp = requests.get(f"{API_URL}/api/books/{book_id}", headers=HEADERS, timeout=30)
        resp.raise_for_status()
        b = resp.json()
        status = b["status"]
        line = (f"  [{status}] {b.get('progress', 0)}% — "
                f"cap {b.get('chapters_processed', 0)}/{b.get('chapters_total', 0)} — "
                f"{b.get('processing_step') or ''}")
        if line != last_line:
            print(line, flush=True)
            last_line = line
        if status == "completed":
            print(f"  ✔ {title}: {b.get('total_concepts')} conceptos, {b.get('total_chunks')} chunks")
            return True
        if status in ("failed", "paused"):
            print(f"  ✘ {title} quedó en '{status}': {b.get('processing_error')}")
            print(f"    Reanudar con: curl -X POST {API_URL}/api/books/{book_id}/resume -H 'Authorization: Bearer {TOKEN}'")
            return False
        time.sleep(POLL_SECONDS)


def main():
    done = existing_titles()
    failures = []
    for path, title, author in MANIFEST:
        if title in done:
            print(f"— '{title}' ya está en el servidor ({done[title]['status']}), salteando")
            continue
        if not os.path.exists(path):
            print(f"— archivo no encontrado, salteando: {path}")
            failures.append(title)
            continue
        print(f"\n▶ Subiendo '{title}' ({os.path.getsize(path) // 1024} KB)…")
        book_id = upload(path, title, author)
        if not wait_for_completion(book_id, title):
            failures.append(title)

    print("\n=== Resumen ===")
    for b in existing_titles().values():
        print(f"  {b['status']:>10}  {b['title']}  ({b.get('total_concepts') or 0} conceptos)")
    if failures:
        print(f"\nCon problemas: {', '.join(failures)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
