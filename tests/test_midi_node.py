"""
The dedicated MIDI node (author's ask, 2026-07-08): a `sequence`-semantics node
whose native face is a full in-canvas piano roll (the node-as-window idea).
Model + render side here; the windowed editor face lives in editor.html.

Runnable via `pytest` or `python tests/test_midi_node.py`.
"""
from __future__ import annotations

import json
import threading
import urllib.request

from voidloops import VoidLoopsProject
from voidloops.render import compile_render


def test_midi_holds_notes_and_renders():
    with VoidLoopsProject() as proj:
        proj.new_pattern("song")
        clk = proj.add_node("clock")
        mid = proj.add_node("midi")
        osc = proj.add_node("osc")
        out = proj.add_node("output", duration=384)
        proj.wire(clk, mid, dst_port="clk")
        proj.wire(mid, osc)
        proj.wire(osc, out)
        for i, p in enumerate(["C4", "E4", "G4", "C5"]):
            proj.add_note(p, i * 96, 96, node=mid)
        assert [n["pitch"] for n in proj.notes(node=mid)] == [60, 64, 67, 72]
        snap = compile_render(proj)
        v = snap["voices"][0]
        assert v["sequencer"]["name"] == mid          # the midi node drives the voice
        assert [n["pitch"] for n in v["notes"]] == [60, 64, 67, 72]


def test_midi_composes_like_sequence():
    """arr composition + transpose: the midi node IS a sequence (question #13's
    likely resolution — one kind, richer face)."""
    with VoidLoopsProject() as proj:
        proj.new_pattern("song")
        clk = proj.add_node("clock")
        inner = proj.add_node("sequencer")
        mid = proj.add_node("midi", transpose=12)
        osc = proj.add_node("osc")
        out = proj.add_node("output", duration=384)
        proj.wire(clk, mid, dst_port="clk")
        proj.wire(inner, mid, dst_port="arr")
        proj.wire(mid, osc)
        proj.wire(osc, out)
        proj.add_note("C4", 0, 96, node=inner)
        proj.add_note("E4", 96, 96, node=mid)         # inline + arr merge
        snap = compile_render(proj)
        pitches = sorted({n["pitch"] for n in snap["voices"][0]["notes"]})
        assert pitches == [72, 76]                    # both up an octave


def test_midi_notes_ride_the_state():
    from voidloops.ui import make_server
    with VoidLoopsProject() as proj:
        proj.new_pattern("song")
        mid = proj.add_node("midi")
        proj.add_note("A4", 0, 96, node=mid)
        httpd = make_server(proj, port=0)
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        try:
            base = f"http://127.0.0.1:{httpd.server_address[1]}"
            with urllib.request.urlopen(base + "/state") as r:
                state = json.loads(r.read().decode())
            n = next(x for x in state["nodes"] if x["kind"] == "midi")
            assert [t["pitch"] for t in n["notes"]] == [69]
            kind = next(k for k in state["kinds"] if k["kind"] == "midi")
            assert kind["editor"] == "piano-window"   # the page keys the face on this
            # param inlets ride along, flagged
            p = next(x for x in kind["inlets"] if x["name"] == "p:transpose")
            assert p["signal"] == "control" and p["param"] is True
        finally:
            httpd.shutdown()


if __name__ == "__main__":
    for name, fn in [
        ("midi_holds_notes_and_renders", test_midi_holds_notes_and_renders),
        ("midi_composes_like_sequence", test_midi_composes_like_sequence),
        ("midi_notes_ride_the_state", test_midi_notes_ride_the_state),
    ]:
        fn()
        print(f"[ok ] {name}")
    print("\nMIDI NODE: ALL OK")
