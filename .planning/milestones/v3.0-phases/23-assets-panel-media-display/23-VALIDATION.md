---
phase: 23
slug: assets-panel-media-display
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-19
---

# Phase 23 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | vitest (frontend) |
| **Config file** | frontend/vite.config.ts |
| **Quick run command** | `cd frontend && npm run test -- --run` |
| **Full suite command** | `cd frontend && npm run test -- --run` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd frontend && npm run test -- --run`
- **After every plan wave:** Run `cd frontend && npm run test -- --run`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 23-01-01 | 01 | 1 | ASST-01 | unit | `cd frontend && npm run test -- --run` | ❌ W0 | ⬜ pending |
| 23-01-02 | 01 | 1 | ASST-02 | unit | `cd frontend && npm run test -- --run` | ❌ W0 | ⬜ pending |
| 23-01-03 | 01 | 1 | ASST-05 | unit | `cd frontend && npm run test -- --run` | ❌ W0 | ⬜ pending |
| 23-02-01 | 02 | 2 | ASST-03, MDIA-03, MDIA-04 | unit | `cd frontend && npm run test -- --run` | ❌ W0 | ⬜ pending |
| 23-02-02 | 02 | 2 | ASST-04 | unit | `cd frontend && npm run test -- --run` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `frontend/src/components/Assets/__tests__/AssetsPanel.test.tsx` — stubs for ASST-01, ASST-02, ASST-05
- [ ] `frontend/src/components/Assets/__tests__/MediaThumbnail.test.tsx` — stubs for ASST-03, MDIA-03, MDIA-04
- [ ] `frontend/src/components/Assets/__tests__/AudioPlayer.test.tsx` — stubs for MDIA-03, MDIA-04
- [ ] `frontend/src/components/Assets/__tests__/UploadZone.test.tsx` — stubs for ASST-04

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Drag-and-drop file upload triggers correctly | ASST-04 | Browser drag events not reliably simulated in vitest | Open Assets panel, drag an image file onto the upload zone, confirm upload starts |
| Audio play/pause/stop controls work end-to-end | MDIA-03, MDIA-04 | Native audio element behavior requires real media | Upload an audio file, click play, verify controls respond |
| Scroll position preserved on view toggle | ASST-05 | Scroll position requires real DOM layout | Scroll Assets panel down, switch to Script view, switch back, verify scroll preserved |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
