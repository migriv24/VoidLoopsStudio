# Log

## 2026-06-27 — Bundle created

- Project conceived: **Void Loops Studio**, a from-scratch pattern DAW (FL Studio /
  LMMS lineage) built on top of [Void Core](/references/void-core.md).
- Read Void Core's SPEC / ARCHITECTURE / interaction-net notes / OKF bundle to ground
  the design.
- Key decisions recorded in the [roadmap](/roadmap.md): base = **LMMS**; integration =
  **fork & gut** (keep engine + VST host, replace model + UI); reducer = **deferred**;
  v1 = model → CLI → engine adapter → minimal UI → sound.
- Identified the governing constraint: Void Core's **drift test** — the audio engine
  computes, the overlay only structures. Captured as the
  [realtime boundary](/concepts/realtime-boundary.md).
- First-author concepts hand-written; remaining concepts left as dangling links
  (planned knowledge) per OKF conformance.

## 2026-06-28 — Core dependencies landed; roadmap made concrete

- Void Core shipped the transformation layers as **three** machines, not one:
  **Reduce / Temper / Scry** (+ materialize) — built, tested, dispatcher-exposed, and
  **authorable as data** (`voidcore.spec`, `config.transform`). The effect handler is
  **bound** (`vc.set_effect_handler`). Verified against the live package
  (`voidcore/__init__.py`, `reduce/`, `temper/`).
- Our forks resolved exactly as requested: cycles preserved via **opaque agents**; pure
  `net→net`; effects only at the holiday boundary. Confirms the
  [realtime boundary](/concepts/realtime-boundary.md) is honored at the core level.
- Renamed the [reducer concept](/concepts/reducer.md) → "the transformation layers" and
  marked the core layers `current`; updated [loops & feedback](/concepts/loops-and-feedback.md),
  [render domain](/concepts/render-domain.md), [effect & routing](/concepts/effect-and-routing.md),
  and the [Void Core spine](/components/voidcore-spine.md).
- Rewrote the [roadmap](/roadmap.md): added a **trivial-audio-backend-first** step so we
  reach first-sound before the LMMS harvest (the effect seam makes the backend swappable).
  The core is no longer the gating factor — remaining work is ours.
- Verdict to the core agent: good stopping point, not blocked. Began readiness for
  build-order step 0 (the `voidloops` app skeleton).

## 2026-06-29 — Build-order step 0 done (first code)

- Scaffolded the `voidloops` Python package: `VoidLoopsProject` wraps `VoidCore` +
  `Dispatcher` and adds JSON state-file persistence (the app's job, not the core's).
- `pyproject.toml`, `__main__.py` demo, `tests/test_smoke.py`, README, `.gitignore`.
- Verified live against the editable `voidcore` + built `libvoidcore.dll`: 5/5 smoke
  tests green (opens on the C core, the Dispatcher superset delegates `mantle`/`rune`/`ls`
  unchanged, undo works, the `scry` transform verb routes, state round-trips through disk
  and a fresh manager). `python -m voidloops` runs end-to-end.
- No DAW model and no audio yet — that's step 1 (glyphs + pattern-mantle) and step 4.

## 2026-06-29 — Build-order step 1 done (the DAW model)

- `voidloops/model.py`: the four DAW glyphs (`note`, `pattern-clip`, `automation`,
  `sample`) with `fields` + documentary `ports`; timing constants + pure conversions
  (ticks↔beats↔seconds); pitch name↔MIDI helpers; provisional reducer `SIGNATURES`.
- **Decided: time is integer ticks** at a project PPQN (default 96), per the author. See
  [note as rune](/concepts/note-as-rune.md). Project meta (ppqn/bpm/time-sig) persists in
  `state.config`.
- `VoidLoopsProject` now re-registers the DAW glyphs on every open (glyphs aren't in
  exported state), seeds project meta, and gained `new_pattern` / `add_note` / `notes`.
  Notes are written with `setjson` (the C core zero-fills glyph `fields` as empty
  *strings*, so typed integers need `setjson`), created atomically as one `batch`/undo
  frame.
- `tests/test_model.py`: 7/7 green — glyphs registered, pitch helpers, integer-typed
  content, a C-major arpeggio that `validate`s clean, tag selection (`track:lead`/`bass`),
  meta + timing (quarter note @120 BPM = 0.50 s), disk round-trip (notes + meta survive).
  Step-0 smoke still green. `python -m voidloops` prints the arpeggio with beat/second
  positions.
- Next: step 2 — author Temper rules + selectors as **data** (`config.transform`).

## 2026-06-29 — MAJOR PIVOT: timeline → node graph

- The author chose to abandon the **arrangement timeline** and make Void Loops a fully
  **node-based DAW** (dataflow / patching, modular-synth lineage: Max/PD/Reaktor/VCV), at a
  *coarse, musical* node granularity (sample / MIDI / VST / effect / mix / output) — not
  Pure-Data primitives. No middle ground; the timeline is removed outright.
- Why it's a *better* fit, not a detour: a node graph **is** an interaction net, so all of
  Void Core's machinery (ports, holidays, cycles, the reducer) applies directly — the
  timeline had been fighting the engine's native shape.
- Resolved the author's open puzzles, each captured as a concept:
  - **time ≠ timeline** → [time without a timeline](/concepts/time-without-timeline.md):
    time stays, generated by clock/sequencer nodes; ticks survive as their output.
  - **the rules intuition** → [rules & reversibility](/concepts/rules-and-reversibility.md):
    three tiers (structural invariant / total-reversible algebra / lossy boundary policy).
    **Negative note length = time reversal** — keep it, don't forbid it.
  - **the reverse-clip dream** → [reverse & reference](/concepts/reverse-and-reference.md):
    a live render-reference node; the original motivation for the whole project.
- Decisions: engine = **harvest LMMS for DSP + VST hosting** (VST is a priority), driven as
  a graph; first sound = **Sequencer → Osc → Output**; keep integer ticks (not fully
  continuous).
- OKF surgery: NEW [node graph](/concepts/node-graph.md), [node types](/concepts/node-types.md),
  [time without a timeline](/concepts/time-without-timeline.md),
  [rules & reversibility](/concepts/rules-and-reversibility.md),
  [reverse & reference](/concepts/reverse-and-reference.md),
  [group node as mantle](/concepts/group-node-as-mantle.md). Rewrote effects/routing,
  daw-architecture, note-as-rune, render-domain, lmms-engine, own-ui, the glossary, and the
  vision. **Deprecated** [pattern as mantle](/concepts/pattern-as-mantle.md) and
  [arrangement](/concepts/arrangement.md). Reset the [roadmap](/roadmap.md) to a node build
  order; noted what carries over from steps 0–1 (most of it).
- Code: steps 0–1 stand; no new code this turn (OKF realigned first, per the design-first
  discipline). Resume at the new step 1 (node glyphs + wiring) next.

## 2026-06-29 (later) — visual viewer, dev-questions, Wikipedia reading; Void Core re-sync

- **Void Core re-sync:** the **`reduce` dispatcher verb is now built** (authorable as data
  via `config.transform.reduce`); the holiday concept names **compute** + **output** kinds
  (so the audio backend splits cleanly — VST = holiday, render = output holiday); the layers
  are leading-words **Scry/Temper/Reduce** and "**seam**" is preferred over "boundary." No
  breaking API changes (import surface identical). Folded into
  [instrument as holiday](/concepts/instrument-as-holiday.md) + [render domain](/concepts/render-domain.md).
- **Visual viewer:** reused Void Core's OKF viewer (`okf/viz/build.py` shim → Void Core's
  `holidays/okf/viz.py`) to generate a self-contained `okf/viz/index.html` (rebranded to
  Void Loops Studio). 24 concepts, 147 links. Gitignored (a build artifact); one-command
  rebuild.
- **[developer_questions.md](/developer_questions.md):** new bundle-root concept — a living
  log of open decisions, each with a lean + links to the affected concept(s).
- **Wikipedia further-reading** added to the concept-dense docs (node graph, time, rules &
  reversibility, reverse & reference, loops & feedback, instrument as holiday) — clearly
  marked external background, never substituting for the project's own explanation; paren'd
  URLs percent-encoded so the viewer's link parser doesn't choke.

## 2026-07-01 — Void Core reorg re-sync; viz retired for FaultSack

- **Re-read Void Core's OKF** (now the single source of truth): the core went through an
  isolation/self-describing cleanup. `notes/` is gone (absorbed into `okf/design/`); the
  GUI/server layer + `createServer` were removed (hosts own their UI — new
  `okf/concepts/ui-ux.md`); the OKF `viz/` viewer + `serve` subcommand were removed (bundles
  are now studied in FaultSack; the OKF engine exposes the bundle as data:
  `ls`/`get`/`query`/`validate`/`analyze`). **No change to our integration** — the dispatcher
  contract, verbs, Voidscript, and the C ABI are byte-for-byte identical (internals were just
  split into modules).
- **Retired our `okf/viz/`** shim (it pointed into Void Core's now-deleted OKF viewer, so it
  was already dead) and its references. Visual study of this bundle now goes through
  **FaultSack** (`../FaultSack`) — a Void Core app that builds
  a unified concept+code graph, ranks "what's most responsible" by centrality (a **module
  map**), and adds a developer-notes critique-and-export flow. Higher altitude than the old
  status-colored reader.
- Fixed two stale core links the reorg broke in [okf-spec.md](/references/okf-spec.md): the
  `viz.html` viewer reference and the `notes/okf.md` rationale pointer (→ `okf/design/okf-design.md`).

## 2026-07-01 (later) — node build-order step 1 done (node glyphs + ports + wiring)

- First code since the pivot. `voidloops/model.py`: the v1 **node glyphs** with typed **port
  signatures** — `clock` (→clock), `sequencer` (clock→events), `osc` (events→audio), `mix`
  (many audio→audio), `output` (audio→∅) — via a `Port`/`NodeKind` model that also emits each
  glyph's documentary `ports` metadata to the core. Three **signal types** (audio/events/clock).
  See [node types & ports](/concepts/node-types.md).
- **Retired the `pattern-clip` glyph** (the last timeline-era artefact) from the registered set,
  per the pivot; `note`/`automation`/`sample` remain as *content* glyphs (things inside a node).
- `VoidLoopsProject` gained the node-graph surface: `add_node(kind, **content)` (fields
  validated against the glyph; numbers typed via `setjson`, strings via `set`), `wire(src, dst)`
  (**type-checked**: outlet/inlet signal types must match; a non-`multi` inlet rejects a second
  wire; ports default to the sole port), and `nodes()`/`wires()` readers. A **wire is a core
  `link`** whose `relation` encodes `signal:src_port->dst_port`; port-type enforcement lives in
  the app (core links stay untyped/dangling-tolerant). See [effects & routing](/concepts/effect-and-routing.md).
- Verified live against the C core: **new `tests/test_nodes.py` 8/8 green** (glyphs registered,
  typed node content, type-mismatch + double-single-inlet rejection, `mix` multi-inlet, a
  `clock→sequencer→osc→output` chain that `validate`s clean, disk round-trip of nodes+wires).
  `test_model.py` updated (pattern-clip now asserted absent) — model 7/7, smoke 5/5 still green.
  `python -m voidloops` prints the first-sound node graph and validates it.
- Next: step 2 — build `sequencer → osc → output` as a patch whose sequencer *holds* the step-1
  note-runes ([group node as mantle](/concepts/group-node-as-mantle.md)), proving the graph
  round-trips with real musical content.

## 2026-07-06 — First FaultSack review round applied (snap_3af48cd28f2f)

The author studied the project in FaultSack and returned the first exported notes batch —
the tool's critique flow working end-to-end. Everything folded in:

- **The Loop.** Renamed *group node as mantle* → **[Loop](/concepts/loop.md)** (the author:
  the old title wasn't a noun to build on; name chosen with the author). The app's namesake
  unit: a sub-graph of nodes used as one node. All living links repointed; disambiguated
  from [loops & feedback](/concepts/loops-and-feedback.md) (cycles).
- **Dev-questions 1–7 all answered** (via the notes; 6 & 7 delegated) and folded:
  compute-holiday = the VST starting point, holidays framed as *generators* (#1); MIDI
  survives as **mini-timelines inside nodes** + the "sequence node" sketch (#2); v1 five
  confirmed (#3); **graph-flatten = data-authored Reduce rules** — the interaction-net
  spirit outranks efficiency (#4, reverses the hand-write-first lean; roadmap step 3
  updated); wire typing **strict now, emergent interactions as a future feature** (#5);
  modulators as params / far-horizon nodes-as-preset-Loops (#6); UI toolkit deferred,
  fastest throwaway canvas at step 5 (#7). [developer_questions.md](/developer_questions.md)
  now lists refined remainders (#8–10).
- **Music-first boundary** recorded in the [vision](/references/voidloops-vision.md): VLS is
  for music/audio production; visuals may come but never take over — the ambitious visual
  work belongs to a planned **TouchDesigner/Cables-lineage sister app** working closely
  with VLS. Also: **negative-length reversal demoted** to "a nice consequence, not the main
  thing" in [rules & reversibility](/concepts/rules-and-reversibility.md).
- **[LMMS engine](/components/lmms-engine.md):** the harvest now explicitly includes LMMS's
  **sound/sample/preset libraries and native synths**, with prominent **credit** to
  github.com/LMMS/lmms + lmms.io.
- **[Own UI](/components/own-ui.md) rewritten** for the core reorg: the "reuse Void Core's
  server/GUI spine" option is dead (that layer was removed; hosts own their UI), and the
  page now *describes the UX* per the core's new ui-ux concept.
- **[The layers](/concepts/reducer.md) slimmed** to VLS's use only — core detail repointed
  to Void Core's own OKF (the author: core aspects shouldn't be re-documented here).
- **[Note as rune](/concepts/note-as-rune.md):** future-possibility noted — net-aware
  custom VSTs (sound responding to the harmony around a note).
- **Message upstream:** the holidays-as-generators framing addressed to the Void Core
  agent, drafted at `MESSAGE_FOR_VOIDCORE.md` (repo root) for the author to relay.

## 2026-07-06 (later) — Questions 8–10 answered; the fundamental node taxonomy

The author answered the refined batch inline. Folded:

- **NEW concept: [the fundamental node taxonomy](/concepts/node-taxonomy.md)** (dev-answer 8).
  No node is elemental — a **category layer** (input / time-event / generator / transform /
  combine / utility / Loop / output) that kinds *inherit* port conventions and behaviors
  from, in the lineage of Blender's geometry-node categories ("the important thing isn't
  that we use this format — it's that we understand where it came from"). The **Blender
  thought experiment** ("what if VLS were built into Blender's nodes — sound as a unit of
  motion?") yields the design rule: **categories are domain-agnostic; signal types carry
  the domain.** Keeps the door open to the visuals sister app and the wider
  rebuild-Blender-on-Void-Core program via cross-domain wires.
- **The render mantle** (dev-answer 9, delegated → decided): generated sound *is* a
  separate mantle — the flattened snapshot is now named the **render mantle**, holding
  generated description-runes with provenance; sample buffers never become runes
  implicitly (drift test); **materialize** is the one crossing into owned runes; speaker
  safety stays a tier-3 boundary limiter, never mantle math
  (→ [render domain](/concepts/render-domain.md)). Also resolves "a note is not one
  thing": note-rune in the arrangement mantle ↔ sounded rune in the render mantle,
  related by the compute holiday.
- **The growth node set** (dev-answer 10, delegated → decided): v1 five unchanged;
  second wave at step 6, category-anchored — `midi-in`, `sample-in`, `sampler`,
  `vst-instrument`, `effect`, `vst-effect`, the sequence node (likely subsuming
  `sequencer`), utilities as needed (→ [node types](/concepts/node-types.md)).
- [developer_questions.md](/developer_questions.md): 8–10 moved to decided; one new open —
  **#11: formalize category inheritance in the glyph system** (lean: an additive
  `category` field on `NodeKind` at the VST step).

## 2026-07-06 (evening) — FIRST SOUND. Build steps 2–4 done; design locked

The author locked the OKF ("lock in our current plans") and we ran the first-sound slice
end to end. **Void Loops Studio makes sound.**

- **Step 2 — a patch as a graph.** The sequencer *holds* its note-runes via the
  `node:<seq>` containment tag (first-class, tag-selectable, exactly the
  [Loop](/concepts/loop.md) story at v1 scale). `add_note(node=)` / `notes(node=)`;
  notes only live in sequencers; one-undo-frame creation; disk round-trip.
  `tests/test_patch.py` 6/6.
- **Step 3 — the graph compile, data-authored.** `voidloops/render.py`: the named-port
  graph converts to the reducer's linear `"i:j"` form (a `multi` inlet allocates a fresh
  index per wire; fan-out from one outlet deferred with a clear error), Void Core's
  Reduce runs with the spec from `config.transform.reduce` (seeded as data, persisted
  with the project; ruleset empty until Loop-expansion), yielding the **render mantle**;
  the Scry-side resolve walks each output back to its generators and attaches notes +
  tick→second timing → the immutable **snapshot**. Pure (reads only, installs nothing),
  deterministic. `tests/test_render.py` 6/6.
- **Step 4 — FIRST SOUND.** `voidloops/backend.py`: a stdlib-only additive synth
  (saw/sine/square/triangle, 5 ms declick, and the tier-3 output **limiter** — the Q9
  speaker-safety constraint made real) bound behind `vc.set_effect_handler`. `deploy
  <path>` bounces the active patch to WAV; `preview` renders + plays; `python -m
  voidloops --play` plays the demo arpeggio. The test *hears* the melody: zero-crossing
  pitch detection confirms C4-E4-G4-C5 within 6 %. Boundary policy exercised: zero/
  negative-length notes are skipped by *this backend* (legal in the model; reversal is a
  future backend's job). `tests/test_sound.py` 5/5.
- **Latent bug fixed (found by step 3):** the C core has **no `config` verb** (SPEC lists
  one), so step-1's `config set` meta seeding had been failing silently behind the
  defaults fallback. Meta + the transform spec now seed into `state.config` *before*
  manager construction; a saved project file really contains them (regression-tested).
- **Upstream reports** appended to `MESSAGE_FOR_VOIDCORE.md`: the `&`-in-tag-expression
  **access-violation crash**, the missing `config` verb (SPEC conformance gap), and
  `from_net` dropping tags.
- Suite: **32/32 across six test files** (smoke 5, model 7, nodes 8, patch 6, render 6,
  sound 5 — step-1 nodes file counts 8 with roundtrip). Next: **step 5, the node-editor
  UI** (fastest throwaway canvas), or deepen the model (Loops as nodes, step 2 of the
  concept) — author's call.

## 2026-07-06 (night) — Loops as nodes ("loops before UI", the author's call)

The namesake unit is built. A **[Loop](/concepts/loop.md)** = a whole mantle used as one
node, and the mechanism is deliberately net-theoretic:

- **Ports are computed, not declared.** A Loop node's inlets/outlets are the **free
  (unwired) ports** of its referenced mantle's graph, qualified `<inner>.<port>` — a
  sub-net's interface *is* its free ports (Lafont). `add_loop(ref)` +
  `loop_ports(node)` in `voidloops/project.py`; `wire()` resolves and type-checks
  through the boundary exactly like any port (sole-port defaulting included).
- **Compile expands.** `_expand_loops` in `voidloops/render.py` splices the referenced
  graph in (names prefixed `<loop>/`), re-anchors boundary wires onto the inner free
  ports, recurses for nested Loops with a **cycle guard** (`a→b→a` rejected; direct
  self-drop rejected at `add_loop`), and carries each spliced sequencer's **notes**
  along from its home mantle. Then the existing pipeline runs unchanged: index-form →
  data-authored Reduce → render mantle → snapshot → sound.
- **Reuse works** — two Loop nodes referencing one mantle yield two voices playing the
  same notes (`loop1/osc1`, `loop2/osc1`): the "pattern used twice" story, no clip
  mechanism needed. **Nesting works** — a Loop containing a Loop expands to
  `outer/inner/osc1` with doubly-qualified boundary ports.
- **Honesty note:** expansion is a compiler **pre-pass**, not a Reduce rewrite — the
  core's rules fire on active pairs and a passive container never forms one; boundary
  splicing needs the deferred general LHS. Exactly dev-answer 4's "hand-wire only that
  gap"; it migrates into the ruleset when the core grows the form.
- `tests/test_loop.py` **7/7** (ports, typed boundary wiring, expansion w/ notes, reuse,
  nesting, cycles, round-trip + audible render). Full suite now **39/39 across seven
  files**. Next: **step 5 — the node-editor UI**, which now has Loops to draw.
- **`MESSAGE_FOR_VOIDCORE.md` rewritten as a full handoff brief** (the core's handoff
  protocol: From/To/Ask + reply checklist, in the transform-layers-handoff format):
  status report (first sound on the core, surfaces exercised), the three bug reports
  (`&` crash / missing `config` verb / `from_net` drops tags), four ranked wants (config
  verb; a container-expansion rule form with our Loop pre-pass as the ready-made use
  case; the crash fix; optional named-port `to_net`), the author's holidays-as-generators
  question (§4), suggested skills, and a reply checklist. Reply channel: via the author,
  or `MESSAGE_FOR_VOIDLOOPS.md` in our repo root.

## 2026-07-07 — Core 0.2.2 absorbed (all our bugs closed); UI prototype = v1 slice COMPLETE

Void Core replied (`MESSAGE_FOR_VOIDLOOPS.md`): the `&` crash fixed (root cause: a
tokenizer that never terminated — a lone `&` is now one never-matching tag atom, oracle
parity), **the `config` verb landed** (no undo frame — session meta by contract),
`from_net` carries tags, `where` returns structured data, and **our Loop expansion is
the named reference case for the general-LHS design**. Actions taken:

- **Verified every claim live** against the rebuilt DLL, then built **`set_meta`** on the
  real verb — the BPM knob: `set_meta(bpm=140)` mid-session, undo history untouched
  (pinned from the consumer side in `test_model.py`). `_active_mantle` now prefers
  structured `where` data (text fallback kept). Retired the rebuild-with-patched-state
  idea; seed-before-construct stays for open-time defaults.
- **Their three asks answered** in the reply (`MESSAGE_FOR_VOIDCORE.md`, replaced):
  (1) 34 filter-grammar edge probes, zero crashes, four semantics flagged for deliberate
  pinning (lone `!` matches all vs lone `&&`/`||` match none; dangling operators; `()`
  vs empty; quote-stripping happens at the CLI layer); (2) the config soak report —
  **09-config held, 44/44**; (3) `_expand_loops` + `tests/test_loop.py` now carry the
  reference-semantics CONTRACT comment. Plus one loose end found: **`vc_version()` still
  hardcodes "0.2.1"** (`vc_manager.c:157`) while the `version` verb says 0.2.2.
- **Step 5 UI prototype built** (`voidloops/ui.py`, dev-answer 7's "fastest throwaway
  canvas"): stdlib HTTP server + one dependency-free page; a **pure dispatcher client**
  (`/cmd` is the only mutation path). Typed-wire canvas, **piano roll inside sequencer
  nodes** (negative-length notes drawn red), Loop nodes dashed with computed free ports,
  patch switcher, play/bounce across the effect seam, and a dispatcher command box (full
  editing power for free). `python -m voidloops --ui`. `tests/test_ui.py` 4/4.
- Suite: **44/44 across eight files**. **The v1 first-sound slice (steps 0–5) is
  complete**; remaining: step 6 — the VST + LMMS harvest (compute holiday, sound
  libraries with credit, the sequence node, taxonomy revisit).

## 2026-07-07 (later) — Step 6 model side done: categories in code, samplers & effects audible; LMMS spike answered

The author chose to move straight into step 6 (the upstream message was dropped as
unnecessary). Two tracks ran together:

- **The taxonomy landed as code** (question #11, decided exactly on its lean):
  `NodeKind.category` + `holiday: bool` (`voidloops/model.py`), all kinds anchored —
  and the compiler is now **category-driven** (`_pull_generators` walks GENERATOR /
  INPUT / COMBINE / TRANSFORM, not hardcoded kind lists), so new kinds slot in without
  compiler edits. The taxonomy stopped being documentation and started paying rent.
- **The growth wave** (dev-answer 10, minus the sequence node — deliberately deferred
  to a design session with its UX, now open question #12): `sampler` (events + sample
  inlets; naive root-relative repitch), `sample-in` (raw source; also a voice when
  wired bare), `midi-in` (glyph only; file parsing later), `effect` (native `gain` +
  `delay` with feedback, applied per-voice along the route), `vst-instrument` /
  `vst-effect` (compile as voices/transforms; **refuse honestly at render** until the
  LMMS backend exists). Snapshot voices grew `sample` + `effects`. Backend restructured
  per-voice → effect chain → sum → output gain → limiter; delay tails extend the
  render. `tests/test_growth.py` **6/6**, all audible assertions.
- **The LMMS code spike is answered** (shallow clone at `Projects/lmms`; findings in
  [LMMS engine](/components/lmms-engine.md)) and it *revises the plan favorably*:
  LMMS already hosts VSTs **out-of-process** (`RemoteVstPlugin` exe ↔ shm + socket
  protocol), so the clean seam is the **wire protocol, not the engine** — VLS writes a
  small client speaking it (that client *is* the compute holiday); `AudioEngine` can
  wait; native instruments are per-plugin cherry-picks. "Fork & gut" softens to
  **protocol-first, engine-later**.
- **First literal harvest:** `data/samples` (7.6 MB) + `data/presets` (11 MB) surveyed
  (764 DrumSynth `.ds`, 181 ogg, 33 flac, 26 wav) — and an actual LMMS sample
  (`shapes/additive.wav`) **played through the VLS sampler live**. ogg/flac need a
  decode step at the library boundary; licensing (GPLv2) checked per-item at
  redistribution time.
- Suite: **50/50 across nine files**. Next: the remote-VST client spike (drive one real
  plugin through the protocol), then the sequence-node design session (#12).

## 2026-07-07 (evening) — Harvest boundaries live: LMMS drums + MIDI files play; VST client unblocked

- **The decode boundary** (`backend._load_sample`): non-WAV samples (ogg/flac/mp3 —
  most of LMMS's library) decode through **ffmpeg** piped at the host boundary (the
  model never sees codecs), memoized; honest errors on garbage input. **A real LMMS
  bass drum (`drums/bassdrum01.ogg`) plays four-on-the-floor through the VLS sampler**
  — the drum library (181 oggs) is usable *now*.
- **`midi-in` is a real node** (`voidloops/midi.py`): a stdlib SMF reader (format 0/1,
  running status, vel-0 note-offs, multi-track merge) feeding the resolve stage.
  Import policy (boundary decision): **the project owns tempo** — SMF tempo events are
  ignored; musical positions survive exactly via the division→PPQN rescale. Unclosed
  notes get one beat; CC/bend skipped until automation lands.
- **The RemotePlugin wire protocol is mapped** into [LMMS engine](/components/lmms-engine.md):
  win32 transport = LMMS's own shm ring-buffer FIFO + two system semaphores, keys via
  argv; handshake (`IdVstLoadPlugin`/`IdInitDone`), the audio shm block
  (`IdChangeSharedMemoryKey`), and the render loop (`IdMidiEvent` →
  `IdStartProcessing` → `IdProcessingDone`). Conclusion: **the VLS client can be pure
  Python (ctypes)** — no C++ build on our side.
- **The exe prerequisite cleared:** LMMS installed via winget →
  `Program Files/LMMS/plugins/RemoteVstPlugin.exe` exists; real VST2s to host are
  already on the machine (OTT). Caveat noted: match the client to the *installed*
  exe's protocol vintage (stable ≠ master headers).
- Suite: **54/54 across ten files**. Next: the Python RemoteVstPlugin client
  (the compute holiday, end-to-end with OTT), then the sequence-node session (#12).

## 2026-07-07 (night) — A REAL VST RUNS INSIDE VLS. The compute holiday's transport is live

The author asked about code volume (answer: ~1.7k app lines + ~1.3k tests, because the
model machinery is Void Core's and the compute mass is harvested — the thesis working);
then the biggest remaining unknown fell:

- **`voidloops/vsthost.py`** — the pure-Python (ctypes) client for LMMS's
  `RemoteVstPlugin`. Matched to the installed **1.2.2** exe by fetching the stable-1.2
  headers (Qt-5 kernel objects; master's Qt-free rewrite differs!). Implements: Qt's
  `makePlatformSafeKey` name mangling (prefix + letters-of-key + SHA1 hex), the
  shm-FIFO struct (32-byte `sem32_t` unions; start/end ptrs at +64/+68; 512 KiB ring
  at +72), lock-depth semantics, string-typed message framing (`id, argc,
  (len,bytes)*` under the data semaphore + one message-semaphore release), free-key
  allocation (Qt's counter dance), the float audio shm announced via
  `IdChangeSharedMemoryKey`, and the block loop. One startup gotcha found live: 1.2's
  exe demands a **third argv — the embed method** (`headless` for us).
- **Verified with a real commercial plugin:** Xfer Records **OTT** (`XfTT`, v1260)
  loads inside `RemoteVstPlugin.exe`, reports 2-in/2-out, **processes stereo audio
  blocks**, accepts MIDI events, and shuts down cleanly — all driven from Python, no
  C++ built anywhere on our side. `tests/test_vsthost.py` (skip-tolerant when the exe
  or dll is absent).
- Suite: **61 tests across eleven files, all green.** Next slice: wire `vsthost`
  behind the `vst-instrument`/`vst-effect` glyphs in the backend (per-note MIDI
  scheduling + block streaming through the plugin), then the sequence-node design
  session (#12).

## 2026-07-07 (late night) — 🏆 PROTOTYPE v1: all six of the author's criteria pass

The author set the v1 acceptance list; every item is now a passing test
(`tests/test_prototype.py`):

1. **Node graph properties** — typed ports reject bad wires; every kind
   category-anchored; Loop ports computed from free ports.
2. **VSTs load and shape sound** — `vst-effect`/`vst-instrument` are wired into the
   render backend: instruments get per-note MIDI scheduling (note-on/off at frame
   offsets) + silent-input block streaming; effects stream the voice buffer through
   the plugin with a decay tail. Audio verifiably passes *through OTT* in-graph.
3. **MIDI sequences + looped sounds** — **looping is the default posture** (as
   time-without-timeline always said): a sequencer's `length`/`offset`/`repeat`
   content loops its figure to fill the output node's **`duration`** window
   (repeat unset = fill; a one-shot is repeat=1).
4. **Sequencing sequences** — offsets/repeats compose arrangements as *node
   content* ("A loops from bar 0; B enters at bar 2, once") — exactly the seam a
   future input (time-of-day, a DJ surface) can drive, per the author's intent.
5. **Tag-routed FX (the bus replacement)** — `tag_node("osc1", "drums")` +
   `add_fx_rule("drums", type="reverb", amount=.5)`: the rule (data, persisted in
   `config.fx_rules`) lands its effect on every voice whose generator/route carries
   the tag. Native **reverb** (Schroeder: 4 combs + 2 allpasses, real tail) and
   **limiter** effect types added alongside gain/delay.
6. **Parallel music generation** — three looping melodies stacked through one mix,
   three simultaneous voices, audibly summed.

War stories worth keeping:
- **The denormal crash.** Plugins decaying to silence **killed the 1.2-era remote
  host** (~0.4–1 s after signal stopped; input dither and DC floors didn't save it —
  the plugin's *internal* state denormalizes). Fix: the classic DAW-host trick — a
  **nyquist-frequency guard buzz at −80 dBFS** mixed into every VST input block
  (verified: 500 blocks clean), plus **graceful degradation** (a plugin death mid-
  render keeps the audio so far / falls back dry — a crashed FX never nukes a bounce).
- **Two CLI-tokenizer quoting fixes:** string content with spaces (plugin paths!) now
  double-quoted in `set`; JSON config values (fx rules) single-quoted (double quotes
  survive inside, same as `batch`).
- `IdMidiEvent` is **five ints** in 1.2 (type, channel, p0, p1, frame offset) — fixed.
- **Desktop launcher:** `VoidLoops.bat` + a Desktop shortcut ("Void Loops Studio",
  imageres icon) → opens the canvas UI.
- Suite: **67 tests across twelve files, all green.** The prototype's remaining
  wants: the sequence-node design session (#12), LMMS native-instrument harvests,
  and the real editor UI — all *post-prototype* work now.

## 2026-07-08 — First user feedback round: the SEQUENCE node, the sound library, UI v2

The author clicked the icon: "we actually need a usable UI… the play button doesn't
even work… nodes don't have labeled ports." Plus: sequence node and LMMS instruments.
All three delivered:

- **The sequence node** (question #12, designed + built): the sequencer generalized
  with a pluggable **`arr` arrangement inlet** (events, multi) — the author's
  dev-answer-2 sketch made real. It merges its own inline notes with every arr source
  (a `midi-in` file, a `sequencer`, **another `sequence` — sequences of sequences,
  literally**), then applies `length`/`offset`/`repeat`/**`transpose`** (the first
  "sequence as a variable" control). Children expand one pass; only the chain's top
  fills the render window; event cycles are structurally refused. `sequencer` stays
  as the simple case (subsumption open). `okf` note: the arrangement inlet is exactly
  where a future dynamic source (time-of-day, a DJ surface) plugs in.
- **The sound library** (`voidloops/library.py`): LMMS's `data/samples` indexed and
  searchable (`search("kick")`, categories, stable refs like `drums/bassdrum01`);
  `add_instrument(ref)` drops a wired sample-in→sampler pair into the patch. Credit
  to the LMMS community rides in the module and the UI footer.
- **UI v2** (`voidloops/ui.py` rewritten; still one dependency-free page): **labeled
  typed ports**, add-node palette (kinds by category + Loops of other patches),
  **drag** (positions persist per patch), **click-to-wire** (type-checked, errors
  surface), an **inspector** (params, tags, delete, *enter a Loop*, and a notes
  editor for sequencer/sequence), the **library browser** panel, a dispatcher command
  bar — and the **play button actually works now**: the page renders across the
  effect seam and plays the WAV in a browser `<audio>` element (`GET /wav`), no
  server-side speakers involved.
- **The desktop icon opens a real project now**: `~/Documents/VoidLoopsProjects/
  default.vlp.json` (starter patch on first run, saved on exit) — not the temp demo.
- Fixes en route: port-hint names the actual kwarg (`dst_port`); UI errors always
  land in the log pane. Suite: **71 tests across thirteen files, all green.**

## 2026-07-08 (later) — UI v3: the real editor investment ("so bad I can't even connect nodes")

The author's verdict on v2 was unambiguous: sound works, CLI works, but the UI blocked
music-making entirely — click-click wiring didn't communicate, and "everything's a text
field." v3 is the first *real* editor investment (same architecture: one dependency-free
page, a pure dispatcher client):

- **Drag-to-wire**: press an outlet, drag a live dashed rubber-band, drop on an inlet —
  compatible inlets light up while dragging, hit targets grew to 12 px, cursors change,
  and the hint bar narrates. **Wires are selectable** (click the curve) and **Delete
  removes them** (Delete on a selected node deletes it too, with its wires).
- **Typed field editors** driven by per-kind metadata served in `/state.field_ui`:
  dropdowns for `osc.wave` (saw/sine/square/triangle), `effect.type`
  (gain/delay/reverb/limiter), **VST plugin pickers** fed by `/vsts` (scans the VST2
  dirs — OTT and FL Studio VSTi discovered), Loop `patch` refs as a mantle dropdown,
  numbers as number inputs with steps and inline hints, and **sample paths get a
  "library…" picker** (click a sound in the library panel to assign it — fields store
  portable library refs; the backend resolves refs at load).
- **A real clickable piano roll** in the inspector for sequence/sequencer nodes:
  16th-note grid, black-key shading, C-row labels, click to add (note-length selector:
  1/16–1/2), click a note to remove, octave scrolling.
- **Toolbar**: undo/redo (the dispatcher's own), a **live BPM box** (`set_meta` over
  `/meta` — the config verb earning its keep), play/stop/bounce.
- Suite: **71/13 green** unchanged (endpoints stable). This closes "throwaway": the
  page is now the seed of the real editor; what remains UX-wise is polish + the full
  node-design pass (okf/components/own-ui.md's long-term section).

## 2026-07-08 (night) — Second feedback round: fan-out, the author's own VSTs, sliders, Shift+A

Field report from real use (the author tried to jam and hit walls). Everything
actionable landed:

- **Fan-out compiles now** (the top blocker: "wasn't able to attach a sequence source
  to a sample" — one sequence feeding sampler *and* VST). Outlets get per-wire
  synthetic indices like multi-inlets; the bands encode the side ([1000,2000) out,
  [2000,3000) in) so direction survives the reduce round-trip. Verified live: **an
  LMMS bassdrum and the author's own Sonatina Choir VST playing the same sequence
  simultaneously.**
- **VST discovery v2**: search paths mirror the author's FL plugin manager (incl.
  `Documents/Image-Line/CustomVSTs` and FL's VST dir), **recursive** (found Sonatina
  Choir in a vendor subfolder), with **PE-header bitness detection** → the client
  auto-picks `RemoteVstPlugin32.exe` for 32-bit plugins (the "bad dll format" fix).
  The picker shows bits. VST3/CLAP remain unloadable (RemoteVstPlugin is VST2) — noted.
- **Every editor action echoes as CLI in the terminal** (`proj.echo`): the author can
  narrate what they did, and the transcript doubles as CLI-improvement evidence.
- **Sliders**: numeric fields with ranges render slider+number pairs (gain 0–2,
  amount 0–2, feedback 0–0.95, tuning/transpose ±24, root 0–127).
- **Shift+A** (the Blender gesture): searchable add-menu at the cursor; the node lands
  where the menu opened. Piano roll: forgiving column-overlap hit detection,
  **right-click always deletes**, a clear button.
- New open questions from the author's direction-setting: **#14 widgets-as-nodes /
  params-as-ports** (ties to dev-answer 6's promote-modulators) and **#15 adopt an
  open-source node-graph front end** (LiteGraph.js lean; study Blender's design
  philosophy first). Suite: **13 files green** (fan-out test flipped to assert the
  capability).

## 2026-07-08 (capture round) — LiteGraph decided; the OKF trued up to shipped reality

The author confirmed **#15: LiteGraph.js** ("yes! litegraph!") and asked for a full OKF
capture before the next session. Done:

- **#15 → decided**: vendor LiteGraph.js (self-contained, no CDN), rebuild the canvas
  layer on it, keep the dispatcher-client seam page-only, study Blender's UI
  philosophy during the port. [Own UI](/components/own-ui.md) rewritten around the two
  permanent commitments (the seam; every action a visible CLI action) + the migration
  plan; the throwaway era is formally over.
- **Roadmap gained the post-prototype era** (jam-feedback-driven, ordered): LiteGraph
  rebuild → widgets-as-nodes (#14) → streaming playback → **VST3/CLAP path** (the
  author's FL list is mostly VST3; our host is VST2-only) → sample/file management
  (author's ask) → LMMS native instruments + the `.ds` DrumSynth corpus → #13.
- **Concept statuses trued to shipped code**: [node types](/concepts/node-types.md)
  (full working set incl. sequence node + fan-out), [effects & routing](/concepts/effect-and-routing.md)
  (tag-routed FX + reverb/limiter built; shared-bus instances still deferred),
  [instrument as holiday](/concepts/instrument-as-holiday.md) (**the compute holiday
  is real** — vsthost + library), [time without a timeline](/concepts/time-without-timeline.md)
  (looping default shipped; literal clock pulses await streaming),
  [index](/index.md) status block (prototype shipped, iterating on real use).

## 2026-07-08 (later) — editor v4: the canvas rebuilt on LiteGraph.js

Post-prototype item 1 shipped, in one sitting. `voidloops/vendor/` now holds the
**LiteGraph.js core build** (MIT, license alongside; the *core* build on purpose —
the full build ships ~200 demo node types that would pollute our add menu). The page
moved out of the Python string into `voidloops/editor.html`; `ui.py` (v4) is just the
dispatcher-client server plus `/vendor/*` (whitelisted) and a richer `/state` (kind
port specs; `multi` flags ride on ports only when true, keeping the historical shape).

The mapping that makes it ours:

- Kinds register as LiteGraph types named **`<category>/<kind>`** — the
  [taxonomy](/concepts/node-taxonomy.md) literally structures the add menu. Loops
  register per-mantle as `loop/<ref>`; double-click a Loop enters its patch.
- **`/state` stays the single source of truth**: the page rebuilds the LiteGraph
  graph after every mutation, so a server-rejected edit (cycle, occupied inlet, type
  clash) just vanishes — the auto-repair the author asked for, free. LiteGraph's own
  serialization is never used; the model lives in Void Core.
- Our signal types are LiteGraph slot types → type-checked link dragging in-canvas,
  in our colors. **Multi inlets** grow one spare slot per sync so fan-in is always
  droppable. Gestures emit POSTs through a promise queue so the **CLI echo matches
  click order** (commitment 2 intact). Shift+A now opens LiteGraph's searchable add
  box at the cursor; multi-select/marquee/zoom-pan/Delete/Ctrl+A come with the canvas.
- Carried over untouched: inspector, piano roll, library browser, patch switcher,
  undo/redo, BPM, browser playback, command bar. Mini note previews draw on
  sequencer nodes; uncaught page errors surface in the log strip.

Verified: **13 test files green** (`test_ui.py` grew a vendored-LiteGraph test:
whitelist serving, kind specs, multi flags) plus **headless-Chrome boot probes** —
the starter patch syncs 4 nodes, a fan-in + Loop patch syncs 5, zero page errors.
Next: the author's jam-session verdict, then #14 (widgets-as-nodes — LiteGraph's
widget system is the natural host).

## 2026-07-08 (later still) — nodes become windows: the MIDI node, VST editor windows, and the control graph

Three author asks in one round ("a more dedicated MIDI node… nodes as windows…
VST visual displays… utility math and logic nodes"), all landed:

- **The `midi` node** — sequence semantics (arr composition, length/offset/repeat/
  transpose; `_resolve_events` treats them identically) with a **dedicated
  piano-roll window face**: minimize = LiteGraph collapse, the ▣ button maximizes
  the node into a resizable window whose body is a full in-canvas roll — left
  click adds, right click deletes (`canvas.onMouse` fires before LiteGraph routes
  buttons, so the face owns clicks and the context menu stays out of the grid),
  length buttons + octave ± in the header, size persists per patch. This is
  question #13's live candidate to subsume sequencer/sequence. Reference studied:
  ryohey/signal. (`tests/test_midi_node.py`.)
- **VST nodes as windows** — `VstUiSession` (voidloops/vsthost.py) spawns
  RemoteVstPlugin with embed `none` → the plugin's REAL native editor on screen
  (`IdShowUI`), a daemon pump draining knob chatter so the GUI never wedges;
  `apply` bakes state to a standard **`.fxp`** (`IdSavePresetFile` — chunk and
  parameter plugins both) stored in `<project>/presets/`, written to the node's
  `preset`, and **loaded by every render instance** (`backend._load_preset`).
  Buttons on the node face + inspector; `POST /vstui`. Verified headless with OTT
  (`test_preset_roundtrip` — CcnK magic, fresh-instance load).
- **The control graph (question #14a)** — new `control` signal; **params as
  ports**: curated numeric fields grow `p:<field>` inlets (box-shaped, pink);
  utility kinds `value`, `math` (unwired inlets fall back to inline a/b),
  `map`, `compare`, and the **`time-of-day` input** (the author's "connect it to
  time of day" example, now literal — hour 0–24, `override` pins it for
  reproducibility). Evaluated once per render Scry-side
  (`render._eval_control`/`_apply_params`, cycle-refusing); per-block automation
  explicitly waits for streaming (item 3). Old projects compile unchanged (the
  reducer signature widening covers the new indices). (`tests/test_utility.py`,
  7/7 — including time-of-day→map→transpose and compare-as-logic.)

Suite: **15 files green**; headless-Chrome probe syncs a patch with a midi face,
a control wire, and a VST node, zero page errors. #14 split: 14a decided/shipped,
14b (widget faces / LFO / VST params) stays open.

## 2026-07-09 — #14b's first slice: sliders ON nodes (face widgets)

The "widgets as nodes" idea got its visible half: **node faces now wear their
controls**, hosted by LiteGraph's widget system (the bet recorded in
[own UI](/components/own-ui.md) — it paid off; zero server changes, `/state`
already carried `field_ui` ranges and `param` flags). The curation rule keeps
faces musical, not busy:

- **Curated params** (exactly the `p:<field>` fields — tuning, root, the gains,
  amount, feedback, transpose) render as **sliders** (ranged) or drag-numbers.
- **Select fields** (osc wave, effect type, math/compare op) render as combos.
- **Utility kinds** wear *all* their numerics — a `value` node is literally a
  floating knob now.
- **Note kinds get no widgets** (their face is the piano roll); Loops and VST
  nodes are untouched (patch refs / plugin windows respectively).
- A **wired param's widget disables and grays** (name grows `⚡`): the control
  graph owns that value — the face says so instead of lying.

The interaction subtlety that mattered: our sync model rebuilds the whole
LiteGraph graph after every mutation, which would yank a slider out from under a
drag. So widget edits **stage locally and flush on pointer-up** (350 ms fallback
for combo menus), one `set` per gesture — the CLI echo stays readable (commitment
2) and the auto-repair rebuild happens only after the hand lifts. LiteGraph
quirks absorbed: sliders are continuous (we snap to the field's `step`),
drag-numbers move by `0.1×step` per pixel (we pass `step×10`).

Verified: **16 test files green**; a headless-Chrome probe counts exactly the
expected 11 widgets across a 7-node patch (osc 2, effect 3, mix 1, output 1,
value 1, math 3 — sequencer 0 by design; `math.b` wired → disabled), zero page
errors, via a `data-widgets` breadcrumb next to `data-nodes`. Next in #14b:
LFO/envelope (blocked on per-block eval → streaming playback, roadmap item 3),
VST params as ports, musical effect presets.

**Item 3's first bite rode along: live tweaks are audible.** *(see below — same
day, the feedback round that called the native era)* A `set` landing
while the transport plays (face widget, inspector field — either path)
re-renders and swaps the `<audio>` source in place, resuming at the same
position — turn the knob mid-playback and hear it a render later. Honest
scoping: the trivial pure-Python backend can't do real-time block rendering,
so true block-by-block streaming (and with it per-block control eval / LFO)
waits for the engine era; this delivers the jam-feel half now.

## 2026-07-09 (later) — jam feedback round 3: the diagnosis, the fixes, and the author calls the native era

Six field reports from a real jam. The headline diagnosis: **the mix node was
never broken.** Replaying the author's exact CLI transcript (rm sequence1 →
undo → the whole mix rebuild) compiles two voices, four notes each, and renders
at full peak — but the author's notes sat at **tick 1344 = seven seconds in**,
placed via a roll they couldn't scroll, so play produced 7s of silence and read
as "the mix doesn't work". Tuning likewise works end-to-end (440→880 Hz verified
by zero-crossing); it was inaudible for the same reason. The real bugs were UX:

- **#2 positions jumping** — nodes without a saved position were re-auto-laid-out
  on every sync, and wire changes change graph depth → jumps. **Fixed the right
  way, per the author's #6**: node positions are now **model content** (`x`/`y`
  via `POST /move` → one atomic `setjson` batch). Every move is a visible CLI
  action, layout persists in the project file (not localStorage), and moving is
  undoable. The author's "log the UI itself" is now literally true for the canvas.
- **#4 params "resetting"** — two real mechanisms found and fixed: the inspector
  redrew (clobbering a field mid-typing) whenever any other mutation refreshed
  the page — it now skips the redraw while focus is inside it; and a graph
  rebuild recreated face widgets from server values while a newer value sat
  staged-but-unflushed — widgets now prefer the staged value.
- **#3 can't move around the roll** — the roll face gained a view: wheel scrolls
  pitch, shift+wheel scrolls time, ◀▶ buttons page by a bar, a `bar N` readout,
  and **opening a roll auto-centers on its notes** — the fix that would have
  shown the author their 7-seconds-in chord immediately.
- **The silence trap itself** — `/render` now reports `first_sound_s`; play logs
  *"first sound lands at 7.0s"* whenever the lead-in exceeds 1.5s.
- The **WinError 10053 traceback spam** (browser aborting `/wav` fetches on src
  swap) is swallowed where it belongs — it was never an error.

Verified: full suite **0 failures** (test_ui grew `move_is_model_content`:
batch = one undo frame; `first_sound_s` asserted), Chrome probe still green.

**And the era call:** the author declared the Python VLS a successful test
version and asked to start the real one — different language, custom responsive
GUI, total interaction observability ("if we need something with a LOT of
control… we might just have to make it ourselves"). Captured as **open question
#16** with a full stack evaluation (lean: **C++20 + Dear ImGui + our own node
canvas + miniaudio**, engine-first; Rust as the documented alternative) and a
new roadmap section, **The native era**: Void Core stays the substrate, the
dispatcher seam stays the architecture, the Python VLS becomes the reference
implementation + test harness, and streaming playback becomes the native
build's first milestone. Awaiting the author's #16 verdict before code starts.

## 2026-07-09 (later still) — #16 decided: C++20, and Void Node is born

The author answered the same day: **C++20, confirmed** — and raised the stakes:
the node UI layer becomes a **separate, generalizable project**. *"We'll call
this Void Node."* Founded today at `../VoidNode` (own OKF, concept-first, no C++
yet by design; eventually its own dedicated agent). Founding requirements from
the author: complete Void Core compatibility with the CLI expanded until
*everything* is logged (node movements included — VLS's positions-as-content
was the same-day proof of concept), **widgets-as-nodes as a founding feature**,
generalizable beyond VLS (most UI-bearing Void Core apps build on it;
FaultSack-class and ESP32-class apps exempt), and production order = *recreate
what we already have, better, piece by piece*.

An outside AI's concept draft was rethought with Void Core in mind — its
"radical log-first architecture" turned out to describe Void Core itself; the
honest mapping (what's inherited vs what's genuinely the library: projection
engine, gesture→command compilation, faces/widgets, the C++ embed) is Void
Node's `okf/concepts/log-first-inheritance.md`, with the draft archived +
critiqued. Cut in the rethink: execution engine (compute boundary), BaaS/cloud,
git-like branch/merge, compilation targets.

**The Void Core C++ audit ran** (author's ask): the C ABI is C++-ready by
design (`extern "C"` header, self-contained dll, CMake, CI prebuilts). One real
gap: **the reducer lives at the Python seam** — a C++ host has no Reduce. Filed
with three options (lean: portable executor spec + conformance, core-side C
reduce eventually) in `../VoidNode/MESSAGE_FOR_VOIDCORE.md`, alongside asks on
log attribution and a view-gesture undo slice. Blocking for VLS-native's
compile pipeline, not for Void Node's canvas.

VLS's role from here: **reference implementation + first client**. The Python
editor and its 16 green test files are the behavioral spec for Void Node's
parity phases; new feature work lands native-side. #16 marked decided in
`developer_questions.md`; the roadmap's native era now routes through Void Node.

## 2026-07-16 — The native build begins, on Void Maiz

The author's call: Void Node — renamed **Void Maiz** upstream on 2026-07-13
(`../VoidMaiz`, namespace `maiz::`) — is ready, with *"MORE than enough
features"* to be the base library; VLS development continues **native-first**,
the full C++ rewrite proceeding on Void Maiz. What Maiz brings, verified today
(its 5 suites green): the `maiz::Core` embed, the projection engine, the
canvas + gesture grammar (move/wire/marquee/add/context/resize, all compiled
to dispatcher commands), faces, inspector, the widget protocol with per-glyph
field editors, the command bar + log strip, and the **C++ port of the reduce
conformance contract** — the gap we filed on 2026-07-09 is closed as a
portable contract.

Sequencing amendment to the native-era plan (#16 said engine-first): with the
shell now nearly free, **the Maiz integration proof comes first** — the native
shell skeleton — and the streaming engine follows as the next milestone, its
priority unchanged. Recorded as the milestone list in the roadmap's native era.

The one real seam decision surfaced (new open question #17, proceeding on the
lean): **wire relations go numeric in the native model** — the reduce
contract's linear `"i:j"` form, which Void Maiz projects natively and
`render.py` already converts to at compile time — retiring the Python era's
`signal:src->dst` named form at the model boundary. Port names stay in glyph
hints (the canvas shows names; the model speaks indices). Python-era
`.vlp.json` projects will need a one-shot relation translation on import
(milestone 2); until then the native shell keeps its own project file.

Landed today: **`native/`** — the C++20 skeleton (`native/CMakeLists.txt`,
consuming Void Maiz as a subdirectory the InteractionCombinators way):
`src/glyphs.{hpp,cpp}` = the VLS glyph set ported from `model.py` (all 18 node
kinds + the content glyphs, categories as palette groups, params as `p:` ports,
signal-typed ports in Maiz's `hints.ports` convention, `port_index()` = the
named⇄linear map, mirroring `render.py`); `src/app.cpp` = the shell (canvas +
inspector + log strip + command bar, starter patch = the Python `ui()` starter
built through the dispatcher, load/save of the native project file). The
Python VLS remains the reference implementation, untouched.

## 2026-07-16 (later) — The VLS makeover begins; first message to Void Maiz

The author, after seeing milestone 1: Maiz's default look *"was good as a demo
version… but for VLS I want it to look a bit better, where nodes have a bit
more features — ports with different shapes, buttons, dials"* — a makeover
specific to VLS, continuing development host-side wherever Maiz's surface
already allows, messaging upstream only for what it doesn't.

The audit of that surface: theming (every CanvasTheme color + CanvasStyle
metric is host-supplied), per-glyph colors/face sizes/shapes (window/polygon/
circle/block — shape-is-notation is built), and arbitrary in-node widgets via
the face registry are all reachable TODAY. Qt widgets are ruled out by Maiz's
own Q12 (ImGui-composed is the one sanctioned path) — no ask made. The real
gaps, both owned by canvas.cpp: port dots are hash-colored circles (no host
mapping, no shapes), and all linguine draw one theme color (no per-type wire
styling — parity loss vs the LiteGraph editor's typed wires).

Landed host-side: **the VLS skin** (`native/src/style.{hpp,cpp}` — the
graphite-and-amber studio theme, dark default + honest light variant, VLS
metrics: wider faces, softer corners, bigger port targets; `signal_color()` =
the four signal accents, CVD-checked, ready for upstream adoption) and **the
rotary knob** (`native/src/faces.{hpp,cpp}::face_knob` — 270° sweep, vertical
drag staging ONE `setjson` on release per #14b, disabled-when-wired in both
the plain and `p:<field>` spellings, double-click reset, integer snap), wired
onto osc/effect/mix/output/sampler/sequence/midi/note faces; face heights
sized for knob rows in the glyph table. app.cpp slimmed to consume both.
All 6 suites stay green; the shell runs restyled.

Upstream: **`MESSAGE_FOR_VOIDMAIZ.md`** (repo root, first VLS→Maiz message,
author relays): §1 port style registry (type → color+shape; the shape channel
is an accessibility requirement, not taste), §2 typed wire styling (registry
color per wire type), §3 `field_is_wired` also matching `p:<key>` (one line —
today the kit's editors never disable for VLS param wires), §4 the knob
offered to the kit once jam-proven, §5 seconding the multi-inlet spare-slot
backlog item. Nothing blocks; §1+§2 are the unreachable half of the makeover.

## 2026-07-16 (later still) — Void Maiz's reply consumed: the makeover is whole

`MESSAGE_FOR_VLS.md` (Void Maiz, same day): **the entire visual-identity batch
landed upstream same-day.** §1 the port style registry
(`CanvasStyle::port_types`, type → color + shape, our accessibility framing
adopted as the feature's stated reason); §2 typed wire colors (from-port's
type, to-port's when the from end is an untyped principal; pending drag shows
the type color until the verdict tint takes over); §3 `field_is_wired` now
matches `p:<key>` kit-wide; §4 our knob absorbed as `maiz::face_knob` +
`widget_field_knob` + the `"knob:min,max,default,snap"` editor kind — with a
real fix (commits via `commit_value`, so string-typed fields stay strings;
our local version always `setjson`ed) and theme-derived colors (SliderGrab);
§5 spare slots re-weighted [vls]. They also defused an ADL ambiguity in our
tree (qualified our `face_knob` calls) — noted, and made moot below.

Adopted in `native/` immediately: **`vls::face_knob` deleted** (born here
08:xx, upstreamed and retired by evening — the one-implementation rule
working as designed); `faces.cpp` is now pure per-glyph wiring over
`maiz::face_knob`. **The amber rides the ImGui style** —
`style.cpp::apply_ui_style` (SliderGrab/CheckMark = VLS amber, both modes).
**`port_types` declared** in `canvas_style()`: audio = filled circle
(continuous), events = ring (discrete), clock = triangle (pulse), control =
square (the Python editor's box slots, muscle-memory parity); typed wires
inherit the colors. **Glyph editors switched to `knob:` kinds** (tuning,
transpose, root, gain×3, amount, feedback, velocity) — the inspector now
wears knobs through the same registration that faces the nodes, exactly the
widget-protocol promise. Both message files kept (consumed, marked); all 6
suites green; the shell verified running.

The makeover's asked-for half is delivered; what remains is ours: jam
verdict on the taxonomy/theme, then the engine (milestone 4) unless the
author reorders.

## 2026-07-16 (later still) — Desktop shortcut for the native shell

The native VLS gets its front door, the successor to the Python era's
`VoidLoops.bat` + "Void Loops Studio" desktop icon. Two pieces:

- **Self-contained exe.** `vls_native.exe` depended on the msys64 ucrt64
  `libstdc++-6.dll` / `libgcc_s_seh-1.dll` (the 0xc0000139-at-launch gotcha
  when Git's own libstdc++ shadowed them). Fixed at the source: the `vls_native`
  target now links `-static -static-libgcc -static-libstdc++`, so the only
  non-system dependency left is `libvoidcore.dll` — which rides beside the exe,
  where Windows' loader finds it regardless of PATH or working dir. Verified:
  the exe launches on a plain PATH now. No DLL-copying, no launcher wrapper,
  no console flash.
- **The shortcut + icon.** `native/install_shortcut.ps1` (re)creates the
  Desktop `.lnk` (target = the exe, workdir = its bin, icon = the new asset);
  `native/assets/vls.ico` is a themed mark matching the makeover — an amber
  270° knob sweep + pointer on a graphite plate, with an audio disc / events
  ring at the base (the port-shape taxonomy in miniature). Verified launching
  through the `.lnk` itself. All 6 suites stay green.

## 2026-10-04 — The catch-up begins: eleven weeks behind, a feature freeze, and what collaborating on music means

The author: VLS is behind the family, so **new features are on hold** while we
catch up on the fundamentals of the other libraries, with LAN networking the
important one. They also asked what collaborating on a music loop should mean,
and for a "local only / private" mode beside a collaborative one.

**Inbox, read and answered.** Void Maiz *headless available* (2026-08-18):
adopting in catch-up C2, with a musical action vocabulary so an agent uses the
instrument rather than poking the data model. Void Core 0.2.14 (2026-09-03):
reship verdict confirmed; save already round-trips the document (§2c is safe);
our glyphs are only *registered*, so they would not travel to a peer, and
declaring them is C1. Void Jelly (2026-10-03): informational, no reply needed.
Void Mago (2026-10-04): all three asks done (below). Replies left in
`../VoidCore` and `../VoidMaiz`.

**Void Mago's asks.** `void.json` written (application, 0.0.1 from
`pyproject.toml`, requires Core via Maiz at `c-abi`, Maiz and Allomone static).
`mago doctor`: no errors or notes of ours (its two errors are a Core↔Palabra
seam-name disagreement). `mago blast voidcore` lists us under RESHIP. The *Void
Node* question is settled in `developer_questions.md`: it is Void Maiz, renamed
2026-07-13.

**The native shell still builds.** Rebuilt against today's Maiz, which now pulls
in Palabra and the Reticulum vendor tree: 25/26 green, and the red one is
Maiz's known `reduce_conformance` (17/25 since Core extended the contract).
One trap found: building under a long path (the agent's temp folder) fails with
`opening dependency file …obj.d: No such file or directory`. That is Windows'
path limit meeting Reticulum's hashed object directories, not a code error.
Build in `native/build`.

**What the family now gives us.** Maiz Q30: Maiz owns what networking looks like,
Palabra owns what it is, the app answers "may this rune leave this device?".
Palabra: whole-state sync that converges under loss and partition; per-mantle and
per-rune export; files by hash. Reticulum on the LAN, sealed, with a person
allowing each joiner; Interaction Combinators runs two-person sessions on it,
with an Android build. Maiz many-inputs (`"max":"many"`) is the spare-slot ask
we made in July.

**The design: [collaboration](/concepts/collaboration.md).** Two axes rather than
one switch. A *project* is Local (no network code runs, the default), Hosted or
Joined, kept in peer-local `config` because privacy is the sender's decision. A
*Loop* is private, **bounced** (the sound leaves by hash, the recipe stays home,
which is how musicians share unfinished ideas) or shared. The render mantle
never leaves. VLS never rewrites the shared graph, so IC's wire-rune machinery
is not needed here. VSTs are the hard case because every device renders
locally; the answer is a visible placeholder plus bounce-on-demand from a peer
that can render, which is Palabra's planned compute capability. Jamming needs a
fourth channel, a shared clock (#19). Tempo has to leave `config` to sync (#18).
A phone is a Remote first (#20), and the streaming engine must be portable from
its first line.

**Roadmap:** a *Catch-up phase* (C0 done; C1 Core 0.2.14, C2 Maiz, C3 LAN editing)
sits before the native build order, which resumes at milestone 2 afterwards.
