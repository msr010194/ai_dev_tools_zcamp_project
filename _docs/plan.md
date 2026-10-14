# Journaling & Personal Knowledge Base App — Scope Spec

## Vision

A personal knowledge base and reflection hub, not a plain note archive. The app presents the user's
notes as a chronological record of their intellectual and personal life, creating an undercurrent of
continuity that stimulates reflection. The novelty is the relationship between **capturing**,
**reflecting**, and **remembering** — not feature count.

Traditional note apps organise through folders (mutually exclusive). This app uses a **3D
organisational model** so notes are never forced into a single exclusive bucket:

| Dimension | Answers | Purpose |
|---|---|---|
| **Type** | What is this note? | Determines structure/behaviour |
| **Collection** | Where does this note belong? | Broad, user-defined, single-home grouping |
| **Tag** | What themes cut across it? | Cross-cutting connections |

## Entry Points (the front door)

The home page presents three **intents**, not a Type picker. Types/Collections/Tags are the
mechanisms operating underneath, not the starting point:

| Entry point | Default Type | Notes |
|---|---|---|
| **Capture** | Idea | Quick switch available to Reference or Plan |
| **Reflect** | Journal | Collection/Tags still user-assigned, not forced into one Journal collection |
| **Preserve / Remember** | Memory | Deliberately mark something worth long-term resurfacing |

Design philosophy: ease of entry and good UI drive engagement, not rigidity or structural
over-engineering. Free-form content is the default; structured fields are added only where they
clearly earn their place (see Types below).

## Note Types

Five Types ship with the app. There is no separate "Decision" type — decisions are recorded as
part of a Plan.

### Journal
Routine, real-time reflection. Also supports a periodic **retrospective** ritual: distinct
weekly/monthly entries that synthesise recent activity (separate from day-to-day entries).

Fields:
- **Entry Date** — auto-filled
- **Mood** — free-text/word choice (e.g. "anxious", "content"); not a numeric or emoji scale
- **Prompt** — optional free text entered by the user; **read-only** once set
- Free-form body

### Idea
Lightweight capture. Fully free-form — no structured fields.

### Reference
Citations/links and reference material.

Fields:
- **Sub-kind** — dropdown: Written / Visual / Audio
- **Link** — free-form URL field

### Plan
Living, evolving intended actions. Also covers decision-type content (a choice plus its rationale)
as part of the plan narrative, rather than as a separate immutable record. Stays free-form beyond
its minimal fields — no enforced "rationale" vs "steps" sub-structure.

Fields:
- **Target Finish/Implementation Date**
- **Checklist** — itemisable list; each item is text + a done/not-done checkbox (no per-item due dates)
- **Current State** — dropdown: Not Started / In Progress / Done / Abandoned
- Free-form body

### Memory
Curated, significant highlights pulled out for long-term resurfacing — retrospective and
deliberate, not a routine capture.

Fields:
- **When**
- **Where**
- Free-form content

## Collections

- Nested/hierarchical (e.g. `Work > Project A > Subproject`)
- User-defined, freely add/rename/delete at any time
- Exactly **one** Collection per note (a single "home"); cross-cutting is handled by Tags, not Collections

## Tags

- **Curated only**: users pick from a predefined, managed tag list — no ad hoc tag creation on the fly
- Tags can be **renamed** without losing any notes attached to them
- Tags are **optional** — a note can be saved with zero tags
- A dedicated **"untagged" filter/view** makes it easy to find notes awaiting future organisation
- Selecting a tag shows a simple list of everything linked to it across Types and Collections
  (the timeline filtered by that tag)

## Home View & Resurfacing

- Default landing view: a **unified chronological timeline** interleaving all Types and Collections,
  filterable/focusable down to a single Collection
- **Resurfacing**: spaced/semi-random resurfacing of older notes (especially Memories), independent
  of date — designed to surface forgotten material rather than a simple date-based "on this day" feed

## Decisions & Out of Scope

- Stack: React frontend, Python FastAPI backend, PostgreSQL; deployed as a single-user demo
- Single user, no accounts or login
- Browse only: no text search
- Out of scope: graph visualisation, tag merging, user-defined prompt templates, multi-user support
