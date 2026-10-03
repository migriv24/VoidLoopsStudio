---
type: Concept
title: The fundamental node taxonomy
description: The category system above individual node kinds — what a node fundamentally IS (input, time/event, generator, transform, combine, utility, Loop, output), what a kind inherits from its category, and the Blender thought experiment that generalizes the design.
resource: null
tags: [status:planned, audience:dev, audience:library, confidence:asserted, foundation]
timestamp: 2026-07-06T00:00:00Z
---

> Born from the author's dev-answer 8 (2026-07-06): don't treat any node (e.g. the
> "sequence node") as a base elemental thing — many nodes will share properties a
> well-designed node would *inherit*. Blender's geometry-node categories (Input, Output,
> Attribute, Utilities, Group, Generate, Simulation, …) are the reference lineage. **The
> important thing isn't that we use Blender's format — it's that we understand where it
> came from**: decades of node-system practice converging on the same few fundamental
> roles.

# Two levels: category and kind

A node **kind** (a glyph: `osc`, `sequencer`, …) is an *instance* of a node **category**.
The category fixes what the kind inherits — its port *conventions* (what side signals
enter/leave, which port is principal), its default behaviors, and how the
[reducer](/concepts/reducer.md) treats it. The kind adds specifics (fields, exact ports,
an editor). This is the inheritance the author asked for: a **sequence node** is not
elemental — it inherits "advances on clock" from the time/event category and
"contains arrangeable content" from the Loop-like containers, then adds its own ports.

# The fundamental categories (v-next design)

| category | role | VLS examples | Blender cousin |
|---|---|---|---|
| **Input / source** | brings outside material into the graph | MIDI file, live MIDI-in, sample file, mic | Input |
| **Time / event** | makes or transforms time and events | clock, sequencer, sequence node, arpeggiator, quantizer | (ours — music's own) |
| **Generator** | events → signal; where sound comes into being | osc, sampler, VST instrument | Generate / primitives |
| **Transform** | signal → signal, statefully | filter, delay, reverb, VST effect | Attribute / transforms |
| **Combine** | many → one | mix/add, crossfade, switch | Join Geometry |
| **Utility** | small value plumbing: math, logic, converters between signal types | gain-scale, tick↔seconds, events→clock | Utilities |
| **Loop (group)** | composition; a sub-graph as one node | any [Loop](/concepts/loop.md) | Group |
| **Output** | sinks; where the graph meets a [domain](/concepts/render-domain.md) | speakers, file — someday non-audio domains | Output |

The author flags Utility and Input as categories we will likely *need to integrate*, not
just admire — a patch always ends up needing small adapters and ways to get material in.

Generators sit on the [compute-holiday seam](/concepts/instrument-as-holiday.md) when the
generating code is external (a VST) — the category is where "holidays as generators"
becomes visible in the graph.

# The Blender thought experiment (the generalization test)

The author's test for whether this taxonomy is *general*: **"what if we were building VLS
into Blender's existing nodes?"** — e.g., plugging a sound in as a unit of *motion* for a
3D object. What survives the move is exactly the category system (input, generate,
transform, combine, group, output — Blender already has all of them); what changes is the
**signal types** on the wires (audio/events/clock vs. geometry/attributes). Conclusion,
adopted as a design rule:

> **Categories are domain-agnostic; signal types carry the domain.** Keep the taxonomy's
> skeleton portable and push everything musical into the typed ports.

This is not idle: the [vision](/references/voidloops-vision.md)'s wider program includes
rebuilding Blender on Void Core someday, and the planned visuals **sister app** would meet
VLS exactly here — a cross-domain wire (sound driving motion) is two graphs agreeing on a
signal type at a boundary port. Designing the categories domain-agnostically now is what
keeps that door open. (See Blender's
[geometry-nodes manual](https://docs.blender.org/manual/en/latest/modeling/geometry_nodes/index.html)
for the reference taxonomy.)

# What this means for the code (not yet built)

v1's five glyphs stand; the category layer is **design, not code**, until the VST/LMMS
step forces the second wave of kinds (see [node types](/concepts/node-types.md) for the
decided growth set). When it lands, the natural shape is a `category` field on
`NodeKind` (`voidloops/model.py`) driving inherited port conventions — small, additive.

# Status

`planned` — a design layer above the built v1 kinds. Formalizing category inheritance in
the glyph system is open question #11 in [developer questions](/developer_questions.md).
