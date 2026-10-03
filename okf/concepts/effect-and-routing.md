---
type: Concept
title: Effects & routing
description: In the node graph, effects are stream-processor nodes and routing is wires. Mixing is an add/mix node. Tag-based effect rules still ride on Scry + Temper.
resource: notes/effect-and-routing.md
tags: [status:planned, audience:dev, audience:library, confidence:asserted]
timestamp: 2026-06-29T00:00:00Z
---

> Rewritten for the [node pivot](/concepts/node-graph.md). Effects and routing get *simpler*
> in a node graph than they were in the timeline/mixer design.

# Effects are nodes

A reverb, delay, filter, or VST effect is an [effect node](/concepts/node-types.md): audio
in → audio out, with internal state. They need **time flowing through them** (the sample
stream), not a timeline — which is why this was the *hardest* question under the timeline
design and is one of the *easiest* here. Modular synths do reverb/delay trivially; so do we.

# Routing is wires

- A **wire** carries a typed signal between ports — a [link](/concepts/reducer.md) that
  *fires* is a **binding**. No mixer-track abstraction needed; the routing *is* the graph.
- **Mixing / sends** = a [mix/add node](/concepts/node-types.md) summing several audio
  inlets ("stack outputs on top of each other").
- **Feedback** (delay → itself, sidechain) = a [graph cycle](/concepts/loops-and-feedback.md),
  broken by a one-block delay; preserved as opaque agents by the reducer.

# Tag-based effect rules (unchanged from the layers analysis)

"Everything tagged `@track_1` → reverb" still splits the same way ([transformation
layers](/concepts/reducer.md)): per-node inserts via Scry + a custom **Temper** rule
(authorable as data); shared-target routing (one reverb fed by many) is a cross-rune rewrite
the restricted Reduce form defers — hand-wired for now. Note: clamps/limiters for speaker
safety are [boundary policies](/concepts/rules-and-reversibility.md), not core rules.

# Status

**`current` (2026-07-08).** Effects are nodes and they stream: native `effect`
(gain / delay / **reverb** — a Schroeder network — / **limiter**) and `vst-effect`
(audio through a real plugin), applied per-voice along the route
(`voidloops/backend.py`). **Tag-routed FX are built** — the bus replacement this page
promised: `tag_node(n, "drums")` + `add_fx_rule("drums", type="reverb", …)`, rules as
data in `config.fx_rules`, landing on every voice whose generator/route carries the
tag (`voidloops/render.py`; `tests/test_prototype.py` criterion 5). Routing is wires;
mixing is the `mix` node; **fan-out compiles** (2026-07-08). Still `planned`: shared
*bus instances* (today a tag-rule instantiates the effect per voice — one shared
reverb fed by many needs the core's general LHS), and Temper-authored insert rules.
