"""Per-call DB session for MCP tool handlers.

MCP tool functions are not FastAPI route handlers, so they cannot use the
`Depends(get_db)` chain. mcp_session() is a plain context manager that opens a
session from the existing SessionLocal and closes it after the call. Open it
late and close it early inside each tool — never hold it across a long AI await
(that pattern is established in Phase 56).
"""

import contextlib

from ..db import SessionLocal


@contextlib.contextmanager
def mcp_session():
    """Yield a SQLAlchemy session for the duration of one MCP tool call."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
