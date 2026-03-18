# Phase 16: Staleness Bug & Migration Upgrade Path - Research

**Researched:** 2026-03-18
**Domain:** FastAPI backend bug fix + SQL delta migration
**Confidence:** HIGH

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| SYNC-03 | Staleness detection — saving screenplay content or regenerating scenes sets `breakdown_stale=true` on the project | scene_wizard branch in wizards.py is missing the `_mark_breakdown_stale` call; one-line fix completes this requirement |
</phase_requirements>

---

## Summary

Phase 16 closes two precise, pre-diagnosed gaps identified in the v2.0 milestone audit. Neither gap requires new abstractions, new API endpoints, or new frontend work. Both fixes are surgical: one Python line insertion and one SQL file copy.

**Gap 1 — SYNC-03 scene_wizard bug:** `apply_wizard_result_to_db()` in `wizards.py` already correctly calls `_mark_breakdown_stale` for the `script_writer_wizard` branch (line 274). The `scene_wizard` branch (lines 279–317) creates `ListItem` rows via `db.add()` directly, bypassing the `list_items.py` API endpoints that carry staleness hooks. The fix is to add `_mark_breakdown_stale(db, project.id)` before `db.commit()` at line 317. The import is already present at line 14 (`from .phase_data import _mark_breakdown_stale`).

**Gap 2 — Migration upgrade path:** `009_breakdown_tables.sql` exists as a standalone file in `backend/migrations/` but is absent from `backend/migrations/delta/`. The `db_migrator.py` service reads only from the `delta/` directory. Fresh Docker deployments use `init_db.sql` which already contains all breakdown tables. Existing deployments that started before v2.0 (from a persistent volume) will never receive the breakdown schema unless either the volume is wiped or the SQL is applied manually. Copying `009_breakdown_tables.sql` into `delta/` as `001_breakdown_tables.sql` closes this gap — `db_migrator.py` will apply it automatically on the next startup.

**Primary recommendation:** Add `_mark_breakdown_stale(db, project.id)` in the `scene_wizard` branch of `apply_wizard_result_to_db` before `db.commit()`, then copy `009_breakdown_tables.sql` to `backend/migrations/delta/001_breakdown_tables.sql`. Add a test for scene_wizard staleness in `test_staleness.py`. Mark SYNC-03 as `[x]` in `REQUIREMENTS.md`.

---

## Standard Stack

### Core (already in codebase — no new dependencies)

| Component | Location | Purpose |
|-----------|----------|---------|
| `_mark_breakdown_stale` helper | `backend/app/api/endpoints/phase_data.py:20` | Sets `project.breakdown_stale=True` when non-deleted elements exist. Does not commit — caller's commit covers it. |
| `apply_wizard_result_to_db` | `backend/app/api/endpoints/wizards.py:209` | Applies wizard generation results to DB for all wizard types |
| `db_migrator.py` | `backend/app/services/db_migrator.py` | Startup migration runner that reads `backend/migrations/delta/NNN_*.sql` files in order |
| `009_breakdown_tables.sql` | `backend/migrations/009_breakdown_tables.sql` | Existing idempotent SQL for breakdown schema (uses `CREATE TABLE IF NOT EXISTS`, `ALTER TABLE ... ADD COLUMN IF NOT EXISTS`) |
| `test_staleness.py` | `backend/app/tests/test_staleness.py` | Existing test module for SYNC-03/SYNC-04 hooks |

---

## Architecture Patterns

### Pattern 1: `_mark_breakdown_stale` call convention (one-commit rule)

The helper is designed to be called **before** the caller's `db.commit()`. It does not commit itself. This pattern is consistent throughout the codebase:

```python
# Source: backend/app/api/endpoints/wizards.py:274-276 (script_writer_wizard branch — the correct reference)
_mark_breakdown_stale(db, project.id)
db.commit()
return {"status": "success", "items_created": len(screenplays)}
```

The `scene_wizard` branch must follow the same pattern:

```python
# Target location: backend/app/api/endpoints/wizards.py — scene_wizard branch (lines 279–317)
# Before the final db.commit() at line 317:
_mark_breakdown_stale(db, project.id)
db.commit()
return {"status": "success", "items_created": items_created}
```

**Why this works:** `_mark_breakdown_stale` queries for any non-deleted `BreakdownElement` with the given `project_id`. If none exist (no breakdown yet), it does nothing — the stale flag stays False. If a breakdown exists, `project.breakdown_stale = True` is set on the in-session object. The immediately following `db.commit()` persists both the new `ListItem` rows and the updated stale flag in a single atomic transaction.

### Pattern 2: Delta migration file conventions

From `backend/migrations/delta/README.md`:

- Files must match `^\d+_` (leading digits followed by underscore)
- Use **idempotent SQL** (`IF NOT EXISTS`, `ON CONFLICT DO NOTHING`)
- Never modify or delete an already-applied file
- `000_baseline` is reserved
- `db_migrator.py` reads only `backend/migrations/delta/` not `backend/migrations/`

The `009_breakdown_tables.sql` file already uses idempotent SQL throughout (`CREATE TABLE IF NOT EXISTS`, `CREATE INDEX IF NOT EXISTS`, `ALTER TABLE projects ADD COLUMN IF NOT EXISTS`). It is safe to copy without modification.

**Naming:** The audit recommends `001_breakdown_tables.sql`. Since the `delta/` directory currently contains only `README.md` (no SQL files), `001` is a correct first delta file.

```
backend/migrations/delta/
├── README.md                    # existing
└── 001_breakdown_tables.sql     # new — copy of 009_breakdown_tables.sql
```

### Pattern 3: Existing staleness test structure

`test_staleness.py` already covers:
- PATCH write phase sets stale (test 1)
- PATCH scenes phase sets stale (test 2)
- PATCH non-write/scenes phase does NOT set stale (test 3)
- `script_writer_wizard` sets stale via `apply_wizard_result_to_db` (test 4)
- Creating/updating/deleting scene list items via API sets stale (tests 5/6/7)
- Extraction clears stale flag (SYNC-04)
- No stale set when no breakdown element exists (test 8)

**Missing test:** `scene_wizard` via `apply_wizard_result_to_db` is not tested. The new test follows the exact same pattern as test 4 (`test_script_wizard_sets_stale`) but calls `apply_wizard_result_to_db` with `wizard_type="scene_wizard"`.

```python
# Source: test_staleness.py:147 pattern — adapted for scene_wizard
def test_scene_wizard_sets_stale(self, db_session):
    """apply_wizard_result_to_db() for scene_wizard sets breakdown_stale=True."""
    project_id = str(uuid.uuid4())
    project = Project(
        id=project_id,
        owner_id=MOCK_USER_ID,
        title="Scene Wizard Stale Test",
        breakdown_stale=False,
    )
    db_session.add(project)
    db_session.flush()

    # Must add PhaseData for scenes/scene_list — scene_wizard creates ListItems against it
    phase_data = PhaseData(
        id=str(uuid.uuid4()),
        project_id=project_id,
        phase="scenes",
        subsection_key="scene_list",
        content={},
    )
    db_session.add(phase_data)

    element = BreakdownElement(
        id=str(uuid.uuid4()),
        project_id=project_id,
        category="character",
        name="Test Character",
        is_deleted=False,
    )
    db_session.add(element)
    db_session.commit()

    result = {
        "scenes": [
            {"title": "Scene 1", "description": "Opening scene"},
        ]
    }
    apply_wizard_result_to_db(
        db_session, project, "scenes", "scene_wizard", result
    )

    db_session.refresh(project)
    assert project.breakdown_stale is True
```

### Anti-Patterns to Avoid

- **Do not add a separate `db.commit()` call** — the helper must remain no-commit; one atomic commit covers both `ListItem` creation and the stale flag change. See [Phase 12-01 decision in STATE.md]: "Helper does NOT commit; caller's existing commit covers breakdown_stale change (one-commit rule)"
- **Do not modify `009_breakdown_tables.sql`** — the delta file must be a copy, not a modification of the original numbered migration file
- **Do not name the delta file starting with `000`** — that prefix is reserved for baseline detection in `db_migrator.py`
- **Do not use `db.flush()` instead of relying on caller's `db.commit()`** — `_mark_breakdown_stale` sets an attribute on the ORM object in the same session; flush is unnecessary

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Marking project as stale | Custom SQL `UPDATE projects SET breakdown_stale=True` | `_mark_breakdown_stale(db, project.id)` | Helper already encapsulates the "only mark if breakdown exists" guard |
| Detecting if breakdown exists | Query in-place | `_mark_breakdown_stale` already queries `BreakdownElement` | Centralizes logic; avoids inconsistency across callers |
| Migration tracking | Custom startup check | `db_migrator.py` + `delta/` pattern | Already proven and used; `schema_migrations` table tracks applied deltas |

---

## Common Pitfalls

### Pitfall 1: Committing before calling `_mark_breakdown_stale`

**What goes wrong:** If `db.commit()` fires at line 317 before `_mark_breakdown_stale` is added, the `ListItem` rows are persisted but the project stale flag is not set. Moving the commit after the helper call is the fix — but getting the order wrong leaves the flag unset.

**How to avoid:** Always call `_mark_breakdown_stale(db, project.id)` immediately before the final `db.commit()` in the `scene_wizard` branch, mirroring the `script_writer_wizard` branch above it.

### Pitfall 2: The delta file is idempotent but the UNIQUE constraint may conflict on re-run

**What goes wrong:** `009_breakdown_tables.sql` has a `CONSTRAINT uq_breakdown_element UNIQUE (project_id, category, name)`. On a fresh DB where `init_db.sql` already created the table with the same constraint, the delta file's `CREATE TABLE IF NOT EXISTS` will skip silently. There is no conflict.

**Why it's safe:** `db_migrator.py` records applied migrations in `schema_migrations`. Once `001_breakdown_tables` is applied, the migrator skips it on subsequent startups.

### Pitfall 3: scene_wizard creates a new PhaseData if none exists

**What goes wrong:** `apply_wizard_result_to_db` in the `scene_wizard` branch uses `db.add(phase_data)` + `db.flush()` to create `PhaseData` on demand if `scenes/scene_list` doesn't exist. The `_mark_breakdown_stale` call must come after all `db.add` + `db.flush` calls but before `db.commit()`.

**Current code structure (lines 279–317):**
```
if wizard_type == "scene_wizard":           # line 279 — set keys
    ...
phase_data = db.query(...)...first()        # line 288 — get or create PhaseData
if not phase_data:
    phase_data = database.PhaseData(...)    # line 293 — create
    db.add(phase_data)
    db.flush()                              # line 299
existing_count = db.query(...).count()      # line 301
for i, item_data in enumerate(generated_items):  # line 305
    db_item = database.ListItem(...)
    db.add(db_item)
    items_created += 1
db.commit()                                 # line 317 — INSERT _mark_breakdown_stale BEFORE this
```

The helper goes at line 316 (before `db.commit()`).

### Pitfall 4: Test requires PhaseData for scene_wizard to work

**What goes wrong:** Unlike `script_writer_wizard` which creates `PhaseData(subsection_key="screenplay_editor")` on demand, the `scene_wizard` branch also creates `PhaseData(subsection_key="scene_list")` on demand. The test must either pre-create it or ensure `db.flush()` succeeds before `_mark_breakdown_stale` queries for elements.

**How to avoid:** Pre-create `PhaseData` in the test setup (as shown in the code example above). The `_mark_breakdown_stale` query only touches `BreakdownElement` and `Project` tables — it does not depend on `PhaseData` existence.

---

## Code Examples

### Fix location: wizards.py scene_wizard branch

```python
# Source: backend/app/api/endpoints/wizards.py (current state)
# Lines 279-317 — scene_wizard branch of apply_wizard_result_to_db

# Current (missing the stale call):
    for i, item_data in enumerate(generated_items):
        db_item = database.ListItem(
            phase_data_id=phase_data.id,
            item_type=item_type,
            sort_order=existing_count + i,
            content=item_data,
            status="draft"
        )
        db.add(db_item)
        items_created += 1

    db.commit()                         # <-- fix: insert _mark_breakdown_stale before this
    return {"status": "success", "items_created": items_created}

# Fixed:
    for i, item_data in enumerate(generated_items):
        db_item = database.ListItem(
            phase_data_id=phase_data.id,
            item_type=item_type,
            sort_order=existing_count + i,
            content=item_data,
            status="draft"
        )
        db.add(db_item)
        items_created += 1

    _mark_breakdown_stale(db, project.id)   # <-- added line
    db.commit()
    return {"status": "success", "items_created": items_created}
```

### Delta migration: copy operation

```bash
# Source: backend/migrations/delta/README.md conventions
cp backend/migrations/009_breakdown_tables.sql \
   backend/migrations/delta/001_breakdown_tables.sql
```

The file is already idempotent — no modification needed.

### db_migrator.py behavior on existing database (verified from source)

```python
# Source: backend/app/services/db_migrator.py:34-100
# Fresh DB: init_db.sql ran, schema_migrations has '000_baseline'
#   -> migrator finds '001_breakdown_tables' not in applied -> skips? NO
#   -> '000_baseline' is in applied, '001_breakdown_tables' is not -> applies it
#   -> CREATE TABLE IF NOT EXISTS ... -> no-ops because tables already exist
#   -> records '001_breakdown_tables' in schema_migrations

# Existing pre-v2.0 DB: no '000_baseline' but projects table exists
#   -> migrator inserts '000_baseline' as baseline marker
#   -> '001_breakdown_tables' not in applied -> applies it
#   -> CREATE TABLE IF NOT EXISTS -> creates breakdown tables for first time
#   -> ALTER TABLE projects ADD COLUMN IF NOT EXISTS breakdown_stale -> adds column
```

The idempotent SQL means running `001_breakdown_tables.sql` against a fresh DB (which already has the tables from `init_db.sql`) is safe — all `CREATE TABLE IF NOT EXISTS` and `CREATE INDEX IF NOT EXISTS` statements will no-op.

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Manual `ALTER TABLE` via psql or volume wipe | `db_migrator.py` reads `delta/*.sql` on startup | Added in Phase 12 era | Existing deployments auto-upgrade |
| N/A — `scene_wizard` always bypassed staleness | After fix: `scene_wizard` calls `_mark_breakdown_stale` | Phase 16 | Staleness banner appears after scene generation |

---

## Open Questions

1. **Should `001_breakdown_tables.sql` be a copy or a symlink?**
   - What we know: `db_migrator.py` uses `migration_file.read_text()` — works with both copy and symlink on Linux/macOS
   - What's unclear: Docker volume mounts may not preserve symlinks reliably
   - Recommendation: Use a copy, not a symlink. More portable and explicit.

2. **Should `009_breakdown_tables.sql` be deleted after copying?**
   - What we know: The file is referenced in the audit. It's not mounted in `docker-compose.yml` or referenced by any startup code.
   - What's unclear: Whether any documentation references this file by name
   - Recommendation: Keep both files. The original `009_breakdown_tables.sql` serves as a human-readable named migration. The `delta/001_` copy is what the migrator uses. No conflict.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest |
| Config file | none (run from `backend/` with venv active) |
| Quick run command | `pytest backend/app/tests/test_staleness.py -x` |
| Full suite command | `pytest backend/app/tests/ -x` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SYNC-03 | `scene_wizard` branch of `apply_wizard_result_to_db` sets `breakdown_stale=True` when breakdown exists | unit/integration | `pytest backend/app/tests/test_staleness.py::TestStalenessHooks::test_scene_wizard_sets_stale -x` | Wave 0 — add to existing `test_staleness.py` |

### Sampling Rate

- **Per task commit:** `pytest backend/app/tests/test_staleness.py -x`
- **Per wave merge:** `pytest backend/app/tests/test_staleness.py backend/app/tests/test_breakdown_api.py -x`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `backend/app/tests/test_staleness.py` — add `test_scene_wizard_sets_stale` to `TestStalenessHooks` class (file exists, test method missing)

*(All other test infrastructure is already in place from Phase 12.)*

---

## Sources

### Primary (HIGH confidence)

- Direct code inspection: `backend/app/api/endpoints/wizards.py` — confirmed `_mark_breakdown_stale` is called in `script_writer_wizard` branch (line 274) but NOT in `scene_wizard` branch (lines 279–317)
- Direct code inspection: `backend/app/services/db_migrator.py` — confirmed reads only `backend/migrations/delta/NNN_*.sql`
- Direct code inspection: `backend/migrations/delta/README.md` — naming convention, idempotency rules
- Direct code inspection: `backend/migrations/009_breakdown_tables.sql` — confirmed fully idempotent SQL
- Direct code inspection: `backend/migrations/init_db.sql` — confirmed fresh DBs already have breakdown tables via `000_baseline`
- Direct code inspection: `backend/app/tests/test_staleness.py` — confirmed `scene_wizard` case not tested
- Audit: `.planning/v2.0-MILESTONE-AUDIT.md` — `SYNC-03-scene-wizard` and `migration-upgrade-path` gaps formally diagnosed with exact line numbers

### Secondary (MEDIUM confidence)

- None required — all findings are from direct code inspection

---

## Metadata

**Confidence breakdown:**
- Bug location: HIGH — exact line confirmed by code inspection and audit diagnosis
- Fix pattern: HIGH — `script_writer_wizard` branch in same function is the reference implementation
- Migration safety: HIGH — idempotent SQL confirmed, `db_migrator.py` logic traced
- Test pattern: HIGH — existing `TestStalenessHooks` tests are direct reference implementations

**Research date:** 2026-03-18
**Valid until:** 2026-04-18 (stable codebase; no external dependencies involved)
