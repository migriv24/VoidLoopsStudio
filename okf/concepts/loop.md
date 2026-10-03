---
type: Concept
title: Loop
description: The Loop — VLS's native unit: a sub-graph of nodes used as a single node (a mantle wired in by boundary ports). The node-world successor of an FL "pattern", and the app's namesake.
resource: notes/loop.md
tags: [status:planned, audience:dev, audience:library, confidence:asserted, foundation]
timestamp: 2026-07-06T00:00:00Z
---

> Renamed from *group node as mantle* (2026-07-06, per the author's FaultSack note: the
> concept needed a real noun to build on). Supersedes the timeline-era
> [pattern as mantle](/concepts/pattern-as-mantle.md). Not to be confused with
> [loops & feedback](/concepts/loops-and-feedback.md), which is about *cycles in the wire
> graph*; a **Loop** is a *grouping* — the two meet only in that a musical loop is often
> played by a Loop.

A **Loop** is Void Loops Studio's native unit: a **sub-graph of nodes used as a single
node**. Structurally it is a [mantle](/references/void-core.md) — its internal nodes are
runes — whose **boundary ports** become the Loop-node's inlets/outlets. Dropping a Loop
into a larger patch is **net composition through boundary ports**, the interaction-net
operation Void Core was built for. It is the node-world successor of an FL Studio
"pattern" — and the app's namesake: you build music by building Loops.

# Why this is cleaner than the timeline version

The timeline design needed "patterns of patterns" via clip-runes placed at offsets — an
awkward second mechanism. Loops are uniform: *a Loop is just a mantle wired in by its
ports*, exactly like every other node. Re-using a Loop twice = two Loop-nodes referencing
one mantle (and the [reverse/reference](/concepts/reverse-and-reference.md) feature is the
same move with a reverse processor on the wire).

# What a sequencer-Loop holds

A drum/melody pattern is a Loop containing a [sequencer node](/concepts/node-types.md) plus
the [note-runes](/concepts/note-as-rune.md) it plays — wired out to a generator. The notes
are owned; the instrument is a [holiday](/concepts/instrument-as-holiday.md) at the boundary.

# The future: Loops as custom nodes

The author's direction (dev-question 6, answered 2026-07-06): eventually **everything
could be modified or edited** — grouping nodes creates a "custom node", and even the
*musically relevant* built-in nodes could ultimately be **preset Loops** (preset groups of
nodes). Two angles to balance: what the first prototype needs now (a fixed, coarse glyph
set) vs. what is most expressive and most faithful to the interaction-combinator spirit
(everything explodable). v1 keeps built-in node glyphs; the Loop mechanism is designed so
it *could* later define node kinds.

# Status

**`current` (2026-07-06) for the v1 mechanism** — `resource:` `voidloops/project.py`
(`add_loop`, `loop_ports`: a Loop's ports are the **free ports** of its referenced
mantle, qualified `<inner>.<port>` — the interaction-net boundary, computed not
declared) + `voidloops/render.py` (`_expand_loops`: recursive compile-time splice with
cycle rejection; spliced sequencers carry their notes along). Verified in
`tests/test_loop.py`: typed boundary wiring, expansion, **reuse** (two Loop nodes, one
mantle), **nesting**, cycle rejection, disk round-trip, and audible render.

Honesty note (dev-answer 4's "hand-wire only the gap"): expansion is a **pre-pass in the
compiler**, not a Reduce rewrite — the core's rule form fires on active pairs, and a
passive container never forms one; boundary-port splicing needs the deferred general
LHS. When the core grows it, the pre-pass migrates into the ruleset.

Still `planned`: Loops as *presets/custom nodes* (the far horizon above), and exposing a
partially-fed `multi` inlet as a boundary port.
