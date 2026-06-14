# backend/app/services/db_migrator.py
#
# Startup migration runner.
# On every app start it:
#   0. Acquires a Postgres advisory lock so concurrent replicas (Railway
#      scaling / redeploy overlap) serialize on DDL instead of racing.  The
#      lock is released in a finally block on every exit path.
#   1. Creates schema_migrations table if it doesn't exist (safety net for
#      databases created before migration tracking was added).
#   2. Fresh-DB baseline (step 0 of the migration body):  when the `projects`
#      table is ABSENT and 000_baseline is not yet recorded, the database is
#      truly empty (no docker-entrypoint hook ran — e.g. a managed Postgres on
#      Railway), so init_db.sql is executed once to create the full schema.
#      init_db.sql is fully idempotent and inserts 000_baseline itself.
#   3. Pre-tracking baseline:  when the `projects` table EXISTS but 000_baseline
#      is not recorded (DB created before migration tracking), 000_baseline is
#      marked applied WITHOUT running init_db.sql.
#   4. Reads backend/migrations/delta/NNN_*.sql files in order and applies any
#      that haven't been recorded yet, then records them (per-migration commit).
#
# Fresh DB on Docker:  docker-entrypoint-initdb.d runs init_db.sql which creates
#   the schema and inserts 000_baseline.  Runner sees 000_baseline recorded and
#   skips step 0 (no double-run); it finds nothing pending to apply.
#
# Fresh DB on a managed host (no entrypoint hook):  projects is absent and
#   000_baseline is unrecorded → step 0 runs init_db.sql once.  A second boot
#   sees 000_baseline recorded → step 0 is an idempotent no-op.
#
# Fail-hard:  if init_db.sql or any delta migration raises, the exception
#   propagates and boot crashes loudly rather than serving against a
#   half-migrated DB.  Per-migration commit means already-applied migrations
#   stay recorded and the failing one retries cleanly on the next boot.
#
# Adding a schema change:
#   Create backend/migrations/delta/NNN_description.sql with idempotent SQL,
#   e.g. "ALTER TABLE foo ADD COLUMN IF NOT EXISTS bar TEXT DEFAULT '';"
#   It will be applied automatically on the next app restart.

import logging
import re
from pathlib import Path

from sqlalchemy import text

logger = logging.getLogger(__name__)

DELTA_DIR = Path(__file__).parent.parent.parent / "migrations" / "delta"
INIT_DB_SQL = DELTA_DIR.parent / "init_db.sql"

# Fixed, arbitrary-but-stable bigint key for the migration advisory lock.
# All app instances use the same key so they serialize on the migration run.
MIGRATION_LOCK_KEY = 8273461928374651


def run_migrations(engine) -> None:
    """Apply any pending migrations.  Called once at app startup.

    The whole run is guarded by a Postgres advisory lock so concurrent
    instances serialize DDL.  On a truly-fresh DB (no projects table, no
    000_baseline) init_db.sql is executed as step 0 before deltas.
    """
    with engine.connect() as conn:
        # --- Step 0: acquire advisory lock (serialize concurrent replicas) ---
        conn.execute(text("SELECT pg_advisory_lock(:k)"), {"k": MIGRATION_LOCK_KEY})
        conn.commit()

        try:
            # --- Step 1: ensure tracking table exists ---
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    id         SERIAL PRIMARY KEY,
                    migration  VARCHAR(255) UNIQUE NOT NULL,
                    applied_at TIMESTAMPTZ DEFAULT NOW()
                )
            """))
            conn.commit()

            # --- Step 2: baseline detection ---
            baseline_recorded = conn.execute(
                text("SELECT COUNT(*) FROM schema_migrations WHERE migration = '000_baseline'")
            ).scalar()

            if not baseline_recorded:
                projects_exist = conn.execute(text("""
                    SELECT EXISTS (
                        SELECT 1 FROM information_schema.tables
                        WHERE table_schema = 'public' AND table_name = 'projects'
                    )
                """)).scalar()

                if not projects_exist:
                    # Truly-fresh DB (no entrypoint hook ran): run init_db.sql as
                    # step 0 to create the full schema.  It is idempotent and
                    # inserts 000_baseline itself.  Any failure propagates.
                    logger.info(
                        "db_migrator: fresh database detected (no projects table) — "
                        "running init_db.sql baseline as step 0"
                    )
                    init_sql = INIT_DB_SQL.read_text()
                    conn.execute(text(init_sql))
                    conn.commit()
                    logger.info("db_migrator: init_db.sql baseline applied")
                else:
                    # Pre-tracking DB (projects exist, no marker): record the
                    # baseline marker only; do NOT run init_db.sql.
                    conn.execute(
                        text("INSERT INTO schema_migrations (migration) VALUES ('000_baseline') ON CONFLICT DO NOTHING")
                    )
                    conn.commit()
                    logger.info("db_migrator: marked existing database as baseline")

            # --- Step 3: collect applied migrations ---
            applied = {
                row[0] for row in
                conn.execute(text("SELECT migration FROM schema_migrations")).fetchall()
            }

            # --- Step 4: apply pending delta files (per-migration commit) ---
            if not DELTA_DIR.exists():
                return

            delta_files = sorted(
                f for f in DELTA_DIR.iterdir()
                if f.suffix == ".sql" and re.match(r"^\d+_", f.name)
            )

            for migration_file in delta_files:
                migration_name = migration_file.stem
                if migration_name in applied:
                    continue

                logger.info(f"db_migrator: applying {migration_name}")
                sql = migration_file.read_text()
                conn.execute(text(sql))
                conn.execute(
                    text("INSERT INTO schema_migrations (migration) VALUES (:name)"),
                    {"name": migration_name},
                )
                conn.commit()
                logger.info(f"db_migrator: applied {migration_name}")

            if delta_files:
                pending = [f.stem for f in delta_files if f.stem not in applied]
                if not pending:
                    logger.info("db_migrator: all migrations up to date")
        finally:
            # --- Always release the advisory lock, even on failure ---
            conn.execute(text("SELECT pg_advisory_unlock(:k)"), {"k": MIGRATION_LOCK_KEY})
            conn.commit()
