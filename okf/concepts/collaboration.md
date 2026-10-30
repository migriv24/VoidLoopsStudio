---
type: Concept
title: Collaboration — private, bounced and shared music
description: What it means for several devices to work on one node-graph DAW, rebuilt on what the family now has (Void Palabra's sync, Void Maiz's networking line, Reticulum on the LAN). Three postures for a project (local, hosted, joined) and three sharing levels for a Loop (private, bounced, shared); what crosses the wire and what never does; why the compute boundary makes VSTs the hard case; the shared clock as a fourth channel; and what a phone is for.
tags: [status:planned, audience:dev, confidence:asserted, foundation]
timestamp: 2026-10-04T00:00:00Z
---

> Written 2026-10-04 during the catch-up (see [roadmap](/roadmap.md), *Catch-up
> phase*). The author: *"there should be like a 'local music only' mode, or like
> 'private music' and then 'collaborative music'."* Nothing here is built. It is
> the conceptual layer the networking work will be built against, and every rule
> in it leans on something a sibling has already built and measured.

# What the family already decided, which we inherit rather than redesign

- **The ownership line** (Void Maiz Q30, 2026-09-18): *Void Maiz owns what
  networking looks like; Void Palabra owns what networking is; the application
  answers one question: "may this rune leave this device?"* VLS's whole share
  of the networking problem is that question, answered musically. That, plus
  the musical clock (§5).
- **Convergence is a property of the state, not of history** (Palabra). Two
  devices exchange whole exportable documents; the merge is commutative,
  associative and idempotent; a conflict is a value, never an error. Loss,
  duplication, reordering and partitions are tested.
- **Three channels** (Maiz, collaborative canvas §2): *committed* (the document,
  synced), *in flight* (presence: cursors, drag ghosts, claims; ephemeral, never
  merged), *local* (`config`: camera, panels; never synced).
- **LAN means Reticulum on the LAN** (family direction 2026-09-23). Maiz's
  `RnsSession` carries Palabra sessions over Reticulum's UDP interface: sealed
  bytes, discovery by announce, a person presses *Allow*, a device let in once is
  known again by proven identity. Interaction Combinators runs on it today,
  desktop ↔ desktop, with an Android build.

# 1. Two axes: the project's posture, and each Loop's level

The author's "local only / private / collaborative" is really two questions,
and keeping them apart is what makes the answer simple.

## 1.1 The project's posture (per device, never synced)

| posture | what runs | what a peer can learn |
|---|---|---|
| **Local** (default) | no network code at all: no announce, no listener, no replica id minted | nothing. The device is silent |
| **Hosted** | this device founds the session; others ask, a person allows each | what the share filter exports (§2) |
| **Joined** | this device starts **empty** and adopts the host's document | the same, in the other direction |

- **Local is the default and is a real mode, not "networking off".** A Local
  project never mints a replica and never announces. "Local music only" means
  *nothing about this project has ever been offered to anyone*, and that is
  only true if the code path does not exist for it. Turning a project from
  Local to Hosted is a deliberate act with a confirmation that says what will
  become visible.
- **The posture lives in `config`** (`net.posture`), which is peer-local by
  contract. That is correct and not an accident: privacy is decided by the
  **sender** (Maiz networking rule 2), so it must never be a field a peer can
  overwrite.
- **A joiner never seeds.** Maiz learned this the hard way: two devices that
  each create the starter patch mint two ids for one name and conflict forever.
  The VLS starter patch is created only by Local and Hosted projects.

## 1.2 A Loop's sharing level (per Loop, the music-specific part)

A [Loop](/concepts/loop.md) is a whole mantle used as one node, and **Palabra
decides what may leave per mantle and per rune.** So the Loop, our namesake
unit, is also the natural unit of sharing. Each Loop has a level:

| level | the recipe (nodes, notes, params) | the sound | a peer sees |
|---|---|---|---|
| **private** | stays home | stays home | nothing, not even that the Loop exists |
| **bounced** | stays home | leaves, as a rendered file by content hash | a Loop node they can **hear**, **wire** and **reuse**, but not open |
| **shared** | leaves | each peer renders its own | a normal Loop, editable by everyone |

**Bounced is the musically interesting level, and nothing in a document editor
has it.** It is how a musician actually shares an idea before it is ready, the
way you would send someone a bounce of a stem rather than the project file:
*"here's the sound, the patch is mine for now."* It also falls straight out of
pieces we already have: [materialize](/concepts/reducer.md) is the one crossing
from computed sound back into structure, and Palabra moves files by hash, only
to peers who ask, only if the bytes match. A bounced Loop is a `sample-in`-like
node whose content reference is the render's hash and whose provenance names
the private Loop. When the owner edits the Loop, a new bounce is a new hash, and
peers hear the change on their next fetch.

Rules that follow from Palabra's semantics and are worth stating because they
are not intuitive:

- **Moving down a level is not retraction.** *"Withholding is not retraction:
  what was already shared stays where it went"* (Palabra SPEC §11.5). Shared →
  private stops future edits from leaving; it does not unsend the past. The UI
  says so at the moment of the change, not in a manual.
- **A private Loop is never mentioned.** A Loop *node* in a shared graph that
  points at a private mantle would leak the mantle's name. So a Loop node
  inherits the level of what it points at: private → the node is withheld too,
  bounced → the node is exported pointing at the bounce, not the mantle.
- **New Loops start private in a session.** Sketching is private by default;
  publishing is a gesture. This is the inverse of the project default (Local
  until you host) and the same principle: nothing leaves without a decision.
- **One answer for every seam.** The level compiles into Maiz's `ShareFilter`,
  which *is* Palabra's export set, so the sync seam and the presence seam cannot
  disagree about what is private (Maiz networking §4). A private Loop's runes
  never appear in a peer's cursor, selection or "is typing" either.

# 2. What crosses the wire, and what never does

| channel | VLS content | notes |
|---|---|---|
| **committed** | the shared graph (nodes, wires, params, notes), shared Loops, bounced Loops' references, **declared glyphs**, preset and sample *references* by hash | via Palabra `doc` frames |
| **files** | samples, `.fxp` presets, bounces | by content hash, fetched on demand (Palabra §11.4) |
| **in flight** | cursors, selections, drag ghosts, claims, a knob mid-turn | presence; never merged |
| **local** | camera, panels, **audio device, buffer size, monitor volume, VST search paths, library root** | `config` |
| **clock** (new, §5) | tempo phase, play/stop, loop position when jamming | ephemeral, VLS-specific |
| **never** | **the render mantle**, audio buffers, anything the compiler derives | see below |

**The render mantle is peer-local, always.** It is *derived*: each device
compiles its own from the shared graph ([render domain](/concepts/render-domain.md)).
Sharing it would mean every peer's compile is merged with every other peer's,
which is double work at best and a conflict storm at worst. It is excluded from
the export set unconditionally, the same way `config` is. This also settles a
worry carried over from Interaction Combinators: IC rewrites the shared net
concurrently, which is why it needed wire runes and fusion. **VLS never rewrites
the shared graph.** Reduce runs on the private, derived render mantle. So VLS
can keep plain edges for wires; the concurrency problem IC solved does not arise
here.

**Glyphs must be declared to travel.** Today `vls::register_glyphs` registers
the glyph set on each open, as host config. A registered glyph does not cross
the wire (Void Core 0.2.14 §3; Maiz measured `"glyphs":{}` in an exported
state). A peer running a different VLS build would receive runes it cannot
read. The fix is Core's adoption step 3: `glyph declare` the VLS set into the
document, so the meaning travels with the music. This is the first item of the
catch-up because nothing else in this page works without it.

**Audio never crosses in the shared level.** Only the recipe crosses. Every
device renders locally. That is the [compute boundary](/concepts/daw-architecture.md)
applied to the network, and it keeps the wire small: a whole song is a few
kilobytes of graph plus samples fetched once.

# 3. The hard case: a device that cannot render what the graph says

If every device renders locally, every device must be able to render every
node. Samples are fine: they travel by hash. **Plugins are not files you can
send**: they are licensed, platform-specific binaries, and a phone has none.

So "peer B lacks the VST that peer A wired in" is the normal case, not an edge
case, and the design should treat it as such:

1. **Never silent, never broken.** The node shows *"Sonatina Choir: on Ana's
   PC"* and renders silence on B. The graph stays valid. Nobody is blocked from
   editing it.
2. **Bounce on demand.** A peer that *can* render the node renders that node's
   output and offers it by hash, exactly like a bounced Loop. Palabra already
   plans this as a capability declaration (*peer and tier*: `compute: [...]`):
   "which device can run Sonatina Choir" becomes **discovery**, not
   configuration. B then hears the choir, one bounce behind A's latest edit.
3. **Live streaming of one node's audio** across the LAN is the far end of the
   same line, and is research (latency, clock, §5).

Presets: a plugin's state (`.fxp`, which the Python era already writes per node)
must travel **by hash**, so every peer that *does* own the plugin gets the same
sound. Library references (`drums/bassdrum01`) are machine-relative today and
must become content references for the same reason.

# 4. Undo, names and tempo: three old decisions the network changes

- **Undo.** Every merge that changes the document restarts Core's undo history
  (Maiz collaborative canvas §5). Maiz's answer is a per-device stack of
  compensating commands: Ctrl+Z undoes *your* last gesture, refused with a toast
  if someone has since changed the same thing. VLS adopts that unchanged.
- **Names.** Two devices adding "sampler-1" at the same moment mint one name for
  two runes, and wires break. Maiz scopes minted names by a device tag. VLS's
  node naming must go through the same function.
- **Tempo.** On 2026-07-07 BPM became `config` so turning the tempo knob never
  touched undo. **`config` does not sync**, so in a session every device would
  play at its own tempo. BPM has to become content, and Void Core 0.2.14 already
  suggests the shape: a `measure` rune with a real unit. The undo concern is
  answered by the compensating history above. Open question #18.

# 5. The fourth channel: a shared clock

Editing together and **playing** together are different things. A document
editor never needs the second one. For a DAW it is the point.

- **Editing together** needs nothing new. Each device plays (or not) on its own
  transport, like two people editing one document and each pressing play on
  their own copy.
- **Jamming** means everyone hears the same bar at the same moment. That needs
  agreement on a *beat timeline* (tempo + a shared origin) and an estimate of
  each peer's clock offset, not streamed audio. Each device's own engine then
  plays the same position locally. Ableton Link is the reference design for this
  on a LAN. Its license (GPLv2 or a commercial license) does not fit an MIT
  family, so this is either a small sync protocol of our own or a deliberate
  license decision. Open question #19.

The clock is ephemeral, like presence: it is never merged and never persisted.
Whether it rides Palabra's presence kind (newest-wins, TTL) or needs its own
low-latency kind is a question for Palabra once VLS has an engine to measure.

**The realtime boundary holds under all of this.** A merge arriving from a peer
is a model change like any local edit: it triggers a recompile and a lock-free
snapshot swap. The audio thread still never sees the network, the core or a
lock. Void Jelly made the same point about games: model-rate events cross the
line; per-frame state never does.

# 6. What a phone is for

Maiz has a touch layer, a phone layout and an Android build path (IC ships an
APK). Reticulum links a phone and a PC on one Wi-Fi, or through a phone's
hotspot with no router at all. A phone cannot host VSTs. That suggests three
roles, in order of cost:

1. **Remote** for a desktop session: transport, knobs, pads, a mixer, a piano
   roll for one Loop. It is a joined peer with a touch layout, and renders
   nothing itself. Cheapest, and immediately useful in a studio.
2. **Sketchpad**: a Local project on the phone with native nodes only (sampler,
   oscillator, sequence, effects). The sketch is made on the bus and brought into
   the desktop session later as a shared or bounced Loop.
3. **Full peer**: a phone in a jam, rendering what it can and receiving bounces
   for what it cannot (§3).

None of this needs code now. **It needs one decision now: the streaming engine
(native build order milestone 4) must be portable from its first line.**
miniaudio has an AAudio backend, so the engine can be one engine on both
platforms. The RemoteVstPlugin client is Windows-only and belongs behind the
compute holiday, where its absence on a phone is just a missing capability.
Open question #20.

# Open

- **#18** BPM (and other "session meta") from `config` to content.
- **#19** The shared clock: our own small protocol, or a license decision.
- **#20** The phone's first role. Lean: Remote first.
- Not yet asked of Palabra: the compute capability (planned there, not built),
  and whether presence can carry a clock.
