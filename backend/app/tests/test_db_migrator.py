"""Control-flow unit tests for the startup migration runner (DMIG-01).

The migrator issues Postgres-specific SQL (pg_advisory_lock, information_schema,
init_db.sql DDL) that cannot run on the SQLite test engine.  These tests drive
run_migrations() against a fully MOCKED SQLAlchemy engine/connection and assert
the control flow: which SQL statements are issued and in what order, that the
advisory lock is acquired and released (even on failure), that init_db.sql runs
only on a truly-fresh DB, and that failures propagate (fail hard).

We route each conn.execute() call by inspecting the rendered SQL text so the
scenario's branch (.scalar() / .fetchall() results) is keyed to the statement,
not to a fragile call-index.
"""

from unittest.mock import MagicMock, patch

import pytest

from app.services.db_migrator import (
    run_migrations,
    MIGRATION_LOCK_KEY,
)

INIT_DB_SENTINEL = "-- INIT_DB_SQL_CONTENT_SENTINEL --\nCREATE TABLE projects (id int);"


def _fake_init_db_sql():
    """A stand-in for the module-level INIT_DB_SQL Path whose read_text()
    returns the sentinel, so only the init_db.sql read is observable (the
    real delta files are still read via their own Path objects)."""
    fake = MagicMock(name="INIT_DB_SQL")
    fake.read_text.return_value = INIT_DB_SENTINEL
    return fake


def _sql_text(call):
    """Render the SQL text of a conn.execute(...) positional arg."""
    if not call.args:
        return ""
    return str(call.args[0])


def _build_conn(*, baseline_count, projects_exist, applied_rows=None,
                delta_raises=False):
    """Build a MagicMock connection whose .execute() routes by SQL text.

    baseline_count : int  -> value returned by the 000_baseline COUNT(*) scalar
    projects_exist : bool -> value returned by the information_schema EXISTS scalar
    applied_rows   : list -> rows returned by 'SELECT migration FROM schema_migrations'
    delta_raises   : bool -> if True, executing a delta .sql file raises RuntimeError
    """
    applied_rows = applied_rows or []
    conn = MagicMock(name="conn")

    def execute(statement, params=None):
        sql = str(statement)
        result = MagicMock(name="result")

        if "WHERE migration = '000_baseline'" in sql:
            result.scalar.return_value = baseline_count
        elif "information_schema.tables" in sql:
            result.scalar.return_value = projects_exist
        elif "SELECT migration FROM schema_migrations" in sql:
            result.fetchall.return_value = applied_rows
        elif delta_raises and ("CREATE" in sql or "ALTER" in sql) \
                and "schema_migrations" not in sql \
                and "pg_advisory" not in sql \
                and "projects (id int)" not in sql:
            # Simulate a delta migration file failing.
            raise RuntimeError("delta boom")
        return result

    conn.execute.side_effect = execute
    return conn


def _build_engine(conn):
    """Wrap a conn in an engine whose connect() is a context manager."""
    engine = MagicMock(name="engine")
    cm = MagicMock(name="connect_cm")
    cm.__enter__.return_value = conn
    cm.__exit__.return_value = False
    engine.connect.return_value = cm
    return engine


def _executed_sql(conn):
    return [_sql_text(c) for c in conn.execute.call_args_list]


def test_fresh_db_runs_init_db_sql_as_step0():
    """projects absent + no 000_baseline → init_db.sql executed as step 0."""
    conn = _build_conn(baseline_count=0, projects_exist=False)
    engine = _build_engine(conn)

    fake_init = _fake_init_db_sql()
    with patch("app.services.db_migrator.INIT_DB_SQL", fake_init):
        run_migrations(engine)

    # init_db.sql was read and its content executed.
    fake_init.read_text.assert_called_once()
    sqls = _executed_sql(conn)
    assert any(INIT_DB_SENTINEL in s for s in sqls), \
        "init_db.sql content should be executed on a truly-fresh DB"
    # The pre-tracking INSERT marker path must NOT run (init_db inserts it itself).
    assert not any(
        "INSERT INTO schema_migrations (migration) VALUES ('000_baseline')" in s
        for s in sqls
    )
    # Lock acquired and released.
    assert any("pg_advisory_lock" in s for s in sqls)
    assert any("pg_advisory_unlock" in s for s in sqls)


def test_pretracking_db_marks_baseline_without_init_sql():
    """projects exist + no 000_baseline → INSERT marker only, no init_db.sql."""
    conn = _build_conn(baseline_count=0, projects_exist=True)
    engine = _build_engine(conn)

    fake_init = _fake_init_db_sql()
    with patch("app.services.db_migrator.INIT_DB_SQL", fake_init):
        run_migrations(engine)

    fake_init.read_text.assert_not_called()
    sqls = _executed_sql(conn)
    assert not any(INIT_DB_SENTINEL in s for s in sqls), \
        "init_db.sql must NOT run when projects already exists"
    assert any(
        "INSERT INTO schema_migrations (migration) VALUES ('000_baseline')" in s
        for s in sqls
    )


def test_recorded_baseline_is_noop_step0():
    """000_baseline already recorded → step 0 skipped entirely (idempotent re-run)."""
    conn = _build_conn(baseline_count=1, projects_exist=True,
                       applied_rows=[("000_baseline",)])
    engine = _build_engine(conn)

    fake_init = _fake_init_db_sql()
    with patch("app.services.db_migrator.INIT_DB_SQL", fake_init):
        run_migrations(engine)

    fake_init.read_text.assert_not_called()
    sqls = _executed_sql(conn)
    assert not any(INIT_DB_SENTINEL in s for s in sqls)
    # information_schema check is skipped because baseline_recorded is truthy.
    assert not any("information_schema.tables" in s for s in sqls)
    # No baseline marker INSERT either.
    assert not any(
        "INSERT INTO schema_migrations (migration) VALUES ('000_baseline')" in s
        for s in sqls
    )


def test_advisory_lock_acquired_and_released():
    """pg_advisory_lock issued before work, pg_advisory_unlock issued in finally."""
    conn = _build_conn(baseline_count=1, projects_exist=True,
                       applied_rows=[("000_baseline",)])
    engine = _build_engine(conn)

    run_migrations(engine)

    sqls = _executed_sql(conn)
    lock_idx = next(i for i, s in enumerate(sqls) if "pg_advisory_lock" in s)
    unlock_idx = next(i for i, s in enumerate(sqls) if "pg_advisory_unlock" in s)
    assert lock_idx < unlock_idx, "lock must be acquired before unlock"
    assert lock_idx == 0, "advisory lock must be the first statement issued"

    # The lock key passed matches the module constant.
    lock_call = conn.execute.call_args_list[lock_idx]
    assert lock_call.args[1] == {"k": MIGRATION_LOCK_KEY}
    unlock_call = conn.execute.call_args_list[unlock_idx]
    assert unlock_call.args[1] == {"k": MIGRATION_LOCK_KEY}


def test_delta_failure_propagates_and_unlocks():
    """A delta execute raising → exception propagates AND unlock still runs."""
    # baseline recorded so step 0 is skipped; deltas then run and the first one
    # (a real file in migrations/delta/) raises.
    conn = _build_conn(baseline_count=1, projects_exist=True,
                       applied_rows=[("000_baseline",)], delta_raises=True)
    engine = _build_engine(conn)

    with pytest.raises(RuntimeError, match="delta boom"):
        run_migrations(engine)

    sqls = _executed_sql(conn)
    assert any("pg_advisory_unlock" in s for s in sqls), \
        "advisory lock must be released in finally even when a delta fails"
