---
type: Foundation
title: DAW architecture — the two machines
description: A DAW is an audio engine that computes samples plus an arrangement model that only describes. Void Loops owns the second and orchestrates the first.
resource: notes/daw-architecture.md
tags: [status:planned, audience:dev, confidence:asserted, foundation]
timestamp: 2026-06-27T00:00:00Z
---

Every DAW, under the UI, is **two machines bolted together**:

# Machine A — the audio engine (computes)

A hard-real-time loop. Every audio block (e.g. 256 frames) it: asks each
[instrument](/concepts/instrument-as-holiday.md) to render its notes for that window,
runs the result through each [effect](/concepts/effect-and-routing.md) in series, and
sums everything down a routing graph to the master output. This is C/C++ DSP. **This
is the part that computes.** Void Loops *keeps LMMS's version of this machine* — see
[LMMS engine](/components/lmms-engine.md).

# Machine B — the project model (describes)

A passive data structure. **Post-pivot (2026-06-29) this is a [node graph](/concepts/node-graph.md)**,
not a timeline: which [nodes](/concepts/node-types.md) exist (sources, sequencers, effects,
mixes, groups, output), wired how, with what parameters. Editing it does **nothing** by
itself — Machine A is *pulled* through it each block. **This is what Void Loops rebuilds on
Void Core**: runes (nodes), mantles (patches/groups), holidays (VSTs), links/bindings
(wires), tags, rules.

# The compute boundary (why this is allowed)

Void Core's railguard — the **drift test** — says: *the host app computes; the overlay
only orchestrates and structures.* A DAW obviously computes (it makes audio), so the
boundary must be drawn exactly. It draws itself: **Machine A is the host (it computes);
Void Core owns Machine B (it structures) and tells Machine A what to render.** Void Core
never touches a sample buffer. This is the same pattern as Void Core's BiologyManager
(edit model → adapter writes the real app), where "the real app" is now a live audio
engine. The hard rule that keeps it honest lives in
[realtime boundary](/concepts/realtime-boundary.md).

# Status

`planned`. This is the founding design decision; no code yet.
