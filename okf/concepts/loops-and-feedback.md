---
type: Foundation
title: Loops & feedback
description: The signature research concept. Interaction nets are confluent because they are acyclic; audio is full of feedback cycles. Reconciling the two is the core "Void Loops" question.
resource: notes/loops-and-feedback.md
tags: [status:planned, audience:dev, confidence:asserted, foundation, research]
timestamp: 2026-06-27T00:00:00Z
---

The project is named for loops, and the name is mathematically load-bearing — not just
the Fruity-Loops pun.

# Two different "loops"

1. **Musical loops (easy).** A pattern that repeats. Post-[pivot](/concepts/node-graph.md)
   this is a **clock → sequencer that wraps** (a phasor / modular counter) — looping is the
   *default* mode of a running patch, not a region on a timeline. See
   [time without a timeline](/concepts/time-without-timeline.md). No theoretical problem.
2. **Signal feedback (hard).** Feedback delays, sidechain compression, resonators, a bus
   that feeds back into an earlier stage. These are **genuine cycles in the signal
   graph**.

# Why feedback is the hard case

[Interaction nets](/references/void-core.md) get their best properties — strong
confluence, a unique normal form, order-independent reduction — *because the rule
discipline assumes locality and (effectively) acyclic reduction*. **A feedback cycle is
exactly the structure that can break confluence**: there may be no terminating normal
form (the loop is the point — it runs forever, sample by sample).

So Void Loops cannot naively "reduce a pattern to its result" the way NeLA reduces a
program. The resolution (consistent with the [drift test](/concepts/daw-architecture.md))
is now **built in Void Core**, exactly as this project requested:

- [Reduce](/concepts/reducer.md) fires only on **active pairs** (principals meeting with a
  rule), so everything else is inert — feedback cycles are preserved for free. The host
  additionally marks feedback agents **opaque** (by glyph or id) so the reducer never
  touches them.
- The acyclic structure around the cycles normalizes; the **cycles pass through as
  cycles** to [Machine A](/components/lmms-engine.md), which evaluates them *over time*
  (one audio block feeds the next) — feedback is a time-domain computation, the host's
  job, not a rewrite to a normal form.

# The open question (mechanism resolved; semantics still research)

*Can a net with audio feedback be given a well-defined, useful structural semantics —
or do cycles simply mark "here the host computes a fixpoint over time"?* This is the
deferred research thread the project exists to explore.

# Further reading (external background)

- [Confluence (rewriting)](https://en.wikipedia.org/wiki/Confluence_%28abstract_rewriting%29)
  — the property cycles threaten. · [Interaction nets](https://en.wikipedia.org/wiki/Interaction_nets)
  — the substrate. · [Audio feedback](https://en.wikipedia.org/wiki/Audio_feedback) — the
  physical phenomenon a signal cycle models.

# Status

`planned` / research. The **mechanism** (preserve cycles as opaque agents) is built and
verified in Void Core's [Reduce](/concepts/reducer.md) layer; the **semantics** (a
structural account of feedback) is the open research thread.
