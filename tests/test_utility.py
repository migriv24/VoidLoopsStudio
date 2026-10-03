"""
The utility category + params-as-ports (question #14, first wave, 2026-07-08):
`control` wires carry plain numbers; utility nodes (value/math/map/compare) and
the `time-of-day` input are pure value plumbing, evaluated once per render; a
wire into a `p:<field>` inlet overrides that field's content at compile time.

Runnable via `pytest` or `python tests/test_utility.py`.
"""
from __future__ import annotations

from voidloops import VoidLoopsProject
from voidloops.render import compile_render


def _patch(proj):
    """clock → sequence → osc → output with one note; returns names."""
    proj.new_pattern("ctl")
    clk = proj.add_node("clock")
    seq = proj.add_node("sequence")
    osc = proj.add_node("osc")
    out = proj.add_node("output", duration=384)
    proj.wire(clk, seq, dst_port="clk")
    proj.wire(seq, osc)
    proj.wire(osc, out)
    proj.add_note("C4", 0, 96, node=seq)
    return seq, osc, out


def test_value_binds_a_param():
    with VoidLoopsProject() as proj:
        seq, osc, out = _patch(proj)
        val = proj.add_node("value", value=7)
        proj.wire(val, seq, dst_port="p:transpose")
        snap = compile_render(proj)
        v = snap["voices"][0]
        assert v["sequencer"]["transpose"] == 7.0     # the override landed
        assert v["notes"][0]["pitch"] == 67           # C4 + 7 semitones, audibly


def test_math_chain_and_inline_fallbacks():
    with VoidLoopsProject() as proj:
        seq, osc, out = _patch(proj)
        a = proj.add_node("value", value=3)
        m = proj.add_node("math", op="add", b=4)      # unwired b falls back to content
        proj.wire(a, m, dst_port="a")
        proj.wire(m, seq, dst_port="p:transpose")
        snap = compile_render(proj)
        assert snap["voices"][0]["notes"][0]["pitch"] == 67   # 60 + (3+4)


def test_map_and_compare():
    with VoidLoopsProject() as proj:
        seq, osc, out = _patch(proj)
        # time-of-day (pinned at 18:00) → map 0-24h onto 0-12 semitones
        tod = proj.add_node("time-of-day", override=18)
        mp = proj.add_node("map", in_min=0, in_max=24, out_min=0, out_max=12)
        proj.wire(tod, mp, dst_port="in")
        proj.wire(mp, seq, dst_port="p:transpose")
        snap = compile_render(proj)
        assert snap["voices"][0]["notes"][0]["pitch"] == 69   # 60 + 18/24*12
        # compare: is it evening? (hour > 17 → 1)
        proj.cmd(f"unlink {mp} {seq}")
        cmp_ = proj.add_node("compare", op="gt", b=17)
        proj.wire(tod, cmp_, dst_port="a")
        proj.wire(cmp_, seq, dst_port="p:transpose")
        snap = compile_render(proj)
        assert snap["voices"][0]["notes"][0]["pitch"] == 61   # 60 + 1


def test_time_of_day_live_is_bounded():
    with VoidLoopsProject() as proj:
        proj.new_pattern("live")
        tod = proj.add_node("time-of-day")            # no override = the wall clock
        seq, osc, out = None, None, None
        from voidloops.render import _eval_control
        nodes = {n["name"]: n for n in proj.nodes()}
        h = _eval_control(tod, nodes, {})
        assert 0.0 <= h < 24.0


def test_type_check_guards_control_wires():
    with VoidLoopsProject() as proj:
        seq, osc, out = _patch(proj)
        try:                                          # audio outlet → control inlet
            proj.wire(osc, seq, dst_port="p:transpose")
            assert False, "audio must not wire into a param inlet"
        except TypeError:
            pass
        val = proj.add_node("value", value=1)
        try:                                          # control outlet → audio inlet
            proj.wire(val, out, dst_port="in")
            assert False, "control must not wire into an audio inlet"
        except TypeError:
            pass


def test_control_cycle_is_refused():
    with VoidLoopsProject() as proj:
        seq, osc, out = _patch(proj)
        m1 = proj.add_node("math")
        m2 = proj.add_node("math")
        proj.wire(m1, m2, dst_port="a")
        proj.wire(m2, m1, dst_port="a")
        proj.wire(m1, seq, dst_port="p:transpose")
        try:
            compile_render(proj)
            assert False, "control cycle must be refused"
        except ValueError as e:
            assert "cycle" in str(e)


def test_param_binding_survives_gain():
    """A value into output's p:gain scales the whole render (params reach any
    curated field, not just transpose)."""
    with VoidLoopsProject() as proj:
        seq, osc, out = _patch(proj)
        half = proj.add_node("value", value=0.5)
        proj.wire(half, out, dst_port="p:gain")
        snap = compile_render(proj)
        assert snap["outputs"][0]["gain"] == 0.5


if __name__ == "__main__":
    for name, fn in [
        ("value_binds_a_param", test_value_binds_a_param),
        ("math_chain_and_inline_fallbacks", test_math_chain_and_inline_fallbacks),
        ("map_and_compare", test_map_and_compare),
        ("time_of_day_live_is_bounded", test_time_of_day_live_is_bounded),
        ("type_check_guards_control_wires", test_type_check_guards_control_wires),
        ("control_cycle_is_refused", test_control_cycle_is_refused),
        ("param_binding_survives_gain", test_param_binding_survives_gain),
    ]:
        fn()
        print(f"[ok ] {name}")
    print("\nUTILITY / PARAMS-AS-PORTS: ALL OK")
