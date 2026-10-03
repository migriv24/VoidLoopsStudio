"""
Step-1 (post-pivot) tests: the node graph — node glyphs with typed ports, creating
nodes, and type-checked wiring. Proves the graph data shapes via `validate`.

The v1 first-sound topology is `clock → sequencer → osc → output`; `mix` sums sources.
See okf/concepts/node-graph.md and okf/concepts/node-types.md.

Runnable via `pytest` or `python tests/test_nodes.py`.
"""
from __future__ import annotations

from pathlib import Path

from voidloops import VoidLoopsProject
from voidloops.model import NODE_KIND


def test_node_glyphs_registered():
    with VoidLoopsProject() as proj:
        glyphs = proj.cmd("glyphs")["data"]
        names = glyphs if isinstance(glyphs, list) and glyphs and isinstance(glyphs[0], str) \
            else [g.get("glyph") for g in glyphs]
        for g in ("clock", "sequencer", "osc", "mix", "output"):
            assert g in names, (g, names)


def test_create_nodes_with_typed_content():
    with VoidLoopsProject() as proj:
        proj.new_pattern("patch")
        clk = proj.add_node("clock", rate=96)
        seq = proj.add_node("sequencer", length=384)
        osc = proj.add_node("osc", wave="saw", tuning=0)
        out = proj.add_node("output", gain=1)
        assert [clk, seq, osc, out] == ["clock1", "sequencer1", "osc1", "output1"]
        nodes = {n["name"]: n for n in proj.nodes()}
        assert set(nodes) == {"clock1", "sequencer1", "osc1", "output1"}
        assert nodes["clock1"]["kind"] == "clock"
        # numbers land as real ints (setjson), strings as strings (set)
        assert nodes["clock1"]["content"]["rate"] == 96
        assert nodes["sequencer1"]["content"]["length"] == 384
        assert nodes["osc1"]["content"] == {"wave": "saw", "tuning": 0}


def test_add_node_rejects_bad_kind_and_field():
    with VoidLoopsProject() as proj:
        proj.new_pattern("patch")
        try:
            proj.add_node("reverb")            # not a v1 node kind
            assert False, "expected ValueError"
        except ValueError:
            pass
        try:
            proj.add_node("osc", frequency=440)  # osc has 'tuning', not 'frequency'
            assert False, "expected ValueError"
        except ValueError:
            pass


def test_wire_typed_chain_validates():
    with VoidLoopsProject() as proj:
        proj.new_pattern("first-sound")
        clk = proj.add_node("clock")
        seq = proj.add_node("sequencer")
        osc = proj.add_node("osc")
        out = proj.add_node("output")
        # ports default to the sole inlet/outlet — one wire per hop
        assert proj.wire(clk, seq) == "clock:clk->clk"
        assert proj.wire(seq, osc) == "events:notes->notes"
        assert proj.wire(osc, out) == "audio:out->in"
        wires = proj.wires()
        assert [(w["from"], w["to"], w["signal"]) for w in wires] == [
            (clk, seq, "clock"), (seq, osc, "events"), (osc, out, "audio")]
        # a fully-connected patch has no dangling wires
        assert proj.cmd("validate")["ok"], proj.cmd("validate")["lines"]


def test_wire_rejects_type_mismatch():
    with VoidLoopsProject() as proj:
        proj.new_pattern("patch")
        clk = proj.add_node("clock")
        osc = proj.add_node("osc")
        # clock outlet (clock) into osc's only inlet (events) — incompatible
        try:
            proj.wire(clk, osc)
            assert False, "expected TypeError"
        except TypeError:
            pass
        # nothing was wired
        assert proj.wires() == []


def test_single_inlet_rejects_second_wire():
    with VoidLoopsProject() as proj:
        proj.new_pattern("patch")
        a = proj.add_node("osc")
        b = proj.add_node("osc")
        out = proj.add_node("output")
        proj.wire(a, out)                       # output.in is a single inlet
        try:
            proj.wire(b, out)
            assert False, "expected ValueError"
        except ValueError:
            pass


def test_mix_multi_inlet_sums_many():
    with VoidLoopsProject() as proj:
        proj.new_pattern("patch")
        a = proj.add_node("osc")
        b = proj.add_node("osc")
        mix = proj.add_node("mix")
        out = proj.add_node("output")
        proj.wire(a, mix)                       # mix.in is multi — many sources ok
        proj.wire(b, mix)
        proj.wire(mix, out)
        ins = [w for w in proj.wires() if w["to"] == mix]
        assert {w["from"] for w in ins} == {a, b}
        assert proj.cmd("validate")["ok"], proj.cmd("validate")["lines"]


def test_patch_roundtrips_through_disk(tmp_path: Path):
    path = tmp_path / "patch.vlp.json"
    with VoidLoopsProject(path) as proj:
        proj.new_pattern("first-sound")
        clk = proj.add_node("clock", rate=96)
        seq = proj.add_node("sequencer", length=384)
        osc = proj.add_node("osc", wave="saw")
        out = proj.add_node("output")
        proj.wire(clk, seq)
        proj.wire(seq, osc)
        proj.wire(osc, out)
        proj.save()
    with VoidLoopsProject(path) as reopened:
        reopened.cmd("use first-sound")
        assert {n["name"] for n in reopened.nodes()} == \
            {"clock1", "sequencer1", "osc1", "output1"}
        assert len(reopened.wires()) == 3          # wires survived the round-trip
        assert reopened.cmd("validate")["ok"], reopened.cmd("validate")["lines"]


if __name__ == "__main__":
    import tempfile

    flat = [
        ("node_glyphs_registered", test_node_glyphs_registered),
        ("create_nodes_with_typed_content", test_create_nodes_with_typed_content),
        ("add_node_rejects_bad_kind_and_field", test_add_node_rejects_bad_kind_and_field),
        ("wire_typed_chain_validates", test_wire_typed_chain_validates),
        ("wire_rejects_type_mismatch", test_wire_rejects_type_mismatch),
        ("single_inlet_rejects_second_wire", test_single_inlet_rejects_second_wire),
        ("mix_multi_inlet_sums_many", test_mix_multi_inlet_sums_many),
    ]
    for name, fn in flat:
        fn()
        print(f"[ok ] {name}")
    with tempfile.TemporaryDirectory() as d:
        test_patch_roundtrips_through_disk(Path(d))
    print("[ok ] patch_roundtrips_through_disk")
    print("\nSTEP 1 NODES: ALL OK")
