"""Per-call DB session for MCP tool handlers.

MCP tool functions are not FastAPI route handlers, so they cannot use the
`Depends(get_db)` chain. mcp_session() is a plain context manager that opens a
session from the existing SessionLocal and closes it after the call. Open it
late and close it early inside each tool — never hold it across a long AI await
(that pattern is established in Phase 56).
"""

import contextlib
from typing import Callable, Optional

from ..db import SessionLocal

# Tests can install a session factory here (mirroring the get_db dependency
# override) so MCP tools hit the test DB instead of the production SessionLocal.
# Production never sets it.
_session_factory_override: Optional[Callable] = None


def set_session_factory_override(factory: Optional[Callable]) -> None:
    """Point mcp_session() at a custom session factory (tests only)."""
    global _session_factory_override
    _session_factory_override = factory


@contextlib.contextmanager
def mcp_session():
    """Yield a SQLAlchemy session for the duration of one MCP tool call."""
    factory = _session_factory_override or SessionLocal
    session = factory()
    try:
        yield session
    finally:
        session.close()
