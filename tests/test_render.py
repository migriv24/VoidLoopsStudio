"""
Step-3 tests: the graph compile — node graph → (data-authored Reduce) → render mantle →
(resolve) → the render snapshot the audio backend pulls. Pure, off-thread, no samples.

Also regression-tests the config seeding fix: the C core has no `config` verb, so meta
and the transform spec must be seeded into state BEFORE the manager is constructed —
previously `config set ...` failed silently and the defaults fallback masked it.

Runnable via `pytest` or `python tests/test_render.py`.
"""
from __future__ import annotations

import json
from pathlib import Path

from voidloops import VoidLoopsProject, compile_render
from voidloops.model import NODE_KIND

from test_patch import _first_sound


def test_config_actually_persists(tmp_path: Path):
    path = tmp_path / "p.vlp.json"
    with VoidLoopsProject(path) as proj:
        proj.save()
    doc = json.loads(path.read_text(encoding="utf-8"))
    cfg = doc["config"]
    assert cfg["ppqn"] == 96 and cfg["bpm"] == 120.0      # meta really in the file now
    spec = cfg["transform"]["reduce"]
    assert set(spec["signatures"]) == set(NODE_KIND)       # reduce spec authored as data
    assert spec["rules"] == []
    # a project with its own values keeps them (existing config wins over defaults)
    doc["config"]["bpm"] = 140.0
    path.write_text(json.dumps(doc), encoding="utf-8")
    with VoidLoopsProject(path) as reopened:
        assert reopened.meta.bpm == 140.0


def test_compile_first_sound_snapshot():
    with VoidLoopsProject() as proj:
        _first_sound(proj)
        snap = compile_render(proj)
        assert snap["meta"]["bpm"] == 120.0 and snap["meta"]["ppqn"] == 96
        assert len(snap["voices"]) == 1
        v = snap["voices"][0]
        assert v["generator"] == "osc1" and v["kind"] == "osc"
        assert v["content"]["wave"] == "saw"
        assert v["sequencer"]["name"] == "sequencer1" and v["sequencer"]["length"] == 384
        assert v["clock"]["rate"] == 96
        assert v["route"] == ["osc1", "output1"]
        assert [n["pitch"] for n in v["notes"]] == [60, 64, 67, 72]
        # seconds resolved at the boundary: quarter notes at 120 BPM
        assert [n["start_s"] for n in v["notes"]] == [0.0, 0.5, 1.0, 1.5]
        assert all(n["length_s"] == 0.5 for n in v["notes"])
        out = snap["outputs"][0]
        assert out["name"] == "output1" and out["gain"] == 1
        assert not out.get("duration")            # unset: auto window


def test_compile_is_pure():
    with VoidLoopsProject() as proj:
        _first_sound(proj)
        before = proj.export()
        compile_render(proj)
        after = proj.export()
        assert before == after                             # reads only; installs nothing
        assert "render" not in [m["name"] for m in after["mantles"]]


def test_compile_two_voices_through_mix():
    with VoidLoopsProject() as proj:
        proj.new_pattern("duo")
        ppqn = proj.meta.ppqn
        mix = proj.add_node("mix", gain=1)
        out = proj.add_node("output", gain=1)
        proj.wire(mix, out)
        for pitches in (["C4", "E4"], ["C2", "G2"]):
            clk = proj.add_node("clock", rate=ppqn)
            seq = proj.add_node("sequencer", length=2 * ppqn)
            osc = proj.add_node("osc", wave="sine", tuning=0)
            proj.wire(clk, seq)
            proj.wire(seq, osc)
            proj.wire(osc, mix)                            # multi inlet: two sources
            for i, p in enumerate(pitches):
                proj.add_note(p, start=i * ppqn, length=ppqn, node=seq)
        snap = compile_render(proj)
        assert len(snap["voices"]) == 2
        for v in snap["voices"]:
            assert v["route"] == [v["generator"], "mix1", "output1"]
            assert len(v["notes"]) == 2
        got = {tuple(n["pitch"] for n in v["notes"]) for v in snap["voices"]}
        assert got == {(60, 64), (36, 43)}


def test_compile_is_deterministic():
    with VoidLoopsProject() as proj:
        _first_sound(proj)
        assert compile_render(proj) == compile_render(proj)


def test_fanout_compiles():
    """One sequencer driving two generators (the author's sampler+VST scenario,
    2026-07-08): fan-out gets per-wire synthetic outlet indices and just works."""
    with VoidLoopsProject() as proj:
        proj.new_pattern("patch")
        seq = proj.add_node("sequencer", repeat=1)
        a = proj.add_node("osc", wave="sine")
        b = proj.add_node("osc", wave="square")
        mix = proj.add_node("mix", gain=1)
        out = proj.add_node("output", gain=1)
        proj.wire(seq, a)
        proj.wire(seq, b)                                  # fan-out from one outlet
        proj.wire(a, mix)
        proj.wire(b, mix)
        proj.wire(mix, out)
        proj.add_note("C4", 0, 96, node=seq)
        snap = compile_render(proj)
        assert len(snap["voices"]) == 2                    # both oscs got the notes
        assert all([n["pitch"] for n in v["notes"]] == [60]
                   for v in snap["voices"])


if __name__ == "__main__":
    import tempfile

    with tempfile.TemporaryDirectory() as d:
        test_config_actually_persists(Path(d))
    print("[ok ] config_actually_persists")
    flat = [
        ("compile_first_sound_snapshot", test_compile_first_sound_snapshot),
        ("compile_is_pure", test_compile_is_pure),
        ("compile_two_voices_through_mix", test_compile_two_voices_through_mix),
        ("compile_is_deterministic", test_compile_is_deterministic),
        ("fanout_compiles", test_fanout_compiles),
    ]
    for name, fn in flat:
        fn()
        print(f"[ok ] {name}")
    print("\nSTEP 3 RENDER: ALL OK")
