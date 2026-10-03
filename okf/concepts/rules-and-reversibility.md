---
type: Foundation
title: Rules, reversibility & the boundary
description: Three tiers of rule — structural invariants, the free/total/reversible algebra, and lossy boundary policies. Where each lives, and why a negative-length note is just a reversed note.
resource: notes/rules-and-reversibility.md
tags: [status:planned, audience:dev, confidence:asserted, foundation, research]
timestamp: 2026-06-29T00:00:00Z
---

The author intuited that some "rules" belong in the engine and some don't, and that
"no negative note length" felt wrong while "velocity clamp" felt useful-but-off. The
terminology that sorts this:

# Three tiers of rule

1. **Well-formedness invariants** (core, immutable). What makes the data *coherent at all*:
   a wire connects ports that exist; a node's glyph is registered. These are the "rules the
   user can't change" — but they are **structural**, not musical.
2. **The free, total, reversible algebra** (core, permissive). The space of everything
   expressible, *including the weird*. The core stays **total** (defined everywhere) and
   **information-preserving** (reversible). Domain restrictions like "length must be > 0"
   do **not** belong here — they foreclose meaning.
3. **Boundary policies / lossy projections** (optional, at the edge). Velocity clamp, grid
   snap. A clamp is **non-injective** (200 and 150 both → 127; not invertible); snap
   destroys the original value. Lossy ops break reversibility/composability, so they live
   at the **render boundary** or as **UI/settings toggles**, never as core laws.

# A nice consequence: negative length = reversal (not the main thing)

A **negative-length note is a time-reversed note** — negative duration *is* the reversal
operation, so forbidding it would foreclose reversal (the FL "reversed intro" story — see
[reverse & reference](/concepts/reverse-and-reference.md)). It stays legal in tier 2.

But — the author's correction (2026-07-06): this was **just an idea worth noting, not the
point of VLS**. The main thing is **node-based music creation**. Negative length matters
here only as an *example* of the principle: keep the core total and don't add domain
restrictions that foreclose meaning. Don't over-index on it.

# Strictness now, emergent interactions later (dev-answer 5, 2026-07-06)

Wire/port typing is **strict for now**: a type-mismatched wire is *rejected* (built that
way in step 1 — `wire()` refuses it), to avoid crashes while the prototype stands up.
But the author's long-term direction inverts the fear: eventually the system should
treat **unprecedented connections as a feature** — plugging a "sound file" node into a
"sequence arrangement" port shouldn't error; the system should have to *decide what that
would even mean*. Tier-1 strictness is therefore a **provisional prototype posture**, not
a permanent law; the tier framework already leaves room (an "adapter" resolving a weird
wire is tier-2/3 machinery, not a core rewrite).

# The resolutions (the author's three cases)

- **No negative length** → *not a rule.* It is reversal; keep it in the total algebra.
- **Velocity clamp** → good and useful, but a **tier-3 boundary policy** (speaker safety),
  optional, in settings/at render — not a core law.
- **Grid snap** → a **UI input affordance** (tier 3), never core.

# The principle

Keep the core **conservative and reversible** (like reversible computation: no information
destroyed). Push every **lossy projection** to the boundary, optional. This is what keeps
recursion, reversal, and future interactions open instead of foreclosed.

# Further reading (external background)

- [Partial function](https://en.wikipedia.org/wiki/Partial_function) (total vs partial /
  domain restriction) · [Injective function](https://en.wikipedia.org/wiki/Injective_function)
  (why a clamp is lossy) · [Reversible computing](https://en.wikipedia.org/wiki/Reversible_computing)
  (the "information-preserving core" idea).

# Status

`planned` / foundational principle. Governs what may ever be hard-coded as a rule.
