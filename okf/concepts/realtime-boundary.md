---
type: Foundation
title: Realtime boundary
description: The audio thread must never call into Void Core. The overlay edits at human speed; the engine renders lock-free from a snapshot.
resource: notes/realtime-boundary.md
tags: [status:planned, audience:dev, confidence:asserted, foundation, constraint]
timestamp: 2026-06-27T00:00:00Z
---

The non-negotiable constraint that keeps Void Loops on the right side of the
[drift test](/concepts/daw-architecture.md).

# The rule

- **Void Core edits happen at human speed** (a CLI command, a UI drag, a script).
  They allocate, take locks, push undo frames — all fine off the audio thread.
- **The audio thread must be lock-free and allocation-free.** It may *never* call a
  dispatcher verb, never mutate a rune, never walk the mantle graph.
- The seam between them is a **snapshot**: when the model changes, the `save`/`render`
  adapter compiles the current project graph into a concrete, immutable render graph
  (instruments + effect chains + routing) and hands it to
  [Machine A](/components/lmms-engine.md) via a lock-free swap. The audio thread reads
  the latest snapshot; it never reads the live model.

# Why it matters

This is exactly the line Void Core's `what-voidcore-is-not.md` draws: *"if Void Core
starts running the game logic / doing the math, we have drifted."* Here the temptation
is real — it would be "convenient" to let the audio callback read a rune directly. That
would couple human-speed editing to hard-real-time and is forbidden. The
[reducer](/concepts/reducer.md) (or, in v1, a hand-written flattener) produces the
snapshot off-thread; the engine only ever consumes it.

# Status

`planned`. Stated now so the architecture is never violated later.
