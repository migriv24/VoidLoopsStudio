---
type: Component
title: Own UI
description: The Void Loops editor — a node canvas over the dispatcher. v4 rebuilt the canvas on vendored LiteGraph.js (2026-07-08, question #15); the seam and panels carried over unchanged.
resource: voidloops/ui.py
tags: [status:current, audience:dev, confidence:verified]
timestamp: 2026-07-08T00:00:00Z
---

Void Loops builds its **own** UI. Post-[pivot](/concepts/node-graph.md) it is a **node
editor**; like every Void Core face it is a thin client over the **dispatcher** — the
CLI, scripts, and the page all issue the same verbs, and the page can never poke the
model directly.

# Two commitments that outlive any front end

1. **The dispatcher-client seam.** The page talks only `/state` (read) + typed POST
   endpoints that resolve to dispatcher commands / project calls. Any future front end
   replaces the *page*, never the seam.
2. **Every action is a visible CLI action** (author's ask, 2026-07-08): the UI runs
   with `proj.echo` on, so each click prints its dispatcher command in the terminal.
   The transcript is the shared language between the author, the agent, and the CLI's
   own improvement backlog.

# Built (v4, 2026-07-08): the canvas on LiteGraph.js

The v3 hand-rolled canvas hit its ceiling; per question #15 ("yes! litegraph!") the
canvas layer now rides on **LiteGraph.js** (MIT, `voidloops/vendor/litegraph.core.js`
build — vendored with its license, served locally at `/vendor/*`, still zero CDN /
fully offline). The page moved out of the Python string into `voidloops/editor.html`.

What the library brought for free: **multi-select + marquee + zoom/pan**, native
link dragging with type-checked slots (our signal types *are* LiteGraph slot types,
so audio/events/clock compatibility is enforced in-canvas with our colors), Delete
on selections, Ctrl+A, a **searchable add box** (double-click, or **Shift+A** — the
Blender gesture now opens it at the cursor) and right-click context menus.

How our model maps onto it:

- Node kinds register as LiteGraph types **generated from `/state.kinds`**
  (`<category>/<kind>` — the taxonomy is the menu structure); Loops register
  per-mantle as `loop/<ref>` (double-click a Loop = enter its patch).
- **`/state` is the single source of truth**: after every mutation the page rebuilds
  the LiteGraph graph from it. A server-rejected edit (cycle, type clash, occupied
  inlet) simply vanishes on re-sync — **auto-repair for free**, and LiteGraph's own
  serialization is never used (the model stays in Void Core).
- Graph gestures emit POSTs: link drag → `/wire`, link removal → `/unwire`, node
  delete → `/delete`, search-box create → `/node` / `/loop` — each echoed as CLI.
  Mutations run through a promise queue so the CLI transcript matches click order.
- **Multi inlets** (`mix.in`, `sequence.arr`) show one slot per existing wire plus
  one spare, so fan-in is always available; the `multi` flag rides on `/state` ports.
- **Node positions are model content** (`x`/`y`, since 2026-07-09 — jam feedback
  #2/#6): a drag end POSTs `/move` (one atomic batch = one undo frame), so every
  move is a visible CLI action, layout persists in the project file, and moving
  undoes like any edit. Newcomers fall into a depth-based auto-layout until first
  touched. Sequencer/sequence nodes draw a **mini note preview**; uncaught page
  errors surface in the log strip (nothing is silent).

Carried over intact from v3: the **inspector** (typed field editors — wave/effect
dropdowns, VST picker with bitness, Loop-ref/mantle dropdowns, slider+number pairs,
library picker), the clickable **piano roll**, the LMMS **sound-library browser**
(credited), patch switcher, undo/redo, live BPM, **browser-native playback**
(`/render` → `<audio src=/wav>`), and the dispatcher command bar. Launched from the
desktop icon onto `~/Documents/VoidLoopsProjects/default.vlp.json`.

# Nodes are windows (author, 2026-07-08)

"We can think of nodes as sort of being windows... and inside them we should be able
to minimize and such." The face system (same date):

- **Minimize** = LiteGraph's native collapse (the dot in the title bar).
  **Maximize** = the ▣ button on nodes that have a face; the node becomes a
  resizable window (drag the corner; size persists per patch).
- **The MIDI node's face is a full in-canvas piano roll**: left click adds a note,
  right click deletes (the face claims clicks via `canvas.onMouse`, which fires
  before LiteGraph's own routing — right-click inside the roll never opens the
  context menu); note-length buttons (1/16…1/2) and octave ± in the roll's header;
  key column with C labels, black-key shading, beat/bar lines. Minimized, the same
  node shows the mini note-preview strip. (`sequencer`/`sequence` get the identical
  face — the `midi` kind is the dedicated home; reference studied: ryohey/signal.)
  **The roll scrolls (2026-07-09, jam #3)**: wheel = pitch, shift+wheel = time,
  ◀▶ pages by a bar, `bar N` readout — and opening a roll **auto-centers on its
  notes**, so late-placed notes are in view instead of silently off-grid.
- **VST nodes are windows onto the plugin**: `plugin window` opens the VST's own
  native editor (see [instrument as holiday](/concepts/instrument-as-holiday.md));
  `apply` bakes the knob state into the node as a `.fxp` preset (renders load it);
  `close` tears it down. Buttons live on the node face and in the inspector.
- **Face widgets (#14b, 2026-07-09): sliders ON nodes.** LiteGraph's widget system
  hosts them, exactly as predicted. The curation rule: **curated params** (the
  `p:<field>` fields — tuning, root, gain, amount, feedback, transpose) wear a
  slider (ranged) or a drag-number; **select fields** (wave, effect type, math op)
  wear a combo; **utility kinds** wear *all* their numerics — a `value` node is
  literally a knob, widgets-as-nodes made real. Note kinds keep their roll face
  (no widget clutter); a **wired param's widget grays out** (`⚡` suffix) — the
  control graph owns that value. Drags stage locally and **flush on pointer-up**
  (350 ms fallback) so the `/state` rebuild never yanks a slider mid-drag, and the
  CLI echo stays one `set` per gesture, not one per pixel. LiteGraph quirks handled:
  sliders are continuous (we snap to the field's step); drag-numbers move by
  `0.1×step` per pixel (we scale ×10).
- Every face action is still a POST → a visible CLI action (commitment 2 holds).

Verified: `tests/test_ui.py` (5/5 — page, state incl. kind port specs + multi flags,
vendored files whitelist-served, dispatcher round-trip, render) plus headless-Chrome
boot probes (graph syncs the starter patch, fan-in and Loop nodes, zero page errors).

# Blender study (ongoing during this era)

Shift+A was the first borrow; the deeper lessons to keep applying: gestures happen
*at the cursor*, search-first menus, every action nameable/repeatable (our CLI echo
is the analogue of Blender's operator log), and editors as views over one data model.

# Further out

The rest of #14b: **LFO/envelope nodes** (blocked on per-block evaluation →
streaming playback), **VST params as ports**, musical presets per effect. The
in-canvas piano roll grows toward a real clip editor (drag-to-move/resize); the
toolkit question for a native shell (Qt/ImGui vs the browser) stays deferred until
the C++ engine work forces it — the seam makes any of these a front-end swap.

# Status

`current` (v4 + node-as-window faces 2026-07-08, + #14b face widgets 2026-07-09 —
`voidloops/ui.py` + `voidloops/editor.html` + `voidloops/vendor/`, verified in
`tests/test_ui.py` + `tests/test_midi_node.py` + headless-Chrome probes incl. a
widget-count probe). Control wires and `p:<field>` param inlets draw natively
(pink, box-shaped slots); curated params wear face sliders. Awaiting the author's
next jam-session verdict. `planned`: LFO/envelope faces (post-streaming), roll
drag-to-move/resize notes.

# The native shell (2026-07-16 →)

The editor's real successor lives in `native/` on **Void Maiz** (the toolkit
question above resolved by #16 + the 2026-07-16 "proceed on Maiz" call). The
seam held exactly as promised: the shell is another dispatcher client — canvas,
inspector, log strip, command bar, every gesture a visible command. This page
(`ui.py` + `editor.html`) is now the *reference implementation*: behavior
questions (staging, faces, typed-wire UX) defer to it.

The VLS identity rides Maiz's host surface: `native/src/style.*` (the
graphite-and-amber studio theme, both modes) and `native/src/faces.*` (the
rotary knob + face wiring — the successor of the #14b sliders). Typed port
*shapes/colors* and typed wire colors were asked upstream and landed same-day
(`MESSAGE_FOR_VLS.md` §1/§2 — `CanvasStyle::port_types`); control kept its
box-shaped slot from the LiteGraph era. The knob was absorbed into Maiz's kit
(§4) and VLS consumes it, amber via the ImGui style. The piano-roll face is
native milestone 6.
