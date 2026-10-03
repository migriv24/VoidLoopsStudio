"""
voidloops/midi.py — a minimal Standard MIDI File reader for the `midi-in` node.

Stdlib-only SMF (format 0/1) parsing: note-on/note-off pairs across all tracks and
channels, merged, as VLS note dicts `{pitch, start, length, velocity}` in **project
ticks** (the file's division is rescaled to the project PPQN).

Deliberate scope (the import policy, a boundary decision not a model rule):
- **The project owns tempo.** SMF tempo events are ignored — imported notes land at
  the project's BPM, like dropping a MIDI clip into a DAW at song tempo. Musical
  *positions* (beats) are preserved exactly via the division→PPQN rescale.
- Note-on with velocity 0 = note-off (the common convention). Unclosed notes get a
  one-beat default length. Other events (CC, pitch bend, meta) are skipped — they
  become interesting when automation lands.
- SMPTE-division files are rejected (rare; musical division only).
"""
from __future__ import annotations

import struct
from pathlib import Path

from .model import DEFAULT_PPQN


def read_midi_notes(path: str | Path, *, ppqn: int = DEFAULT_PPQN) -> list[dict]:
    """All notes of an SMF file, merged across tracks/channels, sorted by
    (start, pitch), in project ticks at `ppqn`."""
    data = Path(path).read_bytes()
    if data[:4] != b"MThd":
        raise ValueError(f"{path}: not a MIDI file (missing MThd)")
    hlen, fmt, ntracks, division = struct.unpack(">IHHH", data[4:14])
    if division & 0x8000:
        raise ValueError(f"{path}: SMPTE-division MIDI not supported")
    scale = ppqn / division
    notes: list[dict] = []
    pos = 8 + hlen
    for _ in range(ntracks):
        if data[pos:pos + 4] != b"MTrk":
            raise ValueError(f"{path}: bad track chunk at byte {pos}")
        tlen = struct.unpack(">I", data[pos + 4:pos + 8])[0]
        notes.extend(_track_notes(data[pos + 8:pos + 8 + tlen], scale, ppqn))
        pos += 8 + tlen
    return sorted(notes, key=lambda n: (n["start"], n["pitch"]))


def _track_notes(track: bytes, scale: float, ppqn: int) -> list[dict]:
    i, tick, running = 0, 0, 0
    open_notes: dict[tuple[int, int], tuple[int, int]] = {}   # (ch,pitch) -> (tick,vel)
    out = []

    def _vlq() -> int:
        nonlocal i
        v = 0
        while True:
            b = track[i]; i += 1
            v = (v << 7) | (b & 0x7F)
            if not b & 0x80:
                return v

    def _close(ch: int, pitch: int, end_tick: int) -> None:
        start, vel = open_notes.pop((ch, pitch), (None, None))
        if start is not None:
            out.append({"pitch": pitch, "start": int(round(start * scale)),
                        "length": max(int(round((end_tick - start) * scale)), 1),
                        "velocity": vel})

    while i < len(track):
        tick += _vlq()
        status = track[i]
        if status & 0x80:
            i += 1
            running = status
        else:
            status = running                    # running status: reuse previous
        kind, ch = status & 0xF0, status & 0x0F
        if kind == 0x90:                        # note on (vel 0 == off)
            pitch, vel = track[i], track[i + 1]; i += 2
            if vel:
                open_notes[(ch, pitch)] = (tick, vel)
            else:
                _close(ch, pitch, tick)
        elif kind == 0x80:                      # note off
            pitch = track[i]; i += 2
            _close(ch, pitch, tick)
        elif kind in (0xA0, 0xB0, 0xE0):        # aftertouch / CC / pitch bend
            i += 2
        elif kind in (0xC0, 0xD0):              # program change / channel pressure
            i += 1
        elif status == 0xFF:                    # meta event
            i += 1                              # type byte
            i += _vlq_len(track, i)
        elif status in (0xF0, 0xF7):            # sysex
            i += _vlq_len(track, i)
        else:
            break                               # unknown: stop parsing this track
    for (ch, pitch), (start, _vel) in list(open_notes.items()):
        _close(ch, pitch, start + int(ppqn / scale))          # unclosed: one beat
    return out


def _vlq_len(track: bytes, i: int) -> int:
    """Length-prefixed payload: returns bytes consumed (the VLQ itself + payload)."""
    n, used = 0, 0
    while True:
        b = track[i + used]; used += 1
        n = (n << 7) | (b & 0x7F)
        if not b & 0x80:
            return used + n
