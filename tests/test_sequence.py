"""
Sequence-node tests (question 12, designed 2026-07-08): the sequencer generalized
with a pluggable arrangement inlet — sequences of sequences, transpose as the first
"sequence as a variable" control — plus the LMMS sound library + add_instrument.

Runnable via `pytest` or `python tests/test_sequence.py`.
"""
from __future__ import annotations

from pathlib import Path

from voidloops import VoidLoopsProject, compile_render
from voidloops import library
from voidloops.backend import render_samples

from test_harvest import _write_test_midi

PPQN = 96


def test_sequence_merges_inline_and_arr_sources(tmp_path: Path):
    mid = _write_test_midi(tmp_path / "riff.mid")     # C4@0 1 beat, E4@1 2 beats
    with VoidLoopsProject() as proj:
        proj.new_pattern("patch")
        midi = proj.add_node("midi-in", path=str(mid))
        seq = proj.add_node("sequence", repeat=1)
        osc = proj.add_node("osc", wave="sine")
        out = proj.add_node("output", gain=1)
        proj.wire(midi, seq, dst_port="arr")
        proj.wire(seq, osc)
        proj.wire(osc, out)
        proj.add_note("G4", 3 * PPQN, PPQN, node=seq)  # inline, after the file's riff
        snap = compile_render(proj)
        notes = snap["voices"][0]["notes"]
        assert [(n["pitch"], n["start"]) for n in notes] == \
            [(60, 0), (64, 96), (67, 288)]             # file + inline, merged in time


def test_sequences_of_sequences_with_transpose():
    with VoidLoopsProject() as proj:
        proj.new_pattern("patch")
        riff = proj.add_node("sequence", length=2 * PPQN, repeat=1)
        proj.add_note("C4", 0, PPQN, node=riff)
        proj.add_note("E4", PPQN, PPQN, node=riff)
        # the outer sequence CONSUMES the riff: repeats it twice, up a fifth
        outer = proj.add_node("sequence", length=2 * PPQN, repeat=2, transpose=7)
        osc = proj.add_node("osc", wave="sine")
        out = proj.add_node("output", gain=1)
        proj.wire(riff, outer, dst_port="arr")
        proj.wire(outer, osc)
        proj.wire(osc, out)
        snap = compile_render(proj)
        notes = snap["voices"][0]["notes"]
        assert [(n["pitch"], n["start"]) for n in notes] == \
            [(67, 0), (71, 96), (67, 192), (71, 288)]  # G4/B4, cycled twice
        assert render_samples(snap)                    # and it sounds


def test_event_cycle_rejected():
    with VoidLoopsProject() as proj:
        proj.new_pattern("patch")
        a = proj.add_node("sequence")
        b = proj.add_node("sequence")
        osc = proj.add_node("osc")
        out = proj.add_node("output", gain=1)
        proj.wire(a, b, dst_port="arr")
        proj.wire(b, a, dst_port="arr")                # a → b → a: legal to draw…
        proj.wire(b, osc, src_port="notes")
        proj.wire(osc, out)
        proj.add_note("C4", 0, PPQN, node=a)
        try:
            compile_render(proj)                       # …but the compiler refuses
            assert False, "expected ValueError"
        except ValueError as e:
            # a cycle that also reaches the output necessarily fans out, so either
            # guard may fire first — the point is the structural refusal
            assert "cycle" in str(e).lower() or "fan-out" in str(e).lower()


def test_library_search_and_instrument():
    if not any(d.is_dir() for d in library.LIBRARY_DIRS):
        print("      (skipped: no LMMS sample library present)")
        return
    hits = library.search("bassdrum")
    assert hits and all("bassdrum" in h["ref"] for h in hits)
    assert "drums" in library.categories()
    with VoidLoopsProject() as proj:
        proj.new_pattern("patch")
        smp = proj.add_instrument(hits[0]["ref"])
        seq = proj.add_node("sequencer", repeat=1)
        out = proj.add_node("output", gain=1)
        proj.wire(seq, smp, dst_port="notes")
        proj.wire(smp, out)
        proj.add_note("C4", 0, PPQN, node=seq)
        samples = render_samples(compile_render(proj))
        assert max(abs(s) for s in samples) > 0.05     # the library drum hits


if __name__ == "__main__":
    import tempfile

    with tempfile.TemporaryDirectory() as d:
        test_sequence_merges_inline_and_arr_sources(Path(d))
    print("[ok ] sequence_merges_inline_and_arr_sources")
    test_sequences_of_sequences_with_transpose()
    print("[ok ] sequences_of_sequences_with_transpose")
    test_event_cycle_rejected()
    print("[ok ] event_cycle_rejected")
    test_library_search_and_instrument()
    print("[ok ] library_search_and_instrument")
    print("\nSEQUENCE + LIBRARY: ALL OK")
