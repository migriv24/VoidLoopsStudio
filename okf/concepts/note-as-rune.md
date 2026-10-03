---
type: Concept
title: Note as rune
description: A note (and an automation point) is the atomic editable unit — a Void Core rune with a DAW-specific glyph. Built in build-order step 1.
resource: voidloops/model.py
tags: [status:current, audience:dev, audience:library, confidence:verified, foundation]
timestamp: 2026-06-29T00:00:00Z
---

A **note** is the atomic editable unit *inside a [sequencer node](/concepts/node-types.md)*
(post-[pivot](/concepts/node-graph.md): a pattern is a [Loop](/concepts/loop.md)
holding a sequencer + its notes). It is a Void Core [rune](/references/void-core.md) with
glyph `note`. **Built and verified in build-order step 1** (`voidloops/model.py`,
`voidloops/project.py`) — the data shape carries over the pivot unchanged.

# Shape (as built)

| rune field | note meaning |
|---|---|
| `spirit` | stable id + a name (auto `n1`, `n2`, … unique in the pattern) |
| `glyph` | `note` (one of the [node-graph](/concepts/node-types.md) glyphs) — editability type + a documentary `ports` signature |
| `content` | `{ pitch, start, length, velocity }` — **all integers** (see timing below) |
| `tags` | `track:<name>`, … — what the mixer/effect [rules](/concepts/effect-and-routing.md) target; `glyph:note` is implicit |

# Timing is integer ticks (decided 2026-06-29)

`start` and `length` are **integer ticks** at a project PPQN (default 96 — divides
2/3/4/6/8/12/16/24/32 cleanly, for triplets and 32nds). Exact, no float drift, the way
most DAWs store time. `pitch` is a MIDI number (60 = C4); `velocity` is stored unclamped
(a velocity **clamp** is a [boundary policy](/concepts/rules-and-reversibility.md), not a
core law). A **negative `length` is legal** — it is a time-reversed note, kept in the total
algebra rather than forbidden (see [rules & reversibility](/concepts/rules-and-reversibility.md)
and [reverse & reference](/concepts/reverse-and-reference.md)). Conversion to seconds happens
only at the [render boundary](/concepts/render-domain.md) via `ticks_to_seconds(ticks, ppqn,
bpm)`. Project meta (ppqn / bpm / time signature) is scalar and persists in `state.config`.

> Implementation note: the C core's `vc_glyph_default_content` zero-fills a glyph's
> `fields` as empty **strings**, so notes are written with `setjson` (JSON-typed) to get
> real integers, created atomically (one `batch` = one undo frame).

# Future possibility: custom VSTs that read the net (author's note, 2026-07-06)

Because notes are first-class runes in an interaction net — not opaque MIDI bytes — a
*custom* VST could one day consume the **structure around a note**, not just the note:
sound that changes with the chord it sits in, timbre responding to the harmony the rune
participates in. Integrating pre-existing VSTs comes first (they only speak MIDI/audio,
via the [holiday boundary](/concepts/instrument-as-holiday.md)); but net-aware instruments
are a genuinely novel capability this data model leaves open. Noted, not scheduled.

# Why a glyph carries a port signature

Per the interaction-net foundation, a glyph declares its **ports** (a `note` has a
principal port that "meets" an instrument, plus an aux slot for modulation). The `ports`
key rides on the glyph as documentary metadata now; the [reducer](/concepts/reducer.md)'s
`signatures` map (provisional in `model.py`) consumes it when Reduce is wired.

# Status

`current` for the data shape (step 1, `validate`-clean, round-trips through disk). The
instrument wiring it feeds is [planned](/concepts/instrument-as-holiday.md) (step 3).
