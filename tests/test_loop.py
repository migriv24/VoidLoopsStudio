"""
Loop tests: the app's namesake unit — a whole mantle used as a single node
(okf/concepts/loop.md). A Loop's ports are the FREE ports of its inner graph
(the interaction-net boundary); compile expands Loops into one flat net.

Covers: port derivation, type-checked boundary wiring, expansion (with notes riding
along), reuse (two Loop nodes, one mantle), nesting, cycle rejection, disk round-trip,
and that a Loop patch actually renders sound.

CONTRACT (agreed with Void Core, 2026-07-07): these tests + render._expand_loops are
the REFERENCE SEMANTICS for the core's future data-form `expand` / general-LHS design.
Flag behavioral changes through the message channel first.

Runnable via `pytest` or `python tests/test_loop.py`.
"""
from __future__ import annotations

from pathlib import Path

from voidloops import VoidLoopsProject, compile_render
from voidloops.backend import render_samples


def _melody(proj: VoidLoopsProject, name: str = "melody"):
    """A loopable mantle: sequencer1 → osc1 (clk inlet and audio outlet left free),
    holding a C-major arpeggio."""
    proj.new_pattern(name)
    ppqn = proj.meta.ppqn
    seq = proj.add_node("sequencer", length=4 * ppqn)
    osc = proj.add_node("osc", wave="sine", tuning=0)
    proj.wire(seq, osc)
    for i, note in enumerate(["C4", "E4", "G4", "C5"]):
        proj.add_note(note, start=i * ppqn, length=ppqn, velocity=90, node=seq)
    return seq, osc


def test_loop_ports_are_the_free_ports():
    with VoidLoopsProject() as proj:
        _melody(proj)
        proj.new_pattern("main")
        loop = proj.add_loop("melody")
        inlets, outlets = proj.loop_ports(loop)
        assert [(p.name, p.signal) for p in inlets] == [("sequencer1.clk", "clock")]
        assert [(p.name, p.signal) for p in outlets] == [("osc1.out", "audio")]


def test_loop_boundary_wiring_is_typed():
    with VoidLoopsProject() as proj:
        _melody(proj)
        proj.new_pattern("main")
        clk = proj.add_node("clock", rate=96)
        loop = proj.add_loop("melody")
        out = proj.add_node("output", gain=1)
        # sole-port defaulting works through the Loop boundary
        assert proj.wire(clk, loop) == "clock:clk->sequencer1.clk"
        assert proj.wire(loop, out) == "audio:osc1.out->in"
        # and mismatches are rejected: audio outlet into a clock inlet
        proj.new_pattern("bad")
        loop2 = proj.add_loop("melody")
        osc = proj.add_node("osc")
        try:
            proj.wire(loop2, osc, src_port="osc1.out")   # audio -> events inlet
            assert False, "expected TypeError"
        except TypeError:
            pass


def test_loop_expands_with_its_notes():
    with VoidLoopsProject() as proj:
        _melody(proj)
        proj.new_pattern("main")
        clk = proj.add_node("clock", rate=96)
        loop = proj.add_loop("melody")
        out = proj.add_node("output", gain=1)
        proj.wire(clk, loop)
        proj.wire(loop, out)
        snap = compile_render(proj)
        assert len(snap["voices"]) == 1
        v = snap["voices"][0]
        assert v["generator"] == f"{loop}/osc1"
        assert v["sequencer"]["name"] == f"{loop}/sequencer1"
        assert v["clock"]["name"] == "clock1"            # the OUTER clock drives it
        assert [n["pitch"] for n in v["notes"]] == [60, 64, 67, 72]
        assert v["route"] == [f"{loop}/osc1", "output1"]


def test_loop_reuse_two_nodes_one_mantle():
    with VoidLoopsProject() as proj:
        _melody(proj)
        proj.new_pattern("main")
        mix = proj.add_node("mix", gain=1)
        out = proj.add_node("output", gain=1)
        proj.wire(mix, out)
        for _ in range(2):
            clk = proj.add_node("clock", rate=96)
            loop = proj.add_loop("melody")
            proj.wire(clk, loop)
            proj.wire(loop, mix)
        snap = compile_render(proj)
        assert len(snap["voices"]) == 2
        gens = {v["generator"] for v in snap["voices"]}
        assert gens == {"loop1/osc1", "loop2/osc1"}
        for v in snap["voices"]:                          # same mantle, same notes
            assert [n["pitch"] for n in v["notes"]] == [60, 64, 67, 72]


def test_nested_loops_expand_recursively():
    with VoidLoopsProject() as proj:
        _melody(proj, "inner")
        proj.new_pattern("outer")                         # a Loop containing a Loop
        wrapped = proj.add_loop("inner")
        proj.new_pattern("main")
        clk = proj.add_node("clock", rate=96)
        loop = proj.add_loop("outer")
        out = proj.add_node("output", gain=1)
        inlets, outlets = proj.loop_ports(loop)           # doubly-qualified free ports
        assert inlets[0].name == f"{wrapped}.sequencer1.clk"
        assert outlets[0].name == f"{wrapped}.osc1.out"
        proj.wire(clk, loop)
        proj.wire(loop, out)
        snap = compile_render(proj)
        v = snap["voices"][0]
        assert v["generator"] == f"{loop}/{wrapped}/osc1"
        assert [n["pitch"] for n in v["notes"]] == [60, 64, 67, 72]


def test_loop_cycles_rejected():
    with VoidLoopsProject() as proj:
        proj.new_pattern("a")
        proj.add_node("osc")
        proj.new_pattern("b")
        proj.add_loop("a")
        proj.cmd("use a")
        try:                                              # direct self-drop
            proj.add_loop("a")
            assert False, "expected ValueError"
        except ValueError:
            pass
        loop_ab = proj.add_loop("b")                      # a -> b -> a: a cycle
        try:
            proj.loop_ports(loop_ab)
            assert False, "expected ValueError (cycle)"
        except ValueError as e:
            assert "cycle" in str(e).lower()


def test_loop_patch_roundtrips_and_sounds(tmp_path: Path):
    path = tmp_path / "looped.vlp.json"
    with VoidLoopsProject(path) as proj:
        _melody(proj)
        proj.new_pattern("main")
        clk = proj.add_node("clock", rate=96)
        loop = proj.add_loop("melody")
        out = proj.add_node("output", gain=1)
        proj.wire(clk, loop)
        proj.wire(loop, out)
        proj.save()
    with VoidLoopsProject(path) as reopened:
        reopened.cmd("use main")
        snap = compile_render(reopened)
        assert snap["voices"][0]["generator"] == "loop1/osc1"
        samples = render_samples(snap)                    # ...and it makes sound
        assert len(samples) > 0 and max(abs(s) for s in samples) > 0.1


if __name__ == "__main__":
    import tempfile

    flat = [
        ("loop_ports_are_the_free_ports", test_loop_ports_are_the_free_ports),
        ("loop_boundary_wiring_is_typed", test_loop_boundary_wiring_is_typed),
        ("loop_expands_with_its_notes", test_loop_expands_with_its_notes),
        ("loop_reuse_two_nodes_one_mantle", test_loop_reuse_two_nodes_one_mantle),
        ("nested_loops_expand_recursively", test_nested_loops_expand_recursively),
        ("loop_cycles_rejected", test_loop_cycles_rejected),
    ]
    for name, fn in flat:
        fn()
        print(f"[ok ] {name}")
    with tempfile.TemporaryDirectory() as d:
        test_loop_patch_roundtrips_and_sounds(Path(d))
    print("[ok ] loop_patch_roundtrips_and_sounds")
    print("\nLOOP: ALL OK")
