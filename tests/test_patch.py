"""
Step-2 tests: a patch as a graph — the full first-sound topology
(clock → sequencer → osc → output) where the sequencer *holds* its note-runes
(containment = the `node:<seq>` tag, so notes stay first-class and tag-selectable).

Proves the node graph round-trips and validates with real musical content.
See okf/concepts/loop.md and okf/roadmap.md step 2.

Runnable via `pytest` or `python tests/test_patch.py`.
"""
from __future__ import annotations

from pathlib import Path

from voidloops import VoidLoopsProject


def _first_sound(proj: VoidLoopsProject, patch: str = "first-sound"):
    """Build the canonical first-sound patch; returns (clk, seq, osc, out)."""
    proj.new_pattern(patch)
    ppqn = proj.meta.ppqn
    clk = proj.add_node("clock", rate=ppqn)
    seq = proj.add_node("sequencer", length=4 * ppqn)
    osc = proj.add_node("osc", wave="saw", tuning=0)
    out = proj.add_node("output", gain=1)
    proj.wire(clk, seq)
    proj.wire(seq, osc)
    proj.wire(osc, out)
    for i, note in enumerate(["C4", "E4", "G4", "C5"]):
        proj.add_note(note, start=i * ppqn, length=ppqn, velocity=90, node=seq)
    return clk, seq, osc, out


def test_sequencer_holds_notes():
    with VoidLoopsProject() as proj:
        _, seq, _, _ = _first_sound(proj)
        held = proj.notes(node=seq)
        assert [n["pitch"] for n in held] == [60, 64, 67, 72]
        assert [n["start"] for n in held] == [0, 96, 192, 288]


def test_two_sequencers_separate_their_notes():
    with VoidLoopsProject() as proj:
        proj.new_pattern("patch")
        lead = proj.add_node("sequencer")
        bass = proj.add_node("sequencer")
        proj.add_note("C4", 0, 96, node=lead)
        proj.add_note("E4", 96, 96, node=lead)
        proj.add_note("C2", 0, 384, node=bass)
        assert [n["pitch"] for n in proj.notes(node=lead)] == [60, 64]
        assert [n["pitch"] for n in proj.notes(node=bass)] == [36]
        assert len(proj.notes()) == 3          # unfiltered still sees the whole patch


def test_notes_only_live_in_sequencers():
    with VoidLoopsProject() as proj:
        proj.new_pattern("patch")
        osc = proj.add_node("osc")
        try:
            proj.add_note("C4", 0, 96, node=osc)
            assert False, "expected ValueError"
        except ValueError:
            pass


def test_full_patch_validates():
    with VoidLoopsProject() as proj:
        _first_sound(proj)
        v = proj.cmd("validate")
        assert v["ok"], v["lines"]


def test_add_note_is_one_undo_frame():
    with VoidLoopsProject() as proj:
        _, seq, _, _ = _first_sound(proj)
        before = len(proj.notes(node=seq))
        proj.add_note("D4", 0, 48, node=seq)
        assert len(proj.notes(node=seq)) == before + 1
        assert proj.cmd("undo")["ok"]
        assert len(proj.notes(node=seq)) == before   # rune + content + tag, one frame


def test_first_sound_patch_roundtrips(tmp_path: Path):
    path = tmp_path / "first-sound.vlp.json"
    with VoidLoopsProject(path) as proj:
        _, seq, _, _ = _first_sound(proj)
        proj.save()
    with VoidLoopsProject(path) as reopened:
        reopened.cmd("use first-sound")
        assert len(reopened.nodes()) == 4
        assert len(reopened.wires()) == 3
        held = reopened.notes(node="sequencer1")
        assert [n["pitch"] for n in held] == [60, 64, 67, 72]
        assert reopened.cmd("validate")["ok"], reopened.cmd("validate")["lines"]


if __name__ == "__main__":
    import tempfile

    flat = [
        ("sequencer_holds_notes", test_sequencer_holds_notes),
        ("two_sequencers_separate_their_notes", test_two_sequencers_separate_their_notes),
        ("notes_only_live_in_sequencers", test_notes_only_live_in_sequencers),
        ("full_patch_validates", test_full_patch_validates),
        ("add_note_is_one_undo_frame", test_add_note_is_one_undo_frame),
    ]
    for name, fn in flat:
        fn()
        print(f"[ok ] {name}")
    with tempfile.TemporaryDirectory() as d:
        test_first_sound_patch_roundtrips(Path(d))
    print("[ok ] first_sound_patch_roundtrips")
    print("\nSTEP 2 PATCH: ALL OK")
