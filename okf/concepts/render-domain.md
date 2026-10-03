---
type: Concept
title: Render domain
description: Playback and export are the Void Core domain (the output target) plus a render adapter. "deploy" = render the song to WAV; the same adapter feeds the soundcard for live playback.
resource: notes/render-domain.md
tags: [status:planned, audience:dev, audience:library, confidence:asserted]
timestamp: 2026-06-27T00:00:00Z
---

In Void Core a [domain](/references/void-core.md) is "the base a mantle renders/deploys
onto" — and SPEC §3.5 already says *a domain need not be a website; it can be an
output/distribution target.* For Void Loops the domain is the **audio output**.

# The mapping

- **Domain** = the render target: a soundcard (live playback) or a file (bounce).
- **The effect-handler seam** = `vc.set_effect_handler(fn)` where `fn(op, args)` routes a
  `render`/`play` op out to the host audio backend. This is **bound in Void Core as of
  2026-06-28** — the holiday seam all real I/O crosses. The generic `effect <op>` verb
  reaches it from the dispatcher. The render target itself is an **output holiday** (one of
  Void Core's named holiday kinds) — see decision #1 in
  [developer questions](/developer_questions.md).
- **Compile the render graph** = [Scry](/concepts/reducer.md)/`expand` the
  [node graph](/concepts/node-graph.md) into the concrete graph the backend pulls (the
  immutable snapshot of the [realtime boundary](/concepts/realtime-boundary.md)), off the
  audio thread.
- **render / playback** = pull the **[output node](/concepts/node-types.md)** for samples;
  the handler runs the backend (initially a trivial built-in synth; later the harvested
  [LMMS engine + VST host](/components/lmms-engine.md)) to a WAV, or block-by-block to the
  soundcard. A "final result" is the output node over a **gated interval** — there is no
  timeline length, so export gates a duration (or stops) rather than reading a song end.

So "export to WAV" and "hit play" are one code path with two sinks — and both are the
host computing, directed by the overlay across the now-bound effect seam.

# Generated sound is its own mantle — the render mantle (decided 2026-07-06)

The author's intuition (dev-answer 9): a compute holiday essentially creates **new runes
on a different mantle** — if the sound playing on the audio device is itself thought of as
a mantle, generated sound is a *separate* mantle from the arrangement. **Adopted**, with
the boundary drawn so it stays mathematically consistent and speaker-safe:

- **The render mantle is the flattened snapshot.** The compile step (arrangement mantle
  →Scry/Reduce→ concrete pull-graph) already produces a second net; we now name it: the
  **render mantle**. It *describes* what is sounding — generated/expanded runes with
  [provenance](/concepts/reducer.md) back to their arrangement sources. The compute
  holiday generates *into this description*.
- **Sample buffers never become runes implicitly.** The actual audio stays transient,
  host-side stream data — the drift test holds (the core describes; the host computes).
  A wrong graph therefore yields a wrong *description*, never a rogue buffer.
- **materialize is the one crossing.** Generated sound becomes *owned* runes (a `sample`
  rune with provenance, in a mantle you keep) only through the explicit, undoable
  materialize step — never as a side effect of playback.
- **Speakers are protected at the boundary, not by the math.** The output holiday carries
  the tier-3 limiter/clamp [policy](/concepts/rules-and-reversibility.md); nothing in
  mantle space can push gain into hardware.

Consistency check: arrangement →(pure layers)→ render mantle →(output holiday)→ host
stream. Both mantle-side arrows are pure and information-preserving (provenance = the
inverse trail); the only lossy, effectful step is the host's, at the seam. This also
answers "a note is not one thing" ([instrument as holiday](/concepts/instrument-as-holiday.md)):
the note-rune lives in the arrangement mantle; its sounded form is a rune in the render
mantle; the holiday relates them.

# Status

**`current` (2026-07-06) for the v1 slice** — `resource:` `voidloops/render.py` (compile →
render mantle → snapshot) + `voidloops/backend.py` (the trivial synth: WAV bounce, preview
playback, the tier-3 limiter) behind `attach_trivial_backend()` /
`vc.set_effect_handler` (`voidloops/project.py`); verified acoustically in
`tests/test_sound.py`. `planned`: the LMMS/VST backend behind the same seam, and gated/
streaming (block-by-block) rendering — today's backend bounces the whole snapshot.
