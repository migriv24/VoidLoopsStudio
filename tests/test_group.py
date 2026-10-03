"""
group_loop (the editor's Ctrl+G, 2026-07-08): select nodes -> ONE Loop node.
The grouped patch must render identically, boundary wires re-anchored onto the
Loop's free ports, notes riding along.

Runnable via `pytest` or `python tests/test_group.py`.
"""
from __future__ import annotations

from voidloops import VoidLoopsProject
from voidloops.render import compile_render


def _pitches(snap):
    return sorted(n["pitch"] for v in snap["voices"] for n in v["notes"])


def test_group_preserves_the_music():
    with VoidLoopsProject() as proj:
        proj.new_pattern("song")
        clk = proj.add_node("clock")
        seq = proj.add_node("sequencer")
        osc = proj.add_node("osc", wave="square")
        out = proj.add_node("output", duration=288)  # exactly one cycle
        proj.wire(clk, seq)
        proj.wire(seq, osc)
        proj.wire(osc, out)
        for i, p in enumerate(["C4", "E4", "G4"]):
            proj.add_note(p, i * 96, 96, node=seq)
        proj.tag_node(osc, "lead")
        before = _pitches(compile_render(proj))

        loop = proj.group_loop([seq, osc], "melody")
        # the originals are gone; one Loop stands in their place
        kinds = {n["name"]: n["kind"] for n in proj.nodes()}
        assert seq not in kinds and osc not in kinds
        assert kinds[loop] == "loop"
        # boundary wires re-anchored onto qualified free ports
        inlets, outlets = proj.loop_ports(loop)
        assert [p.name for p in inlets] == [f"{seq}.clk"]
        assert [p.name for p in outlets] == [f"{osc}.out"]
        wires = {(w["from"], w["to"]) for w in proj.wires()}
        assert (clk, loop) in wires and (loop, out) in wires
        # ...and the music is unchanged (notes moved, content+tags survived)
        after = compile_render(proj)
        assert _pitches(after) == before == [60, 64, 67]
        gen = after["voices"][0]
        assert gen["content"].get("wave") == "square"
        assert f"{loop}/{osc}" == gen["generator"]


def test_group_drops_param_boundary_wires_but_succeeds():
    with VoidLoopsProject() as proj:
        proj.new_pattern("song")
        clk = proj.add_node("clock")
        seq = proj.add_node("sequence")
        osc = proj.add_node("osc")
        out = proj.add_node("output", duration=384)
        proj.wire(clk, seq, dst_port="clk")
        proj.wire(seq, osc)
        proj.wire(osc, out)
        proj.add_note("C4", 0, 96, node=seq)
        val = proj.add_node("value", value=7)
        proj.wire(val, seq, dst_port="p:transpose")   # a param wire at the boundary
        loop = proj.group_loop([seq, osc], "inner")
        snap = compile_render(proj)                    # compiles; param wire dropped
        assert set(_pitches(snap)) == {60}             # transpose no longer bound


if __name__ == "__main__":
    for name, fn in [
        ("group_preserves_the_music", test_group_preserves_the_music),
        ("group_drops_param_boundary_wires", test_group_drops_param_boundary_wires_but_succeeds),
    ]:
        fn()
        print(f"[ok ] {name}")
    print("\nGROUP -> LOOP: ALL OK")
