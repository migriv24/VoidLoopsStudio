"""
voidloops/model.py — the DAW data model: glyphs, timing, and pure helpers.

This is build-order step 1: the rune/mantle shapes that make Void Core into a DAW.
No audio, no host — just the *structure* (Machine B in `okf/concepts/daw-architecture.md`).

Design decisions fixed here:
- **Time is integer ticks** (PPQN ticks per quarter note). Exact, no float drift — what
  most DAWs store. Conversion to seconds happens only at the render boundary (step 4),
  via `ticks_to_seconds`. See `okf/concepts/note-as-rune.md`.
- **A note is a rune** with glyph `note` and content `{pitch, start, length, velocity}`,
  all integers. `pitch` is a MIDI note number (60 = C4), `start`/`length` are ticks,
  `velocity` is 0–127.
- **Project meta** (ppqn, bpm, time signature) is scalar and lives in `state.config` so it
  persists with the project and round-trips.
"""
from __future__ import annotations

from dataclasses import dataclass

# ── timing constants ──────────────────────────────────────────────────────────────
DEFAULT_PPQN = 96          # ticks per quarter note. 96 divides 2/3/4/6/8/12/16/24/32 —
                           # clean triplets and 32nds. (FL Studio's classic internal PPQ.)
DEFAULT_BPM = 120.0
DEFAULT_BEATS_PER_BAR = 4  # time signature numerator
DEFAULT_BEAT_UNIT = 4      # time signature denominator (4 = quarter-note beats)


@dataclass(frozen=True)
class ProjectMeta:
    """Project-level scalars, persisted in `state.config`."""
    ppqn: int = DEFAULT_PPQN
    bpm: float = DEFAULT_BPM
    beats_per_bar: int = DEFAULT_BEATS_PER_BAR
    beat_unit: int = DEFAULT_BEAT_UNIT

    @property
    def ticks_per_bar(self) -> int:
        # a "beat" here is a quarter note; for non-4 beat units, scale accordingly
        return self.ppqn * 4 * self.beats_per_bar // self.beat_unit


# ── pure timing conversions (used at the render boundary, step 4) ──────────────────
def ticks_to_beats(ticks: int, ppqn: int = DEFAULT_PPQN) -> float:
    return ticks / ppqn


def beats_to_seconds(beats: float, bpm: float = DEFAULT_BPM) -> float:
    return beats * 60.0 / bpm


def ticks_to_seconds(ticks: int, ppqn: int = DEFAULT_PPQN, bpm: float = DEFAULT_BPM) -> float:
    return beats_to_seconds(ticks_to_beats(ticks, ppqn), bpm)


# ── pitch helpers ──────────────────────────────────────────────────────────────────
_SEMITONES = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}


def pitch(name: str) -> int:
    """Parse a scientific note name → MIDI number. C4 = 60 (middle C). Accepts sharps (#)
    and flats (b), e.g. 'A#3', 'Eb5'. Pass an int through unchanged."""
    if isinstance(name, int):
        return name
    s = name.strip()
    letter = s[0].upper()
    if letter not in _SEMITONES:
        raise ValueError(f"bad note name: {name!r}")
    i = 1
    semis = _SEMITONES[letter]
    while i < len(s) and s[i] in "#b":
        semis += 1 if s[i] == "#" else -1
        i += 1
    octave = int(s[i:])
    return (octave + 1) * 12 + semis


def pitch_name(midi: int) -> str:
    """Inverse of `pitch` (always spells with sharps)."""
    names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
    return f"{names[midi % 12]}{midi // 12 - 1}"


# ── content glyphs: things that live *inside* a node ───────────────────────────────
# `fields` drives default content; `ports` is documentary interaction-net metadata
# (principal/aux) for when Reduce is wired — the core stores it but doesn't use it yet.
# A `note` is the atomic unit inside a sequencer node (okf/concepts/note-as-rune.md);
# `automation`/`sample` are param/source content. The timeline-era `pattern-clip` glyph
# was retired by the 2026-06-29 node pivot (okf/concepts/arrangement.md is deprecated).
NOTE_GLYPH = {
    "glyph": "note", "label": "Note", "editor": "piano-roll",
    "fields": ["pitch", "start", "length", "velocity"],
    "ports": {"principal": "to-instrument", "aux": ["mod"]},
}
AUTOMATION_GLYPH = {
    "glyph": "automation", "label": "Automation point", "editor": "automation",
    "fields": ["target", "start", "value"],
    "ports": {"principal": "to-param", "aux": []},
}
SAMPLE_GLYPH = {
    "glyph": "sample", "label": "Sample", "editor": "sample",
    "fields": ["path", "start", "gain"],
    "ports": {"principal": "to-instrument", "aux": []},
}

CONTENT_GLYPHS = [NOTE_GLYPH, AUTOMATION_GLYPH, SAMPLE_GLYPH]


# ── node glyphs: the coarse musical nodes of the signal-flow graph ─────────────────
# Post-pivot, the project is a node graph (okf/concepts/node-graph.md). A node is a rune
# whose glyph fixes its typed *port signature*. Unlike content glyphs (principal/aux),
# node ports are directional and typed: each is an inlet or outlet carrying one of three
# signal types. Wires (core `link`s) may only join ports of the same type — that check
# lives in the app (project.wire), using NODE_KIND below. See okf/concepts/node-types.md.

# signal types a wire can carry
AUDIO = "audio"     # a stream of samples (audio-rate)
EVENTS = "events"   # discrete messages: MIDI notes, param changes (control-rate)
CLOCK = "clock"     # timing pulses that drive time (okf/concepts/time-without-timeline.md)
CONTROL = "control" # plain numbers: parameter values, math/logic plumbing (question #14).
                    # Evaluated once per render today; per-block automation arrives
                    # with streaming playback (roadmap post-prototype item 3).

SIGNAL_TYPES = (AUDIO, EVENTS, CLOCK, CONTROL)


@dataclass(frozen=True)
class Port:
    """One typed inlet or outlet on a node glyph. A `multi` inlet accepts many wires
    (a mix/add node summing several sources); a plain inlet accepts exactly one."""
    name: str
    signal: str          # one of SIGNAL_TYPES
    multi: bool = False


# The fundamental categories (okf/concepts/node-taxonomy.md) — what a kind inherits
# from. Domain-agnostic by design ("categories are domain-agnostic; signal types carry
# the domain"). Landed as code at the VST step per dev-question #11's lean.
INPUT = "input"            # brings outside material in (MIDI file, sample file, mic)
TIME_EVENT = "time-event"  # makes/transforms time and events (clock, sequencer)
GENERATOR = "generator"    # events -> signal; where sound comes into being
TRANSFORM = "transform"    # signal -> signal, statefully (effects)
COMBINE = "combine"        # many -> one (mix)
UTILITY = "utility"        # small value plumbing (added as needed, not speculatively)
LOOP_CAT = "loop"          # composition: a sub-graph as one node
OUTPUT = "output"          # sinks; where the graph meets a domain

CATEGORIES = (INPUT, TIME_EVENT, GENERATOR, TRANSFORM, COMBINE, UTILITY,
              LOOP_CAT, OUTPUT)


@dataclass(frozen=True)
class NodeKind:
    """A node glyph's static shape: its category (the taxonomy layer it inherits
    from), content fields, and typed port signature.

    `params` names the content fields that are BINDABLE (question #14, params as
    ports): each appears as an extra `control` inlet `p:<field>`; a wired param's
    content value is overridden by the control graph at compile time."""
    glyph: str
    label: str
    fields: tuple[str, ...]
    inlets: tuple[Port, ...]
    outlets: tuple[Port, ...]
    editor: str = "node"
    category: str = GENERATOR
    holiday: bool = False      # backed by external code across a holiday (VST, …)
    params: tuple[str, ...] = ()

    def param_ports(self) -> tuple[Port, ...]:
        """The kind's bindable fields as control inlets (`p:<field>`)."""
        return tuple(Port(f"p:{f}", CONTROL) for f in self.params)

    def glyph_def(self) -> dict:
        """The dict registered with the C core. Ports/category ride along as
        documentary metadata (opaque to the core); NODE_KIND is the source of truth."""
        def _p(p: Port) -> dict:
            return {"name": p.name, "signal": p.signal, "multi": p.multi}
        return {
            "glyph": self.glyph, "label": self.label, "editor": self.editor,
            "category": self.category, "fields": list(self.fields),
            "ports": {"in": [_p(p) for p in self.inlets],
                      "out": [_p(p) for p in self.outlets]},
        }


# The node set. The v1 five (first sound) plus the step-6 growth wave (dev-answer 10),
# every kind anchored in its category. Coarse, musical granularity throughout.
NODE_KINDS = [
    # time-event
    NodeKind("clock", "Clock", ("rate",),
             inlets=(), outlets=(Port("clk", CLOCK),), category=TIME_EVENT),
    # length = one cycle in ticks (0/unset: span of its notes); offset = when the
    # sequence enters, in ticks; repeat = cycles to play (0/unset: loop to fill the
    # render window). Looping is the DEFAULT posture (okf: time-without-timeline);
    # a one-shot is repeat=1. These are the first "sequencing sequences" controls —
    # the arrangement-source seam (dev-answer 2 / open question 12) grows here.
    NodeKind("sequencer", "Sequencer", ("length", "offset", "repeat"),
             inlets=(Port("clk", CLOCK),), outlets=(Port("notes", EVENTS),),
             editor="piano-roll", category=TIME_EVENT),
    # The SEQUENCE node (dev-answer 2 / question 12, designed 2026-07-08): the
    # sequencer generalized with a pluggable ARRANGEMENT inLET — `arr` accepts any
    # events source (a midi-in file, another sequencer, another sequence: sequences
    # of sequences, literally) and merges it with the node's own inline notes; then
    # its length/offset/repeat/transpose apply to the whole. `transpose` (semitones)
    # is the first "sequence as a variable" control. Chaining = composition.
    NodeKind("sequence", "Sequence", ("length", "offset", "repeat", "transpose"),
             inlets=(Port("clk", CLOCK), Port("arr", EVENTS, multi=True)),
             outlets=(Port("notes", EVENTS),),
             editor="piano-roll", category=TIME_EVENT,
             params=("transpose",)),
    # The MIDI node (author's ask, 2026-07-08): the DEDICATED piano-roll node — a
    # sequence whose native face is a full in-canvas piano roll (the node-as-window
    # idea: minimize = collapse, maximize = the roll opens inside the node). Same
    # semantics as `sequence` (the render pipeline treats them identically); this is
    # question #13's likely resolution — the kind that subsumes sequencer/sequence.
    NodeKind("midi", "MIDI", ("length", "offset", "repeat", "transpose"),
             inlets=(Port("clk", CLOCK), Port("arr", EVENTS, multi=True)),
             outlets=(Port("notes", EVENTS),),
             editor="piano-window", category=TIME_EVENT,
             params=("transpose",)),
    # generators
    NodeKind("osc", "Oscillator", ("wave", "tuning"),
             inlets=(Port("notes", EVENTS),), outlets=(Port("out", AUDIO),),
             category=GENERATOR, params=("tuning",)),
    NodeKind("sampler", "Sampler", ("root",),      # root = the sample's home pitch
             inlets=(Port("notes", EVENTS), Port("sample", AUDIO)),
             outlets=(Port("out", AUDIO),), category=GENERATOR,
             params=("root",)),
    NodeKind("vst-instrument", "VST Instrument", ("plugin", "preset"),
             inlets=(Port("notes", EVENTS),), outlets=(Port("out", AUDIO),),
             category=GENERATOR, holiday=True),
    # inputs
    NodeKind("sample-in", "Sample", ("path", "gain"),
             inlets=(), outlets=(Port("out", AUDIO),), editor="sample",
             category=INPUT, params=("gain",)),
    NodeKind("midi-in", "MIDI In", ("path",),
             inlets=(), outlets=(Port("notes", EVENTS),), category=INPUT),
    # `time-of-day` (INPUT): the author's north-star example of a sequence meaning
    # more than one thing — wire the wall clock into a transpose, a gain, a map.
    # Emits the local hour as a control value (0.0–24.0). `override` (a number)
    # pins it for reproducible renders/tests; empty = live.
    NodeKind("time-of-day", "Time of day", ("override",),
             inlets=(), outlets=(Port("out", CONTROL),), category=INPUT),
    # transforms
    NodeKind("effect", "Effect", ("type", "amount", "feedback"),
             inlets=(Port("in", AUDIO),), outlets=(Port("out", AUDIO),),
             category=TRANSFORM, params=("amount", "feedback")),
    NodeKind("vst-effect", "VST Effect", ("plugin", "preset"),
             inlets=(Port("in", AUDIO),), outlets=(Port("out", AUDIO),),
             category=TRANSFORM, holiday=True),
    # utility — the math/logic plumbing (question #14's first wave). All operate on
    # `control` values; unwired math/compare inlets fall back to their a/b content
    # fields, so they double as inline constants.
    NodeKind("value", "Value", ("value",),
             inlets=(), outlets=(Port("out", CONTROL),), category=UTILITY),
    NodeKind("math", "Math", ("op", "a", "b"),   # op: add sub mul div min max pow mod
             inlets=(Port("a", CONTROL), Port("b", CONTROL)),
             outlets=(Port("out", CONTROL),), category=UTILITY),
    NodeKind("map", "Map range", ("in_min", "in_max", "out_min", "out_max"),
             inlets=(Port("in", CONTROL),), outlets=(Port("out", CONTROL),),
             category=UTILITY),
    NodeKind("compare", "Compare", ("op", "a", "b"),  # op: lt le gt ge eq ne → 1/0
             inlets=(Port("a", CONTROL), Port("b", CONTROL)),
             outlets=(Port("out", CONTROL),), category=UTILITY),
    # combine / output
    NodeKind("mix", "Mix", ("gain",),
             inlets=(Port("in", AUDIO, multi=True),), outlets=(Port("out", AUDIO),),
             category=COMBINE, params=("gain",)),
    # duration = the render window in ticks (0/unset: auto — last note end). This is
    # what looping sequencers fill; export gates a duration, it never reads a song end.
    NodeKind("output", "Output", ("gain", "duration"),
             inlets=(Port("in", AUDIO),), outlets=(), category=OUTPUT,
             params=("gain",)),
    # The Loop — the app's namesake unit (okf/concepts/loop.md): a whole mantle used as
    # one node. `patch` names the referenced mantle; the node's REAL ports are dynamic —
    # the free (unwired) ports of that inner graph, qualified "<inner-node>.<port>" —
    # resolved by the project/compiler, so the static signature here is empty.
    NodeKind("loop", "Loop", ("patch",),
             inlets=(), outlets=(), editor="patch", category=LOOP_CAT),
]

LOOP_KIND = "loop"
NOTE_KINDS = ("sequencer", "sequence", "midi")   # kinds that hold note-runes

NODE_KIND = {k.glyph: k for k in NODE_KINDS}          # glyph name → NodeKind (wiring lookup)
NODE_GLYPHS = [k.glyph_def() for k in NODE_KINDS]     # dicts to register with the core

# every glyph registered on project open
DAW_GLYPHS = CONTENT_GLYPHS + NODE_GLYPHS

# Provisional interaction-net arities (aux-port count) for the reducer's `signatures`
# map. Not exercised until Reduce is wired; revisit then. See okf/concepts/reducer.md.
SIGNATURES = {"note": 1, "automation": 0, "sample": 0}
