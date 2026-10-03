---
type: Component
title: LMMS engine
description: The harvested LMMS audio engine, DSP, and plugin host — the host that computes. Its data model and Qt UI are discarded.
resource: null
tags: [status:planned, audience:dev, confidence:asserted]
timestamp: 2026-06-27T00:00:00Z
---

[LMMS](https://github.com/LMMS/lmms) is harvested for its **DSP + plugin host** only. The
[node pivot](/concepts/node-graph.md) changed the calculus: a *timeline* DAW is a poor base
for a *node* DAW, so we keep less of LMMS than the original "fork & gut" implied — but the
author prioritizes **VST support**, and LMMS's plugin hosting is the reason it stays in the
picture at all.

| LMMS layer | decision | why |
|---|---|---|
| **VST/LADSPA host + DSP building blocks** (C++) | **HARVEST** | VST hosting is a priority; not worth rewriting. The backend that *streams*. |
| Audio engine | **DRIVE AS A GRAPH** | expose its buffer-summing as the runtime our [node graph](/concepts/node-graph.md) compiles into; ignore its timeline scheduling |
| **Sound content: bundled synths, samples, presets, soundfonts** | **HARVEST** | LMMS ships a huge library of default sounds, samples, and instrument presets, plus its native synths (Triple Oscillator, ZynAddSubFX, sfxr, …). VLS wants that content day one — a DAW with no sounds makes no music. Licensing per item (GPL for code, various for content) checked at harvest time. |
| Project / data model (song/track/pattern) | **DISCARD** | replaced by the [Void Core spine](/components/voidcore-spine.md) + node graph |
| Qt GUI | **DISCARD** | replaced by our [own UI](/components/own-ui.md) (a node editor) |

# Credit where due

Void Loops takes far more from LMMS than a code trick — the plugin host, DSP blocks, and
a large sound/sample/preset library are years of that community's work. **LMMS is credited
prominently**: in this bundle, in the app's about/credits surface once one exists, and in
the README — linking [github.com/LMMS/lmms](https://github.com/LMMS/lmms) and
[lmms.io](https://lmms.io/). The harvested content also makes the **sample-library
holiday** ([instrument as holiday](/concepts/instrument-as-holiday.md)) concrete: LMMS's
library is the first corpus it browses.

# Granularity: coarse nodes, not Pure Data

A reference engine like **Pure Data / libpd** (BSD) is a clean dataflow audio graph and a
fine study target, but "way too pure" for this project — the author does **not** want every
knob as a node. Nodes are coarse and musical (a sample-clip node, a MIDI node, a VST
instrument node), so LMMS's *device-level* instruments/effects are a better fit than PD's
primitives. See [node types](/concepts/node-types.md).

# The code spike (2026-07-07) — answered; the harvest plan REVISED

Shallow clone surveyed at `Documents/Projects/lmms`. The findings change the plan
*favorably*: less to fork, cleaner seams than assumed.

1. **VST hosting is out-of-process already.** LMMS runs each VST in a separate
   executable — `RemoteVstPlugin(32|64)` (`plugins/VstBase/RemoteVstPlugin.cpp`) —
   talking to an in-process proxy (`VstPlugin`) over **QProcess + a shared-memory float
   buffer + a socket protocol** (`plugins/VstBase/communication.h`,
   `include/RemotePlugin*.h`). The in-process side is Qt/LMMS-coupled
   (`JournallingObject`, `Knob` — UI!), but the **remote side + the wire protocol is
   the clean seam**. So: **harvest the protocol, not the engine** — VLS implements its
   own small client speaking shm+socket to a reused `RemoteVstPlugin` executable. That
   client *is* the [compute holiday](/concepts/instrument-as-holiday.md); no Qt in our
   process, no `AudioEngine` fork needed for the first VST slice.
2. **The engine can wait.** `src/core/AudioEngine*` (worker threads, buffer manager) is
   the "drive as a graph" target, but the trivial backend + remote-VST client covers
   instruments before we ever need it. "Fork & gut" softens to **protocol-first,
   engine-later**.
3. **Native instruments are per-plugin harvests.** TripleOscillator, ReverbSC, Delay,
   Eq, Sf2Player, ZynAddSubFX, Stk, Sfxr… are `Plugin` subclasses on a moderately
   narrow `Instrument` interface; several wrap third-party DSP libraries takeable
   directly. Cherry-pick per node kind when wanted, not wholesale.
4. **The sound library is real and immediately usable.** `data/samples` = 7.6 MB
   (drums, basses, beats, latin, stringsnpads, waveforms…), `data/presets` = 11 MB,
   plus `wavetables/`. Formats: **764 `.ds` DrumSynth** (text synth definitions — a
   future native-synth harvest of their own), 181 ogg, 33 flac, **26 wav**. The WAVs
   play through VLS's sampler **today** (verified live: `shapes/additive.wav` rendered
   through `sampler` → `output`); ogg/flac need a decode step at the library boundary.
   Licensing: GPLv2 overall; per-item check at redistribution time.

# The RemotePlugin wire protocol, mapped (2026-07-07 — the client design)

Read from `include/RemotePluginBase.h` + `plugins/VstBase/communication.h`. On Windows
the transport is LMMS's own **shared-memory FIFO** (`SYNC_WITH_SHM_FIFO`): a keyed shm
ring buffer (`SHM_FIFO_SIZE`, start/end pointers) guarded by two **system semaphores**
(data + message) — no Qt, no sockets on the win32 path. The host (master) creates an
**in** and an **out** FIFO and passes their keys to the spawned
`RemoteVstPlugin(32|64).exe` as `argv[1]`/`argv[2]`.

- **Handshake:** spawn exe with FIFO keys → `IdVstLoadPlugin(path)` +
  `IdSampleRateInformation` + `IdBufferSizeInformation` → wait `IdInitDone`.
- **Audio channel:** a separate large shm block (float frames, in+out) whose key is
  announced with `IdChangeSharedMemoryKey`.
- **Render loop:** write input frames + queue `IdMidiEvent`s → `IdStartProcessing` →
  wait `IdProcessingDone` → read output frames. Params/presets via
  `IdVstGetParameterDump` / `IdVstSetParameterDump` / `IdVstSetProgram` etc.
  (`VstRemoteMessageIDs`, `IdUserBase = 64`).

All of this is implementable from Python with `ctypes` (CreateFileMapping /
CreateSemaphore) — **the VLS-side client is a pure-Python compute holiday, no C++
build needed on our side.** Prerequisite: a **built** `RemoteVstPlugin` executable —
we have LMMS *source* only; the exe ships with an LMMS install (or a one-off build of
just `plugins/VstBase`). Real VST2 plugins exist on this machine to host (OTT,
FL Studio VSTi in `Program Files/Common Files/VST2`).

**THE CLIENT IS BUILT AND VERIFIED (2026-07-07, same day).** LMMS 1.2.2 installed via
winget (the exe); the protocol re-read from the **stable-1.2 headers matching it**
(Qt-5 kernel objects — master's Qt-free rewrite differs); and
`voidloops/vsthost.py` speaks it end-to-end in **pure Python (ctypes)**: Qt name
mangling (`qipc_sharedmemory_/qipc_systemsem_` + SHA1), the shm-FIFO struct
(32-byte `sem32_t` unions, ptrs at +64/+68, data at +72), string-typed message
framing, the third argv (`headless` embed method), the float audio shm, and the
`IdStartProcessing`/`IdProcessingDone` block loop. **Verified live with a real
commercial plugin:** Xfer Records **OTT** (`XfTT` v1260) loads, reports 2-in/2-out,
processes stereo blocks, takes MIDI without wedging, and shuts down clean
(`tests/test_vsthost.py`). This *is* the compute holiday's transport; wiring it
behind the `vst-instrument`/`vst-effect` glyphs in the render backend is the next
slice (per-note MIDI scheduling + block streaming).

# Status

`planned`. No fork taken yet; this records the intended harvest, revised for the node pivot.
