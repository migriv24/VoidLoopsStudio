---
type: Reference
title: Void Core
description: The foundational host-agnostic overlay engine Void Loops is built on. Its own OKF bundle is the authoritative source.
resource: ../VoidCore/okf/index.md
tags: [status:current, audience:dev, audience:library, confidence:verified]
timestamp: 2026-06-27T00:00:00Z
---

**Void Core** is the author's host-agnostic overlay engine: a structural vocabulary
(rune / mantle / domain / holiday / tag), a command dispatcher, a tag system, a scripting
language (Voidscript), and a logging/undo spine — over software written in *any*
language. It does **not** compute the host app's results; it structures and orchestrates
them (the *drift test*). Void Loops applies it to a DAW.

The authoritative description is Void Core's **own OKF bundle** at
`../VoidCore/okf/`. Key concepts Void Loops leans on:

- **rune** — atomic editable unit → a [note](/concepts/note-as-rune.md).
- **mantle** — runes + a rule table over a domain → a [pattern](/concepts/pattern-as-mantle.md).
- **holiday** — interface to a system you don't own → a [VST](/concepts/instrument-as-holiday.md).
- **link / binding** — passive / reactive connections → [routing](/concepts/effect-and-routing.md).
- **domain + adapter** — the output seam → [render](/concepts/render-domain.md).
- **interaction nets** — the math; runes as agents, a mantle as a net, a holiday as a
  boundary port. The deferred **reducer** is Void Core's unbuilt executor → our
  [reducer](/concepts/reducer.md).

# Status

`current` (Void Core exists and is partly built: C core, Python/JS bindings, OKF engine
v0.1). Void Loops is `planned` on top of it.
