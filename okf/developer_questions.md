---
type: Questions
title: Developer questions
description: A living log of open decisions for the author to answer, each linked to the OKF section it affects. The companion to roadmap.md — roadmap says what we'll build; this says what we still need to decide.
tags: [status:current, audience:dev, confidence:asserted]
timestamp: 2026-07-06T00:00:00Z
---

Open decisions, newest concerns first. Each has a **lean** (my recommendation) so a
non-answer still has a sensible default. Answer inline, in chat, or via FaultSack notes;
answers get folded into the concepts and cleared from here.

> **2026-07-06:** the author answered the whole first batch (questions 1–7) via FaultSack
> notes. All seven are folded into the concepts — see the *decided* list below. The open
> questions that follow are the refined remainders those answers surfaced.

# Open

## 17. Native wire relations — numeric `"i:j"` or the named `signal:src->dst` form? (2026-07-16)

The Python model writes wire relations as `audio:out->in` (self-describing,
name-stable); the reduce contract and Void Maiz's projection both speak the
linear numeric form `"i:j"` (port 0 = principal, aux 1..n in glyph declaration
order) — `render.py` already converts named→linear at compile time. The native
model must pick one. **Lean (proceeding on it): numeric in the model.** The
named form was a convenience of the era when nothing read relations but our own
code; now two consumers (Maiz projection, the reduce contract) pin the numeric
form, and port names live in glyph hints where the canvas displays them anyway.
Costs, honestly: relations stop being human-readable in raw state JSON, glyph
port order becomes a compatibility surface (append-only from here), and
Python-era projects need a one-shot relation translation on import (native
milestone 2). Multi-inlets (mix.in, sequence.arr) take ONE index for now —
fan-in wires share it — pending Maiz's spare-slot design (their backlog).
Affects [node types](/concepts/node-types.md), [own UI](/components/own-ui.md),
the roadmap's native era. Rider: does the native shell share
`default.vlp.json` with the Python editor? Lean: no — its own file
(`default.native.vlp.json`) until the importer lands; one project file with two
writers and two relation dialects would corrupt silently.

> **#16 DECIDED (2026-07-09, same day):** the author confirmed **C++20** — and
> widened the plan: the node UI layer becomes a **separate, generalizable
> project, Void Node** (`../VoidNode`, own OKF, founded today), on which the
> native VLS builds. Production order: recreate the existing VLS capability,
> better, piece by piece. Widgets-as-nodes is a Void Node founding feature.
> The Void Core C++ audit ran (C ABI ready; the reduce-at-the-Python-seam gap
> filed in `../VoidNode/MESSAGE_FOR_VOIDCORE.md`). The evaluation below is kept
> for the record; the living plan is Void Node's OKF + the roadmap's native era.

## 16. The native era — language & stack for the real VLS (author, 2026-07-09)

The author called it after the 2026-07-09 jam round: *"the actual VLS application
will be in a different language likely, and will have a more custom GUI that's more
responsive. I personally think we should just start development on that one, and
stop using python for things."* And the requirement that shapes everything:
libraries must have **enough control to log the UI itself** — node movements,
gestures, every interaction as a visible, replayable action (the dispatcher
principle, now applied to the whole application). *"If we need something with a LOT
of control and isn't available in another library, we might just have to make it
ourselves."*

What the stack must serve (in priority order):

1. **Void Core stays the substrate** — it's a C library; any serious language binds
   to it directly, in-process. The dispatcher remains THE seam: the GUI is a thin
   client that issues commands and reads state, exactly like the Python editor —
   that architecture is the part of the prototype that was always permanent.
2. **Total observability** → this argues hard for an **immediate-mode GUI**
   (Dear ImGui / egui family): every widget and every canvas interaction passes
   through our code every frame, so "log node movements" is a print statement, not
   a fight with a retained toolkit's hidden state. Qt-class toolkits are the
   opposite of what the author asked for.
3. **The audio engine**: streaming block rendering (the thing Python could never
   do — real-time DSP), the RemoteVstPlugin client re-implemented natively, the
   VST3/CLAP path, eventually the LMMS instrument harvests (C++ sources).
4. **Self-contained, vendorable pieces** (the LiteGraph lesson): single-file or
   near-single-file libraries we vendor with licenses, no framework lock-in.

**The two credible stacks:**

- **C++20** — least friction everywhere that matters: Void Core is C, the LMMS
  harvest is C++, the VST3 SDK is C++, RemoteVstPlugin's protocol code is C++.
  GUI: **Dear ImGui** (vendorable, MIT, the de-facto standard for exactly this
  kind of pro-audio tool) with a **node canvas of our own** on its drawlist
  (imnodes as the studied reference — small enough to own, which answers the
  author's "make it ourselves" instinct without rebuilding text input and docking).
  Audio I/O: **miniaudio** (single-file, public-domain/MIT) or RtAudio. This is
  also what dev-answer 7 quietly anticipated ("the C++ harvest makes constraints
  real").
- **Rust** — better safety/tooling story; egui (immediate-mode, observability-
  friendly), cpal for audio, clap-sys/vst3-sys exist. The cost: every LMMS/VST
  harvest crosses a language boundary, unsafe FFI at exactly the hot spots, and
  the node canvas + piano roll still end up hand-built (egui_snarl is young).

**Lean: C++20 + Dear ImGui + our own node canvas (imnodes-informed) + miniaudio**,
with the engine built FIRST (streaming renderer + RemoteVstPlugin client behind
the same snapshot contract `render.py` defines today) and the ImGui shell second.
The Python VLS **stays alive as the reference implementation and test harness** —
its model/compile semantics (`model.py`, `render.py`, the 16 test files) are the
spec the native engine must match, and it keeps working for jams during the port.
Rust remains the documented alternative if the author weighs safety over harvest
friction. Affects [own UI](/components/own-ui.md), [LMMS engine](/components/lmms-engine.md),
[realtime boundary](/concepts/realtime-boundary.md), the whole [roadmap](/roadmap.md).

## 14b. Widgets as nodes — the remaining half

The FOUNDATION SHIPPED 2026-07-08 (see decided #14a below): the `control` signal,
params as `p:<field>` inlets, and the utility kinds (value / math / map / compare +
`time-of-day`). Still open, the *widget* half proper:

- **Time-varying modulators** (LFO, envelope, a draggable `slider` node with a real
  slider ON its face) — blocked on per-block evaluation, i.e. streaming playback
  (roadmap item 3). Today control values evaluate once per render.
- **VST parameters as ports**: the RemoteVstPlugin protocol exposes
  `IdVstParameterCount`/`ParameterDump`/`SetParameter` — a vst node could grow
  `p:` inlets for the plugin's own automatable knobs. Design after the plugin
  window face gets real use.
- **Musical presets per effect** ("I don't know what numbers to put").

**Lean:** slider-on-node-face first (LiteGraph widgets host it naturally), LFO when
streaming lands. Affects [node types](/concepts/node-types.md), [own UI](/components/own-ui.md).

## 13. Does `sequence` subsume `sequencer`? (now: does `midi` subsume both?)

The sequence node is built (2026-07-08); `sequencer` is strictly a special case.
**New candidate (2026-07-08): the `midi` node** — same semantics as sequence, plus
the dedicated piano-roll window face the author asked for. If the midi node's UX
proves out in jam sessions, it subsumes *both* older kinds.

**Lean:** let the author live with `midi` for a while; if it becomes the reflex,
retire `sequencer` (keep `sequence` as the faceless/compact variant or fold it too).
Affects [node types](/concepts/node-types.md).

14a. **Params as ports — the foundation** *(shipped 2026-07-08, first wave of #14)*:
    the `control` signal type; every curated numeric field is a bindable `p:<field>`
    inlet (osc.tuning, effect.amount/feedback, mix/output/sample-in.gain,
    sampler.root, sequence/midi.transpose); utility kinds `value`, `math`
    (add/sub/mul/div/min/max/pow/mod, unwired inlets fall back to inline a/b),
    `map` (range), `compare` (lt/le/gt/ge/eq/ne → 1/0) and the `time-of-day` input
    (the author's DJ-dynamic example — hour 0–24, `override` pins it). Evaluated
    once per render at compile time (`voidloops/render.py::_eval_control`;
    `tests/test_utility.py` 7/7); per-block automation arrives with streaming.
    The widget half stays open as **14b** above.

15. **Node-graph front end** *(decided 2026-07-08, author: "yes! litegraph!")* →
    **vendor LiteGraph.js** (MIT, single-file, no CDN — stays self-contained) and
    rebuild the editor page on it, keeping the `/state`+`/cmd` dispatcher-client seam
    untouched so the migration is page-only. Study **Blender's UI design philosophy**
    during the port (Shift+A already borrowed; multi-select, marquee, zoom/pan,
    auto-reconnect come with the library) (→ [own UI](/components/own-ui.md)).

# Decided (2026-07-06, via FaultSack notes + inline answers) — folded into concepts

1. **Audio-backend holiday split** → the **compute holiday** is where VST implementation
   begins; holidays understood as *generators* (→ [instrument as holiday](/concepts/instrument-as-holiday.md);
   framing passed upstream to Void Core).
2. **How a sequencer holds notes** → mini-timelines *inside* nodes; MIDI survives the
   timeline's removal; the "sequence node" growth sketch (→ [time without a timeline](/concepts/time-without-timeline.md),
   [node types](/concepts/node-types.md)).
3. **v1 node set** → confirmed ("kinda right"), revisit later (→ open #10).
4. **Graph-flatten** → **data-authored Reduce rules**, not a hand-written pass — less
   efficient, far more expandable, and true to the interaction-net spirit
   (→ [the layers](/concepts/reducer.md), [roadmap](/roadmap.md) step 3).
5. **Wire typing** → **strict now** (reject mismatches; avoid crashes while prototyping);
   long-term, unprecedented connections become a *feature* the system interprets
   (→ [node types](/concepts/node-types.md), [rules & reversibility](/concepts/rules-and-reversibility.md)).
6. **Node granularity** *(delegated)* → modulators as params, promotable to nodes; far
   horizon: musically-relevant nodes as preset [Loops](/concepts/loop.md)
   (→ [node types](/concepts/node-types.md), [Loop](/concepts/loop.md)).
7. **UI toolkit** *(delegated)* → defer; first sound is headless; fastest throwaway
   canvas at step 5; final toolkit decided when the C++ harvest makes constraints real
   (→ [own UI](/components/own-ui.md)).
8. **Sequence-node ports / fundamental nodes** → don't treat any node as elemental;
   a **category layer** (input / time-event / generator / transform / combine / utility /
   Loop / output) that kinds *inherit* from, generalization-tested by the Blender thought
   experiment ("categories are domain-agnostic; signal types carry the domain")
   (→ NEW [node taxonomy](/concepts/node-taxonomy.md), [node types](/concepts/node-types.md)).
9. **Generated sound** *(delegated)* → it is a separate mantle: the **render mantle** —
   the flattened snapshot as a named net of generated description-runes with provenance;
   buffers never become runes implicitly; materialize is the one crossing; speakers are
   protected by the boundary limiter, not the math (→ [render domain](/concepts/render-domain.md)).
10. **v1 node set revisit** *(delegated)* → v1 five stand; second wave at step 6, each
    kind category-anchored: `midi-in`, `sample-in`, `sampler`, `vst-instrument`,
    `effect`, `vst-effect`, the sequence node (likely subsuming `sequencer`), utilities
    as needed (→ [node types](/concepts/node-types.md)). **Landed 2026-07-07** (all but
    the sequence node → open #12).
11. **Category inheritance in the glyph system** *(decided by code, 2026-07-07)* →
    exactly the lean: an additive `category` field on `NodeKind` (`voidloops/model.py`),
    plus `holiday: bool` for externally-backed kinds; the compiler pulls voices **by
    category** (`render.py::_pull_generators`), so new kinds slot in without compiler
    edits. Categories are conventions, not glyphs
    (→ [node taxonomy](/concepts/node-taxonomy.md)).
