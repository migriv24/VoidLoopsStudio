---
type: Reference
title: Void Loops vision
description: The project's goals and motivation in the author's words — a from-scratch, owned, interaction-net-native DAW.
resource: null
tags: [status:current, audience:dev, confidence:verified, vision]
timestamp: 2026-06-27T00:00:00Z
---

> This is the author's stated vision, captured 2026-06-27. It is `status:current`
> because it is a faithful record of intent (a Reference/vision doc, exempt from the
> "current needs a code resource" rule), not a claim about built code.

# The goal

Remake FL Studio from scratch — **owned**, so the author can change anything — but built
**on top of [Void Core](/references/void-core.md)**, the author's own interaction-net
overlay engine. Hence the name: **Void Loops Studio**.

# Why "from LMMS, not from nothing"

A DAW is enormous. Rather than start from zero, harvest a mature open-source pattern DAW
(**LMMS**) for the hard real-time parts, and rebuild the model + UI on Void Core. See
[LMMS engine](/components/lmms-engine.md).

# Why interaction nets

The author already uses a DAW fluently (FL Studio) and recognized the structural
overlaps unprompted: a **pattern feels like a mantle**, a **VST feels like a holiday**,
an **effect-on-a-track feels like a rule on a tagged mantle**, and **loops are a real
mathematical structure**, not just the Fruity-Loops pun. Void Loops is the experiment in
building a DAW whose foundation *is* graph theory / interaction nets. See
[the Loop](/concepts/loop.md),
[instrument as holiday](/concepts/instrument-as-holiday.md),
[loops & feedback](/concepts/loops-and-feedback.md).

# The node pivot (2026-06-29) and its motivation

Mid-design, the author chose to abandon the **timeline** and make Void Loops a fully
**node-based** DAW ([node graph](/concepts/node-graph.md)) — in the dataflow / modular-synth
lineage (Max, Pure Data, Reaktor, VCV Rack), at a *coarse, musical* node granularity (a
sample node, a MIDI node, a VST node — not Pure-Data primitives). The deepest motivation is
a feature FL Studio couldn't give: a **reversed copy of the song's ending placed at the
start, that updates live when the ending changes**. That "render-reference" is the project's
north star and falls out naturally from a node graph (a wire into a rendered sub-graph) — see
[reverse & reference](/concepts/reverse-and-reference.md). The author wants a DAW that "stays
open to capabilities" and is faithful to 70s/80s modular practice; recursion and reversal
must never be foreclosed (see [rules & reversibility](/concepts/rules-and-reversibility.md)).

# Music-first (the author's boundary, 2026-07-06)

**VLS is primarily for music and audio production** — the transformation of sounds, the
construction of melodies, the manipulation of samples. That is the main thing; features
like negative-length reversal are ideas the design keeps *open*, not the point (see
[rules & reversibility](/concepts/rules-and-reversibility.md)).

Visualization is a real part of DAW culture (FL Studio leans on it), so VLS will likely
grow *some* visual elements or ways of producing visuals — a future plan, not now — but
it must **not become about that**. The ambitious visual work belongs to a planned
**sister application** in the TouchDesigner ([derivative.ca](https://derivative.ca/)) /
Cables ([cables.gl](https://cables.gl/)) lineage — node-based visual programming that
would work *very closely* with VLS (two node graphs, same Void Core substrate). Recorded
here as direction; no design yet.

# Standing on LMMS (and saying so)

The engine harvest means VLS will carry LMMS's plugin host, DSP, **and its large library
of sounds, samples, and presets**. That debt is acknowledged prominently — see
[LMMS engine](/components/lmms-engine.md) — with credit to
[github.com/LMMS/lmms](https://github.com/LMMS/lmms) and [lmms.io](https://lmms.io/).

# The wider program

Void Loops is the **first** of several planned "rebuild X on Void Core" projects
(Blender, Godot, … later). The DAW is first because the author is most fluent in music.
A secondary goal is therefore to **stress-test whether Void Core can truly be a
foundational library** for a large, compute-heavy application — the DAW is the proof.

# Status

`current` (faithful record of intent). The *design* it motivates is in the
[concepts](/index.md); the *code* is unbuilt.
