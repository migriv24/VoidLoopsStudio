"""
Step-6 harvest tests: the two boundaries that make LMMS's content usable —
the ffmpeg decode step (ogg/flac samples) and the MIDI-file reader (`midi-in`).

Uses the real LMMS clone when present (skips those cases gracefully when not).

Runnable via `pytest` or `python tests/test_harvest.py`.
"""
from __future__ import annotations

import struct
from pathlib import Path

from voidloops import VoidLoopsProject, compile_render
from voidloops.backend import render_samples
from voidloops.midi import read_midi_notes

LMMS = Path("C:/Users/migri/Documents/Projects/lmms")


def _write_test_midi(path: Path) -> Path:
    """Format-0 SMF, division 480: C4 at 0 for a quarter, E4 at 1 beat for a half,
    with a running-status pair and a vel-0 note-off."""
    def vlq(n):
        out = [n & 0x7F]
        n >>= 7
        while n:
            out.insert(0, 0x80 | (n & 0x7F))
            n >>= 7
        return bytes(out)

    ev = b"".join([
        vlq(0), bytes([0x90, 60, 100]),          # C4 on
        vlq(480), bytes([0x80, 60, 64]),         # C4 off after 1 beat
        vlq(0), bytes([0x90, 64, 90]),           # E4 on (new status)
        vlq(960), bytes([64, 0]),                # E4 off via running-status vel-0
        vlq(0), bytes([0xFF, 0x2F, 0x00]),       # end of track
    ])
    track = b"MTrk" + struct.pack(">I", len(ev)) + ev
    header = b"MThd" + struct.pack(">IHHH", 6, 0, 1, 480)
    path.write_bytes(header + track)
    return path


def test_midi_reader_scales_to_project_ticks(tmp_path: Path):
    mid = _write_test_midi(tmp_path / "riff.mid")
    notes = read_midi_notes(mid, ppqn=96)        # 480 -> 96: scale 0.2
    assert notes == [
        {"pitch": 60, "start": 0, "length": 96, "velocity": 100},
        {"pitch": 64, "start": 96, "length": 192, "velocity": 90},
    ]


def test_midi_in_node_is_a_real_event_source(tmp_path: Path):
    mid = _write_test_midi(tmp_path / "riff.mid")
    with VoidLoopsProject() as proj:
        proj.new_pattern("patch")
        src = proj.add_node("midi-in", path=str(mid))
        osc = proj.add_node("osc", wave="sine")
        out = proj.add_node("output", gain=1)
        proj.wire(src, osc)                      # events -> events, type-checked
        proj.wire(osc, out)
        snap = compile_render(proj)
        v = snap["voices"][0]
        assert v["sequencer"]["name"] == "midi-in1"
        assert [n["pitch"] for n in v["notes"]] == [60, 64]
        assert [n["start_s"] for n in v["notes"]] == [0.0, 0.5]   # beats survived
        samples = render_samples(snap)
        assert len(samples) > 0 and max(abs(s) for s in samples) > 0.1


def test_lmms_ogg_drum_plays_through_the_sampler():
    ogg = LMMS / "data/samples/drums/bassdrum01.ogg"
    if not ogg.exists():
        print("      (skipped: LMMS clone not present)")
        return
    with VoidLoopsProject() as proj:
        proj.new_pattern("patch")
        seq = proj.add_node("sequencer")
        smp = proj.add_node("sampler", root=60)
        src = proj.add_node("sample-in", path=str(ogg), gain=1)
        out = proj.add_node("output", gain=1)
        proj.wire(seq, smp, dst_port="notes")
        proj.wire(src, smp, dst_port="sample")
        proj.wire(smp, out)
        for i in range(4):                       # four-on-the-floor
            proj.add_note("C4", i * 96, 48, node=seq)
        samples = render_samples(compile_render(proj))
        assert max(abs(s) for s in samples) > 0.1
        # each beat hits: energy at the head of every quarter
        for i in range(4):
            beat = samples[int(i * 0.5 * 44100):int((i * 0.5 + 0.1) * 44100)]
            assert max(abs(s) for s in beat) > 0.05, f"beat {i} silent"


def test_decode_error_is_honest(tmp_path: Path):
    bad = tmp_path / "noise.ogg"
    bad.write_bytes(b"this is not audio")
    with VoidLoopsProject() as proj:
        proj.new_pattern("patch")
        src = proj.add_node("sample-in", path=str(bad), gain=1)
        out = proj.add_node("output", gain=1)
        proj.wire(src, out)
        try:
            render_samples(compile_render(proj))
            assert False, "expected ValueError"
        except ValueError as e:
            assert "decode failed" in str(e)


if __name__ == "__main__":
    import tempfile

    with tempfile.TemporaryDirectory() as d:
        tp = Path(d)
        test_midi_reader_scales_to_project_ticks(tp)
        print("[ok ] midi_reader_scales_to_project_ticks")
        test_midi_in_node_is_a_real_event_source(tp)
        print("[ok ] midi_in_node_is_a_real_event_source")
        test_lmms_ogg_drum_plays_through_the_sampler()
        print("[ok ] lmms_ogg_drum_plays_through_the_sampler")
        test_decode_error_is_honest(tp)
        print("[ok ] decode_error_is_honest")
    print("\nSTEP 6 HARVEST: ALL OK")
