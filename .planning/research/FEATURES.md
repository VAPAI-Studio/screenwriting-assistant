# Feature Landscape: v3.0 Shotlist & Production Breakdown

**Domain:** Film pre-production shotlist creation, asset management, dual-mode app
**Researched:** 2026-03-19
**Confidence:** HIGH

---

## Context: What Already Exists

- `BreakdownElement` model with categories, source tracking, user_modified flag
- `BreakdownPage.tsx` with CategoryTabs, ElementCard, StalenessBar, AddElementDialog
- `breakdown_service.py` AI extraction pipeline
- Staleness pattern: `Project.breakdown_stale` flag
- Reverse sync: user-initiated push of breakdown element back to screenplay
- `SidebarChat` component with brainstorm/action modes
- File upload infrastructure in `books.py`

---

## Table Stakes

| Feature | Why Expected | Complexity |
|---------|--------------|------------|
| Shot creation from script text | Core interaction: highlight -> Add Shot | High |
| Standard shot fields (freeform text) | Shot size, camera, movement, dialogue, sound, etc. | Medium |
| Shot ordering and numbering | Scene 1 Shot 1, Scene 1 Shot 2... | Medium |
| Shotlist table/grid view | Spreadsheet-like — universal format | Medium |
| Scene-level grouping | Shots organized by scene | Low |
| Two-mode app toggle | Distinct visual identity per mode | Medium |
| Read-only script view | Reference in breakdown mode | Medium |
| Media upload for assets | Image and audio for pre-production | High |
| Shot-to-breakdown-element linking | Shots reference characters, props, locations | Medium |

---

## Differentiators

| Feature | Value | Complexity |
|---------|-------|------------|
| AI shotlist generation from script | No mainstream tool auto-generates shotlists | High |
| AI chat with shotlist awareness | Conversational shot creation/modification | High |
| Highlight-to-shot interaction | Text-selection-to-action pattern | Medium |
| Left panel toggle: script vs assets | Fluid reference switching | Low |
| Audio reference uploads | Sound designers value this; no competitor offers | Medium |

---

## Anti-Features (Do NOT Build in v3.0)

| Feature | Why Not |
|---------|---------|
| Scheduling/calendar | PROJECT.md defers |
| Budget/cost tracking | Separate domain |
| Export to PDF storyboards | Separate feature pass |
| Video upload/playback | Too large, needs transcoding |
| Real-time collaborative editing | Save-triggered sync per PROJECT.md |
| Camera/lens database presets | Freeform text sufficient |
| Shot diagram / overhead view | Different product category |
| Storyboard drawing tools | Support image upload instead |

---

## Standard Shot Fields Reference

| Field | Description | Examples |
|-------|-------------|---------|
| shot_size | Frame size | ECU, CU, MCU, MS, MWS, WS, EWS |
| camera_angle | Angle | Eye Level, Low, High, Dutch |
| camera_movement | Movement | Static, Pan, Tilt, Dolly, Tracking |
| lens | Focal length | 24mm, 50mm, 85mm |
| description | What happens | Freeform |
| action | Physical action | Freeform |
| dialogue | Key lines | Freeform |
| sound | Sound design | Freeform |
| characters | Characters in shot | Freeform |
| environment | Location/setting | Freeform |
| props | Props visible | Freeform |
| equipment | Special equipment | Freeform |
| notes | Director/DP notes | Freeform |

---
*Features research: 2026-03-19*
