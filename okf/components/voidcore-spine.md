---
type: Component
title: Void Core spine
description: The linked Void Core C core (libvoidcore) — provides the model, dispatcher, tags, undo, and scripting that replace LMMS's data layer.
resource: null
tags: [status:planned, audience:dev, confidence:asserted]
timestamp: 2026-06-27T00:00:00Z
---

The new data layer of the gutted [LMMS fork](/components/lmms-engine.md) is
[Void Core](/references/void-core.md), linked as a C library (`libvoidcore`, header
`voidcore.h`). Because LMMS is C++ and Void Core ships as a C core, **it links directly —
no rewrite, no IPC.** (This is the same reason Void Core's C core "didn't need a rewrite"
to support holidays.)

# What it provides Void Loops, for free

- the rune/mantle/holiday/domain model = the whole [arrangement model](/concepts/daw-architecture.md);
- the **dispatcher** = one command surface the CLI, the [own UI](/components/own-ui.md),
  and scripts all call;
- **tags + filter grammar** = mixer tracks and [effect rules](/concepts/effect-and-routing.md);
- **undo/redo + dirty-tracking** = the DAW's edit history for free;
- **Voidscript** = a scripting/automation surface most DAWs lack entirely.

# What Void Loops must add to Void Core

- node glyphs: `osc`, `sequencer`, `clock`, `output`, `mix`, `sample`, plus `note`
  (the sequencer's contents) — each with [port signatures](/concepts/node-types.md);
- an instrument/effect **holiday** wrapping the plugin/synth (the holiday interface and
  the bound `vc.set_effect_handler` seam already exist);
- the `render`/`play` handler that drives the audio backend (build-order step 4);
- our DAW Temper rules + selectors, authored as data (`config.transform`).

The **transformation layers I would have had to build myself are already done**: Void
Core shipped Reduce / Temper / Scry / materialize (2026-06-28), authorable as data, with
the effect handler bound. See [the transformation layers](/concepts/reducer.md). So Void
Loops is now almost pure application work over a ready foundation.

# Status

`planned` (our app). The foundation is confirmed capable — the author's "can Void Core
even do this?" question is answered **yes**, with the
[realtime boundary](/concepts/realtime-boundary.md) respected and the layers/effect-seam
already in place.
