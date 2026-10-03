---
type: Dictionary
title: DAW glossary — DAW ⇄ Void Core
description: The dictionary mapping standard DAW vocabulary to Void Core's internal nouns. Ships with the bundle so the mapping is self-describing.
resource: notes/daw-glossary.md
tags: [status:planned, audience:dev, audience:library, confidence:asserted]
timestamp: 2026-06-27T00:00:00Z
---

Void Loops speaks **node-DAW** outward and **Void Core** inward. This table is the seam,
revised for the [node pivot](/concepts/node-graph.md). (Same pattern as Void Core's own
`references/voidcore-glossary.md`, which bridges OKF ⇄ Void Core.)

| node-DAW term | Void Core term (internal) | notes |
|---|---|---|
| Project / patch | the state document (a [node graph](/concepts/node-graph.md)) | the whole signal-flow graph |
| Node (source / effect / mix / output) | [rune](/concepts/note-as-rune.md), typed by glyph | the atomic unit; coarse, musical |
| Node type + its inlets/outlets | glyph + [port signature](/concepts/node-types.md) | |
| Wire / patch cable | [link](/concepts/reducer.md) that fires = a **binding** | typed by signal (audio/events/clock) |
| Group / sub-patch ("pattern") | a [Loop (a mantle used as a node)](/concepts/loop.md) | net composition |
| Note / MIDI event | rune, glyph `note`, inside a [sequencer node](/concepts/node-types.md) | atomic editable unit |
| Clock / sequencer | a node that emits clock/events | time lives here, not on a ruler |
| Instrument / VST / synth / sampler | [holiday](/concepts/instrument-as-holiday.md) | boundary port; VST3/CLAP/LADSPA |
| Sample (single) | rune, glyph `sample` (file ref) | a generator node plays it |
| Effect (reverb, delay) | an [effect node](/concepts/effect-and-routing.md) | a stream processor; a plugin effect is a holiday |
| Mixer / send | a [mix/add node](/concepts/node-types.md) + wires | routing *is* the graph |
| "Tag X → add effect Y" | Scry + a [Temper](/concepts/reducer.md) rule (per-node) | the author's `track_1 → reverb` |
| Reverse / reference clip | a [reverse/reference node](/concepts/reverse-and-reference.md) | live render-reference (the north star) |
| Velocity clamp / grid snap | a [boundary policy](/concepts/rules-and-reversibility.md) | optional, not a core rule |
| Export / bounce to WAV | [output node](/concepts/render-domain.md), gated interval | no timeline length; gate a duration |
| Playback | the same render adapter, to the soundcard | pull the output node |
| Loop | a [clock → wrapping sequencer](/concepts/time-without-timeline.md) | the default mode of a running patch |
| Feedback loop / sidechain | a **cycle** in the net | preserved as opaque agents — [loops & feedback](/concepts/loops-and-feedback.md) |
| ~~Arrangement / timeline~~ | *removed* | see deprecated [arrangement](/concepts/arrangement.md) |

# Status

`planned`. Ships in the bundle because Void Loops *is* a Void Core app (the dictionary
travels with the data, per the OKF design).
