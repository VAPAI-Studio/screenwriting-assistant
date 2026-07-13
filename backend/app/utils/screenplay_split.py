"""Split raw screenplay text into scenes by INT./EXT. sluglines.

Server-side equivalent of the frontend's splitByHeadings (Phase 54, D-54-03).
Shared by the MCP screenplay_write tool and the REST screenplay file import —
both must produce identical scene lists for the same text.
"""

import re

# Matches an INT./EXT. scene heading (slugline) at the start of a line.
_HEADING_RE = re.compile(r"^\s*(INT\.|EXT\.|INT/EXT\.|I/E\.)", re.IGNORECASE)


def split_by_headings(text: str) -> list:
    """Split a hand-written screenplay into scenes by INT./EXT. sluglines.

    Each slugline starts a new scene; no-heading text becomes a single
    "Untitled" scene so nothing is lost. Returns [{title, content,
    episode_index}]. Title is the slugline; content is the body after it.
    """
    text = text or ""
    if not text.strip():
        return []

    scenes = []
    cur_title = None
    cur_body: list = []

    def _flush():
        if cur_title is None and not any(l.strip() for l in cur_body):
            return
        title = cur_title if cur_title is not None else "Untitled"
        scenes.append({"title": title, "content": "\n".join(cur_body).strip("\n")})

    for line in text.splitlines():
        if _HEADING_RE.match(line):
            _flush()
            cur_title = line.strip()
            cur_body = []
        else:
            cur_body.append(line)
    _flush()

    for i, s in enumerate(scenes):
        s["episode_index"] = i
    return scenes
