---
status: partial
phase: 70-show-creation-wizard-mode-presets
source: [70-VERIFICATION.md]
started: 2026-06-18T14:12:21Z
updated: 2026-06-18T14:12:21Z
---

## Current Test

[awaiting human testing]

## Tests

### 1. Connected preset end-to-end (Microserie / Serie conectada)
expected: Creating a show with a connected preset persists `continuity_mode='connected'`, seeds `episode_duration_minutes` (2 for Microserie, 22 for Serie conectada), and the typed Season Arc appears on the show page after creation.
result: [pending]

### 2. Antología preset hides cross-episode steps
expected: Selecting the Antología preset hides the Season Arc field at creation, persists `continuity_mode='anthology'`, and performs no bible season-arc write.
result: [pending]

### 3. Edit-side pre-selection and persistence
expected: Opening an existing show's editor highlights the card matching its stored `continuity_mode` + duration (Microserie vs Serie conectada disambiguated by duration=2). Changing the selection disables cards while in-flight, and the new mode survives a full page reload.
result: [pending]

### 4. Cross-show navigation without reload (CR-03 risk)
expected: Navigating from Show A to Show B without a full page reload shows Show B's correct preset card pre-selected — NOT Show A's. (Known risk: BibleEditor has no `key={showId}` in ShowDetail; the re-seed guard may keep Show A's selection.)
result: [pending]

### 5. Error handling on bible-seed failure (CR-01 risk)
expected: If the chained `PUT /api/shows/{id}/bible` fails after the show is created, the user sees a clear error rather than silent loss of seeded duration / season arc. (Known risk: no try/catch or onError on the two-call create sequence.)
result: [pending]

## Summary

total: 5
passed: 0
issues: 0
pending: 5
skipped: 0
blocked: 0

## Gaps
