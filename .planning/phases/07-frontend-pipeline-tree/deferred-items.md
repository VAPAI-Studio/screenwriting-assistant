# Deferred Items - Phase 07

## Pre-existing TypeScript Errors (out of scope)

These errors exist before Phase 07 changes and are not caused by any Phase 07 work:

1. **IndividualEditorView.tsx:192** - Property 'full_width' does not exist on type 'FieldDef'
2. **RepeatableCardsView.tsx:93** - Property 'key' does not exist on type 'CardGroupDef'
3. **SidebarChat.tsx:611** - Type mismatch on button onClick handler (string vs MouseEvent)

These prevent `npm run build` (`tsc && vite build`) from succeeding but do not affect the correctness of the Phase 07 changes. The new types, constants, and API methods compile without errors when checked individually.
