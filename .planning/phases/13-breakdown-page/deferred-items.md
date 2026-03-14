# Deferred Items — Phase 13: Breakdown Page

## Pre-existing TypeScript Build Errors (Out of Scope)

These errors existed before Plan 13-01 and are in files not modified by this plan.

| File | Line | Error |
|------|------|-------|
| `frontend/src/components/Patterns/IndividualEditorView.tsx` | 192 | `Property 'full_width' does not exist on type 'FieldDef'` |
| `frontend/src/components/Patterns/RepeatableCardsView.tsx` | 93 | `Property 'key' does not exist on type 'CardGroupDef'` |
| `frontend/src/components/Shared/SidebarChat.tsx` | 611 | `Type '(override?: string) => Promise<void>' is not assignable to type 'MouseEventHandler<HTMLButtonElement>'` |

These must be resolved before running `tsc --noEmit` produces a clean build.
