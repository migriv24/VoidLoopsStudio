---
type: Concept
title: The transformation layers (Reduce / Temper / Scry)
description: How Void Loops APPLIES Void Core's three transformation layers. Slimmed 2026-07-06 — the layers themselves are the core's concern; the authoritative detail lives in Void Core's OKF.
resource: ../VoidCore/okf/concepts/reduce.md
tags: [status:planned, audience:dev, confidence:asserted, foundation]
timestamp: 2026-07-06T00:00:00Z
---

> Slimmed 2026-07-06 per the author's FaultSack note: the layers are **an aspect of Void
> Core** — understand them, but don't re-document them here. The authoritative pages are
> Void Core's own [Reduce / Temper / Scry concepts](/references/void-core.md)
> (`VoidCore/okf/concepts/{reduce,temper,scry}.md`). This page keeps only *our use*.

The one-line map (details upstream): **Scry** = pure read-side projection; **Temper** =
idempotent normalization rules; **Reduce** = the interaction-net rewriter (`net→net`);
**materialize** = the one explicit, undoable freeze. All pure, all off the audio thread —
which is what lets them produce the immutable snapshot the
[realtime boundary](/concepts/realtime-boundary.md) hands to the engine.

# How the DAW uses each

- **Scry** — select rule targets by tag (`track:lead`); resolve the view the
  [render adapter](/concepts/render-domain.md) consumes (live preview == final render).
- **Temper** — canonicalize patterns (sort/dedupe/default velocity); per-track
  [effect-insert rules](/concepts/effect-and-routing.md) authored as data.
- **Reduce** — the genuinely topological work: **compiling the node graph into the
  engine's render graph**, including [Loop](/concepts/loop.md) expansion via `expand`,
  with [cycles preserved as opaque agents](/concepts/loops-and-feedback.md).
- **materialize** — "bake this pattern to real notes": user-initiated, undoable, never
  the hot render path.

# Decided 2026-07-06: the graph-flatten is data-authored Reduce (dev-answer 4)

The author chose **reduce-rules-as-data** over a hand-written flatten pass, reversing the
earlier lean: less computationally efficient, but far more expandable — and it keeps VLS
in **the spirit of Void Core, actually using the interaction net** ("or then what's the
point of using the void core?"). Architecture and future-proofing outrank first-sound
speed here. Where the core's restricted rule form can't express a rewrite yet (general
LHS, data-form `expand` are deferred upstream), we hand-wire *only that gap* and note it,
rather than abandoning the data-authored path.

# Status

`current` in Void Core (see its OKF). **`current` for Void Loops' compile (2026-07-06):**
`voidloops/render.py` runs Reduce with the data-authored spec from
`config.transform.reduce` (seeded + persisted per project) to produce the render mantle,
then resolves the snapshot Scry-side — `tests/test_render.py`. The ruleset is empty until
[Loop](/concepts/loop.md) expansion lands (code-registered `expand`, per the upstream
deferral); Temper rules and `materialize` use remain `planned`.
