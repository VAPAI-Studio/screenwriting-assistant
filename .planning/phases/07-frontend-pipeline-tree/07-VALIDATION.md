---
phase: 7
slug: frontend-pipeline-tree
status: draft
nyquist_compliant: true
wave_0_complete: true
created: 2026-03-12
---

# Phase 7 -- Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | None -- no frontend test framework installed |
| **Config file** | none |
| **Quick run command** | `cd frontend && npm run build` |
| **Full suite command** | `cd frontend && npm run build && npm run lint` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd frontend && npm run build`
- **After every plan wave:** Run `cd frontend && npm run build && npm run lint`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 07-01-01 | 01 | 1 | TREE-01 | build | `cd frontend && npm run build` | yes | pending |
| 07-01-02 | 01 | 1 | TREE-03 | build | `cd frontend && npm run build` | yes | pending |
| 07-02-01 | 02 | 2 | TREE-01 | build | `cd frontend && npm run build` | yes | pending |
| 07-02-02 | 02 | 2 | TREE-01 | build | `cd frontend && npm run build` | yes | pending |
| 07-02-03 | 02 | 2 | TREE-01 | build | `cd frontend && npm run build` | yes | pending |
| 07-03-01 | 03 | 2 | TREE-02 | build | `cd frontend && npm run build` | yes | pending |

---

## Wave 0 Requirements

*Existing infrastructure covers all phase requirements. No frontend test framework installation needed -- `npm run build` (TypeScript compilation) serves as the automated quality gate.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Tree renders collapsible hierarchy of phases, subsections, agent badges | TREE-01 | No frontend test framework; visual UI component | Open /books, create agents, verify tree shows phase->subsection->agent hierarchy with expand/collapse |
| Tree auto-refreshes on agent CRUD | TREE-02 | Requires browser interaction to verify React Query invalidation | Create/edit/delete agent, observe tree updates without page reload |
| Empty state renders when no agents | TREE-01 | Visual verification | Delete all agents, verify "Create agents to see how they map to your pipeline" message |
| Toggle excludes agent from pipeline reviews | TREE-03 | Requires browser interaction + backend state verification | Toggle agent off, verify visual distinction, verify agent excluded from next pipeline review |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 15s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved
