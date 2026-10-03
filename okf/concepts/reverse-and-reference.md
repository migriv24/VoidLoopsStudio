---
type: Concept
title: Reverse & reference nodes
description: The recursive "render-reference" feature — a node that takes a rendered sub-graph as input (e.g. a reversed copy of the ending) and updates live when the source changes. The original motivation for building this DAW.
resource: notes/reverse-and-reference.md
tags: [status:planned, audience:dev, confidence:asserted, research]
timestamp: 2026-06-29T00:00:00Z
---

The feature that motivated the whole project (the author's words): in FL Studio they
wanted a reversed copy of the song's *ending* at the *start*. Exporting an MP3 and
reversing it meant the intro broke every time they edited the ending. The wish: a clip
that is a **live reference to a rendered section**, not a baked sample.

# Why the node graph gives this for free

In a [node graph](/concepts/node-graph.md) a node can take *another part of the graph* as
input. A **reverse node** wires the **rendered output of a sub-graph** (the ending group)
into a reverse processor. Because it references the *graph*, not a frozen sample, **editing
the ending updates the reversed intro automatically.** The "render reference" the author
wanted is just a wire into a [Loop](/concepts/loop.md). And a reverse
is a [negative-length](/concepts/rules-and-reversibility.md) render — the algebra already
permits it.

# The honest subtleties

- **Bounded render.** Reversal needs a *finite* segment, so a reverse/freeze node carries
  explicit time bounds (a local span — not a global timeline).
- **Recursion / cycles.** If the intro references the ending which references the intro,
  you get infinite regress. That is a [cycle](/concepts/loops-and-feedback.md); Void Core's
  **opaque-agent** rule (preserve, don't reduce) is exactly the guard. The recursion the
  author is excited about is real *and* is where the cycle math earns its keep.
- **Cost.** A live reference re-renders its source on change; a freeze/cache (with
  [materialize](/concepts/reducer.md) + provenance) is the escape hatch when that's too
  expensive.

# Further reading (external background)

- [Backmasking](https://en.wikipedia.org/wiki/Backmasking) — reversed audio in music (the
  effect itself). · [Recursion](https://en.wikipedia.org/wiki/Recursion_%28computer_science%29)
  — the reference-into-a-render structure and its base-case discipline.

# Status

`planned` / research, and explicitly *far off* — captured now because it is the north
star: the design must never foreclose it. Not in the v1 [slice](/roadmap.md).
