"""
Step-1 tests: the DAW data model — glyphs, a pattern-mantle of note-runes, integer-tick
content, `validate`, tag selection, and round-trip.

Runnable via `pytest` or `python tests/test_model.py`.
"""
from __future__ import annotations

from pathlib import Path

from voidloops import VoidLoopsProject, pitch, pitch_name
from voidloops.model import DEFAULT_PPQN, ticks_to_seconds


def test_daw_glyphs_registered():
    with VoidLoopsProject() as proj:
        glyphs = proj.cmd("glyphs")["data"]
        names = glyphs if isinstance(glyphs, list) and glyphs and isinstance(glyphs[0], str) \
            else [g.get("glyph") for g in glyphs]
        for g in ("note", "automation", "sample"):
            assert g in names, (g, names)
        # the timeline-era pattern-clip glyph was retired by the node pivot
        assert "pattern-clip" not in names, names


def test_pitch_helpers():
    assert pitch("C4") == 60
    assert pitch("A4") == 69          # concert A = 440 Hz = MIDI 69
    assert pitch("C#4") == 61
    assert pitch("Eb4") == 63
    assert pitch(60) == 60
    assert pitch_name(60) == "C4"


def test_add_note_writes_integer_content():
    with VoidLoopsProject() as proj:
        proj.new_pattern("p1")
        proj.add_note("C4", start=0, length=DEFAULT_PPQN, velocity=100)
        c = proj.cmd("get n1")["data"]
        # crucially: real ints, not the glyph's empty-string defaults
        assert c == {"pitch": 60, "start": 0, "length": 96, "velocity": 100}
        assert all(isinstance(c[k], int) for k in c)


def test_build_a_pattern_and_validate():
    with VoidLoopsProject() as proj:
        proj.new_pattern("c-major")
        ppqn = proj.meta.ppqn
        for i, note in enumerate(["C4", "E4", "G4", "C5"]):
            proj.add_note(note, start=i * ppqn, length=ppqn, velocity=90)
        notes = proj.notes()
        assert [n["pitch"] for n in notes] == [60, 64, 67, 72]
        assert [n["start"] for n in notes] == [0, 96, 192, 288]
        # the model is well-formed: no dup names, registered glyphs, no dangling edges
        assert proj.cmd("validate")["ok"], proj.cmd("validate")["lines"]


def test_notes_query_by_glyph_and_track_tag():
    with VoidLoopsProject() as proj:
        proj.new_pattern("p1")
        proj.add_note("C4", 0, 96, track="lead")
        proj.add_note("E4", 96, 96, track="lead")
        proj.add_note("C2", 0, 384, track="bass")
        assert len(proj.notes()) == 3
        # tag selection (the substrate step 2's mixer rules build on)
        assert set(proj.cmd('ls --tag track:lead')["data"]) == {"n1", "n2"}
        assert proj.cmd('ls --tag track:bass')["data"] == ["n3"]


def test_meta_defaults_and_timing():
    with VoidLoopsProject() as proj:
        m = proj.meta
        assert m.ppqn == 96 and m.bpm == 120.0
        # one quarter note at 120 BPM = 0.5 s
        assert ticks_to_seconds(m.ppqn, m.ppqn, m.bpm) == 0.5


def test_set_meta_live_without_touching_undo():
    """The BPM knob (core >= 0.2.2): `set_meta` writes session meta with NO undo
    frame — undo still targets the last *musical* edit, and the meta change survives."""
    with VoidLoopsProject() as proj:
        proj.new_pattern("p1")
        proj.add_note("C4", 0, 96, velocity=90)
        assert proj.set_meta(bpm=140, ppqn=192).bpm == 140.0
        assert proj.meta.ppqn == 192
        assert proj.cmd("undo")["ok"]                  # undoes the NOTE, not the meta
        assert proj.notes() == []
        assert proj.meta.bpm == 140.0 and proj.meta.ppqn == 192
        try:
            proj.set_meta(swing=50)                    # not a meta field
            assert False, "expected ValueError"
        except ValueError:
            pass


def test_pattern_roundtrips_through_disk(tmp_path: Path):
    path = tmp_path / "song.vlp.json"
    with VoidLoopsProject(path) as proj:
        proj.new_pattern("p1")
        proj.add_note("C4", 0, 96, velocity=77)
        proj.save()
    with VoidLoopsProject(path) as reopened:
        reopened.cmd("use p1")
        notes = reopened.notes()
        assert notes == [{"name": "n1", "pitch": 60, "start": 0, "length": 96,
                          "velocity": 77}]
        assert reopened.meta.ppqn == 96   # meta survived too


if __name__ == "__main__":
    import tempfile

    flat = [
        ("daw_glyphs_registered", test_daw_glyphs_registered),
        ("pitch_helpers", test_pitch_helpers),
        ("add_note_writes_integer_content", test_add_note_writes_integer_content),
        ("build_a_pattern_and_validate", test_build_a_pattern_and_validate),
        ("notes_query_by_glyph_and_track_tag", test_notes_query_by_glyph_and_track_tag),
        ("meta_defaults_and_timing", test_meta_defaults_and_timing),
        ("set_meta_live_without_touching_undo", test_set_meta_live_without_touching_undo),
    ]
    for name, fn in flat:
        fn()
        print(f"[ok ] {name}")
    with tempfile.TemporaryDirectory() as d:
        test_pattern_roundtrips_through_disk(Path(d))
    print("[ok ] pattern_roundtrips_through_disk")
    print("\nSTEP 1 MODEL: ALL OK")
