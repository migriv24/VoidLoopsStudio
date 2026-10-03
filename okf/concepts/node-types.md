---
type: Concept
title: Node types & ports
description: The coarse node taxonomy (generator, event/clock, effect, mix, group, output) and the typed ports/signals (audio, events, clock) that wires carry.
resource: notes/node-types.md
tags: [status:planned, audience:dev, audience:library, confidence:asserted, foundation]
timestamp: 2026-06-29T00:00:00Z
---

A node is a [rune](/concepts/note-as-rune.md); its **glyph** is its node type and fixes
its **port signature** (which inlets/outlets it has, and which is principal). The
taxonomy is deliberately **coarse** ([node graph](/concepts/node-graph.md) granularity).
Above the kinds sits the **[fundamental node taxonomy](/concepts/node-taxonomy.md)** —
the category layer (input / time-event / generator / transform / combine / utility /
Loop / output) each kind inherits from.

# The node kinds (v1 set)

| kind | examples | ports (in → out) |
|---|---|---|
| **generator / source** | oscillator, **sampler** (sample clip), **VST instrument** | events in → audio out |
| **event / sequencer** | MIDI clip, step sequencer, **clock** | clock in → events out |
| **effect** | gain, delay, reverb, filter, VST effect | audio in → audio out |
| **mix / add** | sum/mixer ("stack outputs on top of each other") | many audio in → one audio out |
| **group** | a sub-patch / "pattern" | a [Loop (a mantle as a node)](/concepts/loop.md) |
| **output** | the render sink (speakers / file) | audio in → (the world) |

The author's framing: a **MIDI node needs a source** (an instrument) to become audio —
i.e. a sequencer's events wire into a generator's event inlet. An **add/mix node** stacks
several generators (like Blender geometry-nodes "join").

# Signal types on ports (a wire is typed)

- **audio** — a stream of samples (audio-rate).
- **events** — discrete messages: MIDI notes, parameter changes (control-rate).
- **clock** — timing pulses that drive [time](/concepts/time-without-timeline.md).
- **control** *(2026-07-08, question #14)* — plain numbers: parameter values and
  math/logic plumbing. Evaluated **once per render** at compile time today;
  per-block automation arrives with streaming playback.

A wire may only connect ports of compatible type. This typing is what makes "a MIDI node
requires a source" a *structural* rule, not a convention. Port signatures also feed the
[reducer's](/concepts/reducer.md) `signatures` map when the graph compiles.

## Params as ports (question #14's foundation, shipped 2026-07-08)

A kind's curated numeric fields are **bindable**: each appears as an extra control
inlet named `p:<field>` (osc `p:tuning`, effect `p:amount`/`p:feedback`, mix/output/
sample-in `p:gain`, sampler `p:root`, sequence/midi `p:transpose`). A wire into a
param inlet overrides that field's content value with the evaluated control graph —
"widgets connect to parameters," structurally. Param inlets are named-only (they
never capture a default-port wire) and Loop boundaries stay structural.

Typing is **strict in v1** (mismatches rejected — decided 2026-07-06, dev-answer 5); the
long-term direction is the inverse: unprecedented connections as a *feature* the system
must interpret. See [rules & reversibility](/concepts/rules-and-reversibility.md).

# Growth direction: the "sequence node" (author's sketch, dev-answer 2, 2026-07-06)

The author's rough shape for where the sequencer taxonomy grows: a **sequence node**
that takes an **audio source** (what plays — a VST/instrument node plugged in) and an
**arrangement source** (what/when to play). One kind of arrangement source is a **MIDI
file**; another is an *arrangeable* node the user edits notes in directly (the current
`sequencer` glyph, its notes as a mini-timeline — see
[time without a timeline](/concepts/time-without-timeline.md)). This splits *what plays*
from *what is played* as two pluggable ports. Per dev-answer 8, the sequence node is
**not elemental**: it inherits from the [taxonomy's](/concepts/node-taxonomy.md)
time/event category (clock-driven) and Loop-like containment (arrangeable content), then
adds its ports. UI/UX must be considered *with* this design when it lands ("it always
starts here").

# The decided growth set (dev-answer 10, 2026-07-06 — delegated, decided)

The v1 five stand **unchanged** for first sound (they're built; no churn before audio).
The second wave lands with the VST/LMMS step (build step 6), each kind anchored in its
[category](/concepts/node-taxonomy.md):

- **Input:** `midi-in` (MIDI file/device → events), `sample-in` (audio file → audio /
  sample content).
- **Generator:** `sampler` (events + sample → audio), `vst-instrument` (events → audio;
  [compute-holiday](/concepts/instrument-as-holiday.md)-backed).
- **Transform:** `effect` (audio → audio, native DSP) and `vst-effect` (holiday-backed).
- **Time/event:** the **sequence node** (above) arrives here — likely subsuming the v1
  `sequencer` as a preset/simple case of it.
- **Utility:** added *as needed*, not speculatively (the author expects we'll need them;
  the first real patch will tell us which).

Rationale: this is the minimal set that makes the LMMS harvest usable (VSTs, samples,
effects) while keeping every addition category-anchored rather than ad-hoc.

# Granularity edge cases (dev-answer 6, 2026-07-06 — delegated)

Modulators (LFO / envelope) stay **node parameters** by default, promotable to nodes when
the user wants to share/patch them — coarse by default, explodable on demand. The far
horizon (the author's second angle): even *musically relevant* nodes could ultimately be
**preset [Loops](/concepts/loop.md)** — preset groups of nodes, everything editable — the
most expressive reading of the interaction-combinator spirit. v1 builds the fixed glyph
set; the Loop mechanism keeps the horizon open.

# Status

**`current` (2026-07-08) for the full working set** — `resource:` `voidloops/model.py`
(`Port`/`NodeKind` + `category` + `holiday` + `params`; signal types incl. `control`) +
`voidloops/project.py` (type-checked wiring incl. param inlets) + `voidloops/render.py`
(category-driven compile; signatures feed the reducer; **fan-out and multi-inlets both
compile** via per-wire synthetic indices; `_eval_control` + `_apply_params` = the
control graph). Built kinds: the v1 five, the growth wave (`sampler`, `sample-in`,
`midi-in`, `effect`, `vst-instrument`, `vst-effect`), the **`sequence` node**, the
**`midi` node** (2026-07-08 — sequence semantics + the dedicated piano-roll window
face; question #13's live candidate to subsume sequencer/sequence), the **utility
wave** (`value`, `math`, `map`, `compare` + the `time-of-day` input — question #14a,
`tests/test_utility.py`), **params-as-ports**, and the [Loop](/concepts/loop.md).
Still `planned`: time-varying modulators (LFO/slider faces — #14b, needs streaming),
VST params as ports.
