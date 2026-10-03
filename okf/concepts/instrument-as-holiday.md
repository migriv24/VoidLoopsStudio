---
type: Concept
title: Instrument as holiday
description: A VST/synth/sampler is external code you don't own, reached over a plugin protocol — exactly Void Core's holiday (boundary port).
resource: notes/instrument-as-holiday.md
tags: [status:planned, audience:dev, audience:library, confidence:asserted, foundation]
timestamp: 2026-06-27T00:00:00Z
---

A **VST / synth / sampler** is third-party code Void Loops does not own, reached over a
protocol (VST3 / CLAP / LADSPA). That is the textbook definition of a Void Core
[holiday](/references/void-core.md) = a **free / boundary port** of the net: the place a
mantle wires *out* to another net it does not reduce. The author felt this directly
("VSTs give me vibes of being holidays") — interaction-net theory confirms it.

# The holiday interface, for an instrument

Void Core's holiday surface (`query`/`get`/`insert`/`describe`) specializes to:

```
describe()        -> { name, params, ports: {midi_in, audio_out}, kind: instrument }
get(paramRef)     -> a parameter value / preset
insert(midi)      -> feed MIDI/notes for a render window   (the "play" direction)
```

The audio actually rendered crosses the [realtime boundary](/concepts/realtime-boundary.md):
the model *describes* the wire (this pattern's notes go to this instrument); the
[engine](/components/lmms-engine.md) *runs* the plugin on the audio thread.

# Samples too

A raw **sample** is either: (a) content on a `sample` rune pointing at a file (owned,
the engine plays it), or (b) a whole **sample library** modeled as a query-backed mantle
over a folder — a [holiday](/references/void-core.md) you browse by tag. Both are
planned; v1 needs only one instrument holiday to prove the boundary.

# Holiday kinds (the audio backend, named) — decided 2026-07-06

Void Core's holiday concept explicitly enumerates **compute** and **output** kinds, which
sorts the whole audio backend cleanly: **rendering to speakers/file** is an **output
holiday** (see [render domain](/concepts/render-domain.md)), and — per the author's
dev-answer 1 — the **compute holiday is where VST implementation begins**: a VST is
external code that *computes things into runes/streams*, so it is conceptualized as a
compute holiday from the start (not deferred until self-hosted DSP exists).

# Holidays as generators (the author's framing, 2026-07-06)

The author's reading, worth keeping in front of us: a holiday is not just a
"generalizable API" — it is a **generator**. Runes are elemental; mantles are runes
interacting; **holidays generate** — MIDI+VST generate note-runes, and a compute holiday
generates *the sounded version* of a note. Which surfaces something real: **a note is not
one thing.** The note-rune on a sequencer and the generated sound of that note are
different entities (possibly different rune types — open), related through the holiday
that computes one from the other. This framing is really about Void Core itself, and has
been passed upstream to the core (VLS uses the core; it doesn't redesign it) — see the
message logged 2026-07-06. For VLS the practical consequence stands: **start VST work at
the compute-holiday seam, thinking of it as the thing that generates sound-runes from
note-runes.**

# Further reading (external background)

- [VST](https://en.wikipedia.org/wiki/Virtual_Studio_Technology) ·
  [CLAP](https://en.wikipedia.org/wiki/CLAP_%28audio_plugin_standard%29) ·
  [LADSPA](https://en.wikipedia.org/wiki/LADSPA) — the plugin protocols a holiday speaks.
- [Software sampler](https://en.wikipedia.org/wiki/Sampler_%28musical_instrument%29) — for
  the sample/sampler node.

# Status

**`current` (2026-07-08) — the compute holiday is real.** `resource:`
`voidloops/vsthost.py`: the pure-Python client for LMMS's out-of-process
`RemoteVstPlugin` host (the 1.2.2 shm-FIFO protocol; PE-bitness detection auto-picks
the 32/64-bit exe; denormal-guard input; graceful degradation on plugin death). Real
plugins verified: Xfer OTT (effect) and the author's Sonatina Choir (instrument,
MIDI-scheduled per note). The **sample library** is also real (`voidloops/library.py`
over LMMS's corpus, refs resolved at the load boundary).

**The plugin's own window is real too (2026-07-08, "VST nodes as windows"):**
`VstUiSession` spawns the remote with embed method `none` — the VST's native editor
as a detached window (`IdShowUI`) — with a daemon pump draining the remote's
messages so knob-twisting never wedges the FIFO. `save_preset`/`load_preset`
(`IdSavePresetFile`/`IdLoadPresetFile`, standard `.fxp` — works for chunk AND
plain-parameter plugins) bake the knob state into the node's `preset` field, which
every render-side instance loads back (`backend._load_preset`;
`tests/test_vsthost.py::test_preset_roundtrip` with OTT). Still `planned`: VST3/CLAP
(the remote host is VST2-only), **VST params as `p:` ports** (question #14b — the
protocol exposes parameter dumps), and Void Core's holiday *registry* formalizing
these as named holidays.
