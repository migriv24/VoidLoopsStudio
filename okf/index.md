---
okf_version: "0.1"
---

# Void Loops Studio — Knowledge Bundle (dev)

An [Open Knowledge Format](/references/okf-spec.md) bundle describing **Void Loops
Studio** — a node-based DAW (a from-scratch FL Studio / LMMS lineage, pivoted to the
dataflow paradigm) built **on top of [Void Core](/references/void-core.md)**, with
interaction nets as its structural foundation.

The thesis in one breath: a DAW is two machines — an **audio engine that computes
samples** (DSP + VST host harvested from LMMS, in C++) and a **project model that only
describes**. Void Loops makes Void Core *own the second machine* and orchestrate the first,
never touching a sample buffer. See [DAW architecture](/concepts/daw-architecture.md) and
the [realtime boundary](/concepts/realtime-boundary.md) — the constraint that keeps us on
the right side of Void Core's drift test.

> **Major pivot (2026-06-29): Void Loops is now a NODE-BASED DAW.** The arrangement
> timeline is gone; the project is a [node graph](/concepts/node-graph.md) (dataflow /
> modular-synth lineage). This is the project's native shape — a node graph *is* an
> interaction net. See the pivot in [log.md](/log.md).

This is the **dev** bundle: it includes `status:planned` concepts (almost everything,
at this stage). Honesty convention (inherited from Void Core): every concept is
`status:planned` (designed, not built), `status:current` (built & backed by a
`resource:` link to code), or `status:deprecated`.

> Status of the project, 2026-07-08: **🏆 prototype v1 shipped; iterating on real
> use.** The v1 slice (steps 0–5) and the author's six acceptance criteria all pass
> (`tests/test_prototype.py`); step 6's harvest is largely in (samples, MIDI, real
> VSTs through the RemoteVstPlugin protocol client, fan-out, tag-routed FX, looping
> sequences, the sequence node). The editor (**v4**) launches from a desktop icon
> onto a persistent user project, with every action echoed as CLI; its canvas now
> rides on **vendored LiteGraph.js** (post-prototype item 1, shipped 2026-07-08 —
> multi-select, zoom/pan, type-checked link dragging, searchable add box, same
> dispatcher seam). Same day: **nodes became windows** — the `midi` node (in-canvas
> piano-roll face), VST nodes opening their real plugin editors (`.fxp` capture),
> and the control graph (#14a: utility math/logic kinds + params as `p:` ports).
> Current target: streaming playback and #14b's widget faces — see the
> [roadmap](/roadmap.md)'s post-prototype era.

# Planned work

* [Roadmap](/roadmap.md) - planned concepts + the near-term build order (node model → first sound: Sequencer → Osc → Output)
* [Developer questions](/developer_questions.md) - the living log of open decisions for the author, each linked to its concept

> **Studying this bundle:** point **FaultSack** (`../FaultSack`)
> at this project — it builds a graph-centrality **module map** + study site (flashcards, quiz,
> and a developer-notes critique flow) over the bundle *and* the code. The old in-tree
> `okf/viz/` viewer was a shim into Void Core's OKF viewer, which the core has since removed;
> FaultSack replaces it, at a higher altitude.

# Concepts — the vocabulary

The node paradigm (post-pivot):

* [The node graph](/concepts/node-graph.md) - **the central concept**: the project is a signal-flow graph of coarse nodes
* [Node types & ports](/concepts/node-types.md) - the node kinds + typed signals (audio/events/clock)
* [The fundamental node taxonomy](/concepts/node-taxonomy.md) - the category layer kinds inherit from; the Blender generalization test
* [Time without a timeline](/concepts/time-without-timeline.md) - time via clock/sequencer nodes; ticks survive, the ruler doesn't
* [Loop](/concepts/loop.md) - **the app's namesake unit**: a sub-graph of nodes used as one node (a mantle wired in by boundary ports); the node-world "pattern"
* [Rules, reversibility & the boundary](/concepts/rules-and-reversibility.md) - three tiers of rule; the core stays total & reversible (strict wiring now, emergent interactions later)
* [Reverse & reference nodes](/concepts/reverse-and-reference.md) - the live render-reference; the project's north star
* [Collaboration](/concepts/collaboration.md) - local / hosted / joined projects; private / bounced / shared Loops; what crosses the wire; the shared clock; what a phone is for (planned, 2026-10-04)

Carried over (re-anchored on the node graph):

* [DAW architecture](/concepts/daw-architecture.md) - the two machines; where the compute boundary falls
* [Realtime boundary](/concepts/realtime-boundary.md) - the audio thread never calls into the core (the drift-test guard)
* [Note as rune](/concepts/note-as-rune.md) - the atomic unit, inside a sequencer node (built, step 1)
* [Instrument as holiday](/concepts/instrument-as-holiday.md) - VSTs and sample sources as boundary ports
* [Effects & routing](/concepts/effect-and-routing.md) - effects are stream-processor nodes; routing is wires
* [Loops & feedback](/concepts/loops-and-feedback.md) - musical loop = wrapping sequencer; feedback = a cycle
* [Render domain](/concepts/render-domain.md) - export/playback as the output node + render adapter
* [The transformation layers](/concepts/reducer.md) - Reduce/Temper/Scry (+ materialize); built in core, ours to apply

Deprecated by the pivot:

* [Pattern as mantle](/concepts/pattern-as-mantle.md) → [Loop](/concepts/loop.md)
* [Arrangement](/concepts/arrangement.md) - the timeline is removed

# Components — the implementations

* [LMMS engine](/components/lmms-engine.md) - harvested DSP + VST host (the host that streams)
* [Void Core spine](/components/voidcore-spine.md) - the linked C core (the model + dispatcher)
* [Own UI](/components/own-ui.md) - our from-scratch node editor (patch canvas)

# References

* [Void Loops vision](/references/voidloops-vision.md) - the project's goals in the author's words
* [DAW glossary](/references/daw-glossary.md) - DAW term ⇄ Void Core term (the dictionary)
* [Void Core](/references/void-core.md) - the foundational engine this is built on
* [OKF spec](/references/okf-spec.md) - the format this bundle conforms to
