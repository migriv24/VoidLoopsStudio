---
type: Roadmap
title: Roadmap
description: Forward-looking index and build order for Void Loops Studio, after the 2026-06-29 node-graph pivot.
tags: [status:current, audience:dev, confidence:asserted, roadmap]
timestamp: 2026-06-29T00:00:00Z
---

The forward-looking counterpart to [index.md](/index.md) and [log.md](/log.md). **Revised
for the node pivot (2026-06-29):** Void Loops is a [node-based DAW](/concepts/node-graph.md),
not a timeline DAW.

# The decisions that fix this roadmap

1. **Node-based, no timeline.** The project is a signal-flow graph of *coarse, musical*
   [nodes](/concepts/node-types.md) (sample / MIDI / VST / effect / mix / output) — FL
   Patcher / Bitwig granularity, not Pure-Data primitives. The arrangement timeline is
   removed; [time comes from clock/sequencer nodes](/concepts/time-without-timeline.md).
2. **Engine: harvest LMMS for DSP + VST hosting**, prioritizing VST support; drive its
   buffer-summing as the runtime our node graph compiles into; ignore its timeline. A
   trivial synth (or libpd) may reach first-sound sooner. See
   [LMMS engine](/components/lmms-engine.md).
3. **Core = total & reversible; lossy policy at the boundary.** No "no negative length"
   rule (negative length = reversal); velocity clamp / grid snap are optional boundary
   policies, not core laws. See [rules & reversibility](/concepts/rules-and-reversibility.md).
4. **Transformation layers are built** (Reduce/Temper/Scry in Void Core); they compile the
   node graph → the engine's render graph. See [the layers](/concepts/reducer.md).
5. **North star, far off:** the live [reverse/reference node](/concepts/reverse-and-reference.md).
   The design must never foreclose recursion/reversal.

# What carries over from steps 0–1 (built before the pivot)

The pivot costs less code than it might seem — most of steps 0–1 survives:
- **Step 0** (the `voidloops` package: `VoidLoopsProject` = VoidCore + Dispatcher + state
  file) — **unchanged**.
- The **rune/mantle/glyph machinery** — unchanged; we define *node* glyphs instead of
  timeline glyphs.
- **`model.py`'s timing + pitch helpers** — kept; clock/sequencer/MIDI nodes still need
  ticks↔seconds and note names ([time without a timeline](/concepts/time-without-timeline.md)).
- **`note` glyph + note-runes** — kept, now as the contents of a
  sequencer-[Loop](/concepts/loop.md).
- **Retired:** the `pattern-clip` glyph and any timeline/arrangement notion.

# v1 build order — toward first sound (Sequencer → Osc → Output)

1. **Node glyphs + ports.** ✅ **DONE (2026-07-01).** The v1 [node glyphs](/concepts/node-types.md)
   (`clock`, `sequencer`, `osc`, `mix`, `output`) with typed port signatures
   (`voidloops/model.py`); `VoidLoopsProject.add_node` / `wire` create and **type-check**
   wires (a wire = a core `link` whose relation encodes `signal:port->port`) with
   `nodes()`/`wires()` readers (`voidloops/project.py`). A `clock→sequencer→osc→output` chain
   `validate`s clean (`tests/test_nodes.py`, 8/8). `pattern-clip` retired. *Graph data shapes proven.*
2. **A patch as a graph.** ✅ **DONE (2026-07-06).** The full first-sound topology with
   the sequencer *holding* its note-runes (containment = the `node:<seq>` tag — notes stay
   first-class and tag-selectable). `add_note(node=seq)` / `notes(node=seq)`;
   `tests/test_patch.py` 6/6. *Node graph round-trips & validates with real musical content.*
3. **Graph compile (flatten) — data-authored Reduce.** ✅ **DONE (2026-07-06).**
   `voidloops/render.py`: named ports ⇄ the reducer's linear `"i:j"` form (multi-inlets
   allocate per-wire indices), the reduce pass runs with rules from
   `config.transform.reduce` (empty ruleset today — normal form of a chain is itself;
   Loop-expansion rules land here), producing the **render mantle**, then the Scry-side
   resolve walks output→generators and attaches notes/meta → the immutable snapshot
   (the [realtime-boundary](/concepts/realtime-boundary.md) artifact). Pure: reads only,
   installs nothing. `tests/test_render.py` 6/6. Also fixed: config seeding (the C core
   has no `config` verb — meta/transform now seed into state pre-construction; reported
   upstream). *Model → render-graph, off-thread, proven.*
4. **Trivial audio backend → FIRST SOUND.** ✅ **DONE (2026-07-06).** `voidloops/backend.py`:
   a pure-Python additive synth (saw/sine/square/triangle, declick envelope, the tier-3
   output **limiter**) behind `vc.set_effect_handler` — `deploy <path>` bounces the active
   patch to WAV; `preview` renders + plays. The melody is verified **acoustically** in
   `tests/test_sound.py` (zero-crossing pitch detection hears C4-E4-G4-C5) — 5/5.
   *You hear the melody — the no-timeline model proven by ear.*
4b. **Loops as nodes.** ✅ **DONE (2026-07-06, "loops before UI").** The namesake unit is
   real: `add_loop(ref)` drops a mantle in as one node; its ports are the inner graph's
   **free ports** (computed, not declared — the net boundary); the compiler expands
   Loops recursively (cycle-rejecting, notes riding along). Reuse and nesting proven,
   audibly (`tests/test_loop.py`, 7/7). Expansion is a compiler pre-pass until the core's
   general rule LHS lands (see [Loop](/concepts/loop.md)).
5. **Node-editor UI.** ✅ **v1 PROTOTYPE DONE (2026-07-07).** `voidloops/ui.py`: the
   fastest-possible canvas (stdlib HTTP server + one self-contained page, zero deps) —
   typed-wire patch view, **piano roll inside sequencer nodes**, Loop nodes with their
   free ports, patch switcher, **play/bounce buttons**, and a dispatcher command box
   (= full editing through the one verb surface). A pure dispatcher client; explicitly
   throwaway scaffolding (`python -m voidloops --ui`; `tests/test_ui.py` 4/4). The real
   editor (drag-wiring, in-canvas piano-roll editing, enter/exit Loops) replaces the
   page, not the seam. See [own UI](/components/own-ui.md).
> **🏆 PROTOTYPE v1 REACHED (2026-07-07):** the author's six acceptance criteria all
> pass (`tests/test_prototype.py`) — typed node graph, VSTs in-graph, looping MIDI
> sequences, sequence-of-sequences via offsets/repeats/duration, tag-routed FX
> (reverb+limiter, the bus replacement), parallel voices. Desktop launcher:
> `VoidLoops.bat` + the "Void Loops Studio" desktop shortcut.

6. **VST + LMMS harvest.** 🔶 **IN PROGRESS (model side DONE 2026-07-07).**
   Landed: the **category layer in code** (`NodeKind.category` — question #11 decided),
   the **growth kinds** (`sampler`, `sample-in`, `midi-in`, `effect`, `vst-instrument`,
   `vst-effect`, all category-anchored), a **category-driven compiler** (voices pulled
   by taxonomy, not kind lists), and the trivial backend playing **samples** (naive
   repitch from root) and **effects** (gain/delay) — with VST nodes compiling but
   refusing honestly at render. An actual LMMS sample plays through the VLS sampler.
   The **code spike is answered** ([LMMS engine](/components/lmms-engine.md)): harvest
   the **RemoteVstPlugin protocol**, not the engine — VLS-side client = the compute
   holiday. Remaining: that client (drive one real VST), the ogg/flac decode step for
   the sample library, the **sequence node** (design with its UX, question 8's rider),
   and MIDI-file parsing for `midi-in`.

# Planned concepts

* [The node graph](/concepts/node-graph.md) · [Node types & ports](/concepts/node-types.md)
  · [Time without a timeline](/concepts/time-without-timeline.md)
  · [Loop](/concepts/loop.md)
  · [Rules & reversibility](/concepts/rules-and-reversibility.md)
  · [Reverse & reference](/concepts/reverse-and-reference.md)
* [Instrument as holiday](/concepts/instrument-as-holiday.md) · [Effects & routing](/concepts/effect-and-routing.md)
  · [Loops & feedback](/concepts/loops-and-feedback.md) · [Render domain](/concepts/render-domain.md)

# The post-prototype era (2026-07-08 →) — driven by jam-session feedback

The v1 slice shipped; the loop is now *the author makes things → friction becomes the
roadmap* (two feedback rounds already folded). Ordered by decided priority:

1. **The LiteGraph editor rebuild** — ✅ **DONE (2026-07-08, editor v4)**: LiteGraph.js
   vendored (`voidloops/vendor/`, MIT core build, no CDN), the canvas rebuilt on it
   (multi-select, marquee, zoom/pan, type-checked link dragging, searchable add box
   incl. Shift+A), the `/state`+`/cmd` seam and the inspector/piano-roll/library
   panels untouched; kinds register as `<category>/<kind>` types, Loops as
   `loop/<ref>`; `/state` re-sync = auto-repair. Awaiting the author's jam-session
   verdict. See [own UI](/components/own-ui.md).
2. **Widgets as nodes / params as ports** (question #14) — 🔶 **#14a SHIPPED
   (2026-07-08)**: the `control` signal, `p:<field>` param inlets on curated
   numeric fields, utility kinds (`value`/`math`/`map`/`compare` + `time-of-day` —
   the DJ-dynamic input), evaluated once per render (`tests/test_utility.py`).
   Same day: the **`midi` node** (the dedicated piano-roll-window node — #13's
   candidate) and **VST-nodes-as-windows** (native plugin editor + `.fxp` capture).
   **Slider faces ON nodes SHIPPED (2026-07-09)**: curated params + selects as
   LiteGraph face widgets, utility kinds fully widget-faced (`value` = a knob),
   wired params gray out, flush-on-pointer-up (see [own UI](/components/own-ui.md)).
   Remaining (#14b): LFO/envelope (needs per-block eval → item 3), VST params as
   ports, musical presets per effect.
3. **Streaming playback** — block-by-block rendering to the soundcard (play/pause/
   position, live tweaks audible) instead of whole-window bounces; the step toward
   the author's DJ-dynamic sequences. 🔶 **First bite (2026-07-09): live tweaks
   audible** — a param `set` during playback re-renders and resumes in place.
   True block streaming (and per-block control eval → LFO) needs the real engine;
   the pure-Python backend can't render real-time.
4. **VST3 (and CLAP) path** — the RemoteVstPlugin host is VST2-only; most of the
   author's FL plugin list is VST3. Likely a new remote host harvest or bridge.
5. **Sample/file management** — beyond the LMMS library: the author's own sample
   folders as library roots, import/copy policy, per-project sample references.
6. **LMMS native instruments** — TripleOscillator etc. as per-plugin harvests, and
   the 764-file `.ds` **DrumSynth** corpus (a text-defined drum synth engine of its
   own). With credit, per [LMMS engine](/components/lmms-engine.md).
7. **Sequence/sequencer subsumption** (question #13) — decide when the LiteGraph
   editor's piano-roll UX lands.

# The native era (called 2026-07-09) — the real VLS begins

The author, after the 2026-07-09 jam round: the Python VLS *"has been a useful test
version… it's best to move on."* The real application: a different language, a custom
responsive GUI, and libraries with **enough control to log the UI itself** (node
movements included) — or we build those parts ourselves. **Stack decided same day
(#16): C++20** — and the node UI layer became its own project: **Void Maiz**
(`../VoidMaiz`, founded 2026-07-09 as *Void Node*, renamed 2026-07-13; own OKF),
the generalizable node-graph UI library for Void Core apps. The native VLS is
a Void Maiz client; production order = recreate the Python VLS capability,
better, piece by piece, with VLS supplying the glyphs, faces (piano roll),
compile pipeline, and audio engine. What is fixed:

- **Void Core stays the substrate**; the **dispatcher seam stays THE architecture**
  — the native GUI is a thin client exactly like the page was.
- **Engine first, shell second**: the native build starts with the streaming
  block renderer + a native RemoteVstPlugin client behind the same snapshot
  contract `render.py` defines today — the part Python fundamentally cannot do —
  then the ImGui shell replaces the browser.
- **The Python VLS becomes the reference implementation + test harness**: its
  model/compile semantics and 16 green test files are the spec the native engine
  must match, and it stays jam-usable during the port. Maintenance continues
  (bug fixes, capture), new *features* land native-side.
- Items 3–7 above (streaming, VST3/CLAP, sample mgmt, LMMS instruments, #13)
  **migrate into the native build order** — streaming playback is its first
  engine milestone, and VST3/CLAP its second, both natural in C++.

## The native build order (fixed 2026-07-16 — Void Maiz declared ready, the rewrite begins)

Void Maiz shipped phases 1–4 (embed, projection, canvas + gesture grammar,
faces, widget protocol, the reduce-contract port); the author called it ready.
One amendment to "engine first, shell second": with the shell nearly free on
Maiz, **milestone 1 is the shell skeleton** (the integration proof); the
engine keeps its priority as the very next thing. Native code lives in
**`native/`** in this repo; the Python VLS at `voidloops/` stays the reference
implementation. Wire relations go **numeric** in the native model (open
question #17's lean — the reduce contract's `"i:j"` form).

1. **The shell skeleton** 🔶 — `native/`: the VLS glyph set ported from
   `model.py` (Maiz `hints.ports` convention, categories as palette groups,
   params as `p:` control inlets), the starter patch through the dispatcher,
   canvas/inspector/log-strip/command-bar, native project file load/save.
   *Exit test: the starter patch renders, edits, and its transcript replays.*
2. **The importer + parity gestures** — Python-era `.vlp.json` projects load
   (named→numeric relation translation, one-shot); the mouse-only rebuild of
   the starter patch (Maiz phase-3 exit test, run on VLS glyphs).
3. **The compile pipeline port** — `render.py` semantics in C++ (named⇄linear,
   Loop expansion, category-driven voice pull, the snapshot artifact), pinned
   by the Python tests' expectations as the behavioral spec.
4. **The streaming engine** — miniaudio-class device output, block-by-block
   render (play/pause/position, live tweaks, per-block control eval → LFO);
   the realtime boundary holds (audio thread never calls the core).
5. **The native RemoteVstPlugin client** — real VSTs in-graph again; then
   VST3/CLAP (item 4 of the post-prototype list).
6. **The piano-roll face** — VLS's signature face, on Maiz's face API (its
   phase-4 proving face); `midi`/`sequence` editing lands here (#13 decides).

# Deferred / research

* **The live [reverse/reference node](/concepts/reverse-and-reference.md)** — north star;
  needs bounded render + cycle handling. Far off.
* **Confluence under audio feedback** — cycles preserved (opaque agents); a structural
  *semantics* for feedback stays research. See [loops & feedback](/concepts/loops-and-feedback.md).
* **Shared-target effect rewrites** + **data-form `expand`** — core deferred the general
  Reduce LHS; hand-wire for now.
* **CLAP/VST3** beyond the LMMS host; **sample library** as a query-backed holiday.
