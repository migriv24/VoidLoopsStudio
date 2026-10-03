---
type: Foundation
title: The node graph
description: Void Loops is a node-based (dataflow / patching) DAW. The project is a signal-flow graph of coarse musical nodes, not a timeline of clips. This is the central reframe (2026-06-29).
resource: notes/node-graph.md
tags: [status:planned, audience:dev, audience:library, confidence:asserted, foundation]
timestamp: 2026-06-29T00:00:00Z
---

> **The pivot (2026-06-29).** Void Loops abandons the arrangement **timeline** and becomes
> a **node-based DAW** — a dataflow / patching environment in the lineage of Max/MSP, Pure
> Data, Reaktor, VCV Rack, and Bitwig's Grid (and modular synthesis — the 70s/80s practice
> the author was reaching for). This replaces [pattern as mantle / clip](/concepts/loop.md)
> as the top-level structure and retires [arrangement](/concepts/arrangement.md).

# What it is

The project is a **signal-flow graph**: [nodes](/concepts/node-types.md) (coarse musical
units) connected by **wires** at typed **ports**. To make sound, the **output node** is
*pulled* for the next block of samples; it pulls its inputs recursively back to the
generator nodes (**demand-driven / pull-based block processing**). Time is the global
sample clock advancing per block — see [time without a timeline](/concepts/time-without-timeline.md).

# Coarse granularity (the key constraint)

Nodes are **musically meaningful**, not DSP primitives. A node is a sampler, a VST
instrument, a MIDI/sequencer source, an effect, a mixer, an output — *not* a single
oscillator or filter knob. Pure Data is "way too pure"; we are closer to **FL Studio's
Patcher / Bitwig device chains**. A node's parameters are its rune `content`, edited in
place — not exploded into sub-nodes. (You plug a sample and a MIDI into an instrument
node; you don't wire every variable.)

# Why this fits Void Core better than the timeline did

A node graph **is** an [interaction net](/concepts/reducer.md): nodes are agents, glyphs
fix [port signatures](/concepts/node-types.md), wires are [links/bindings](/concepts/effect-and-routing.md),
a sub-patch is a [Loop (a mantle used as a node)](/concepts/loop.md) (net
composition), a VST is a [holiday](/concepts/instrument-as-holiday.md) (boundary port),
and feedback is a [cycle](/concepts/loops-and-feedback.md) (opaque agents). The
[drift test](/concepts/daw-architecture.md) still holds: Void Core owns the graph; the
host streams the samples.

# Formal backing (so it isn't hand-wavy)

- **Kahn Process Networks** — deterministic dataflow (output independent of schedule); the
  dataflow cousin of Void Core's interaction-net **confluence**.
- **Synchronous Dataflow (SDF)** (Lee & Messerschmitt / Ptolemy) — the model for statically
  scheduling a multirate signal-flow graph in real time.

# Further reading (external background — not a substitute for the above)

- [Dataflow programming](https://en.wikipedia.org/wiki/Dataflow_programming) ·
  [Kahn process networks](https://en.wikipedia.org/wiki/Kahn_process_networks) — the formal
  model + its determinism (the confluence cousin).
- [Pure Data](https://en.wikipedia.org/wiki/Pure_Data) ·
  [Max](https://en.wikipedia.org/wiki/Max_%28software%29) ·
  [Modular synthesizer](https://en.wikipedia.org/wiki/Modular_synthesizer) — the lineage.

# Status

`planned`. The central concept of the post-pivot design; everything else re-anchors here.
