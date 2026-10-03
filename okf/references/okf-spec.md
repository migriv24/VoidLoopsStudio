---
type: Reference
title: OKF spec
description: The Open Knowledge Format v0.1 — the format this bundle conforms to. Authoritative copy lives with Void Core.
resource: C:/Users/migri/Documents/Projects/VoidCore/okf/references/okf-spec.md
tags: [status:current, audience:dev, confidence:asserted]
timestamp: 2026-06-27T00:00:00Z
---

This bundle conforms to the **Open Knowledge Format v0.1**: a directory of markdown
concepts, each `type`d YAML-frontmatter + body, cross-linked by ordinary markdown links
(dangling links are legal — "not-yet-written knowledge"). Reserved filenames: `index.md`,
`log.md`. Honesty lives in `tags` (`status:` / `audience:` / `confidence:`).

The authoritative spec and the reference engine live with
[Void Core](/references/void-core.md) at
`C:/Users/migri/Documents/Projects/VoidCore/okf/references/okf-spec.md` and
`C:/Users/migri/Documents/Projects/VoidCore/holidays/okf/`. Void Loops' bundle is a
standard OKF bundle: Void Core's OKF engine exposes it as data (`ls`/`get`/`query`/
`validate`/`analyze`), and FaultSack studies it visually (the stock `viz.html` viewer was
retired in the core's cleanup pass).

# Status

`current` (the format). See Void Core's `okf/design/okf-design.md` for the full design
rationale (the old `notes/` folder was absorbed into `okf/design/`).
