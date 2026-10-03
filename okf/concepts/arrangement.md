---
type: Concept
title: Arrangement (deprecated)
description: Timeline-era concept — the song as a mantle of clip-runes placed on a timeline. Removed by the 2026-06-29 node pivot, which abandons the arrangement timeline entirely.
resource: null
tags: [status:deprecated, audience:dev, confidence:asserted]
timestamp: 2026-06-29T00:00:00Z
---

> **Deprecated 2026-06-29.** The [node pivot](/concepts/node-graph.md) removes the
> arrangement **timeline** outright (the author wanted no middle ground). There is no
> top-level timeline of clips.

The song's structure now lives in the [node graph](/concepts/node-graph.md) itself: time is
produced by clock/sequencer nodes ([time without a timeline](/concepts/time-without-timeline.md)),
sections are [Loops](/concepts/loop.md), and the "final result" is whatever
the [output node](/concepts/render-domain.md) yields over a gated interval. Kept for history.
