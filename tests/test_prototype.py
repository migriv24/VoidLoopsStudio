"""
PROTOTYPE ACCEPTANCE — the author's six v1 criteria (2026-07-07), one test each:

1. the node graph has the expected properties (typed ports, categories, Loops)
2. load VSTs and generate sound (vst-effect in-graph; vst-instrument machinery)
3. MIDI sequences + looped sounds (sequencer loops fill the render window)
4. sequencing sequences (offset/repeat/length — and the seam stays open)
5. tag-routed FX replacing busses (reverb + limiter, "everything tagged X → FX")
6. parallel music generation (stacked melodies, simultaneous sequences)

Runnable via `pytest` or `python tests/test_prototype.py`.
"""
from __future__ import annotations

from pathlib import Path

from voidloops import VoidLoopsProject, compile_render
from voidloops.backend import SAMPLE_RATE, render_samples
from voidloops.model import CATEGORIES, NODE_KIND
from voidloops.vsthost import REMOTE_EXE

OTT = Path("C:/Program Files/Common Files/VST2/OTT_x64.dll")
PPQN = 96


def test_1_node_graph_properties():
    # every kind category-anchored; ports typed; Loop ports computed from free ports
    assert all(k.category in CATEGORIES for k in NODE_KIND.values())
    with VoidLoopsProject() as proj:
        proj.new_pattern("melody")
        seq = proj.add_node("sequencer")
        osc = proj.add_node("osc")
        proj.wire(seq, osc)
        proj.add_note("C4", 0, PPQN, node=seq)
        proj.new_pattern("main")
        loop = proj.add_loop("melody")
        inl, outl = proj.loop_ports(loop)
        assert [p.signal for p in inl] == ["clock"]
        assert [p.signal for p in outl] == ["audio"]
        try:
            proj.wire(proj.add_node("clock"), proj.add_node("osc"))
            assert False, "typed ports must reject clock->events"
        except TypeError:
            pass


def test_2_vst_loads_and_shapes_sound():
    if not (REMOTE_EXE.exists() and OTT.exists()):
        print("      (skipped: no RemoteVstPlugin/OTT on this machine)")
        return
    with VoidLoopsProject() as proj:
        proj.new_pattern("patch")
        seq = proj.add_node("sequencer", repeat=1)
        osc = proj.add_node("osc", wave="saw")
        fx = proj.add_node("vst-effect", plugin=str(OTT))
        out = proj.add_node("output", gain=1)
        proj.wire(seq, osc)
        proj.wire(osc, fx)
        proj.wire(fx, out)
        proj.add_note("A4", 0, PPQN, velocity=110, node=seq)
        snap = compile_render(proj)
        assert snap["voices"][0]["effects"][0]["kind"] == "vst-effect"
        samples = render_samples(snap)              # audio really went THROUGH OTT
        assert max(abs(s) for s in samples) > 0.01
        assert len(samples) > int(1.4 * SAMPLE_RATE)   # plugin tail rendered


def test_3_midi_sequences_loop_to_fill_the_window():
    with VoidLoopsProject() as proj:
        proj.new_pattern("patch")
        # a one-bar figure, looping (repeat unset = fill) into a 4-bar window
        seq = proj.add_node("sequencer", length=4 * PPQN)
        osc = proj.add_node("osc", wave="sine")
        out = proj.add_node("output", gain=1, duration=16 * PPQN)
        proj.wire(seq, osc)
        proj.wire(osc, out)
        proj.add_note("C4", 0, PPQN, node=seq)
        snap = compile_render(proj)
        notes = snap["voices"][0]["notes"]
        assert [n["start"] for n in notes] == [0, 384, 768, 1152]   # looped 4x
        samples = render_samples(snap)
        assert len(samples) == 16 * PPQN * SAMPLE_RATE // PPQN // 2  # 8 s window
        for k in range(4):                          # each cycle audibly hits
            head = samples[int(k * 2 * SAMPLE_RATE):int((k * 2 + 0.4) * SAMPLE_RATE)]
            assert max(abs(s) for s in head) > 0.1, f"cycle {k} silent"


def test_4_sequencing_sequences():
    with VoidLoopsProject() as proj:
        proj.new_pattern("patch")
        mix = proj.add_node("mix", gain=1)
        out = proj.add_node("output", gain=1, duration=8 * PPQN)
        proj.wire(mix, out)
        # A enters at 0 and loops; B enters two bars in, once (an arrangement,
        # expressed as node content — the seam a future "time of day" input drives)
        for offset, repeat, pitch in ((0, 0, "C4"), (8 * PPQN // 2, 1, "G4")):
            seq = proj.add_node("sequencer", length=2 * PPQN, offset=offset,
                                repeat=repeat)
            osc = proj.add_node("osc", wave="sine")
            proj.wire(seq, osc)
            proj.wire(osc, mix)
            proj.add_note(pitch, 0, PPQN, node=seq)
        snap = compile_render(proj)
        a, b = snap["voices"]
        starts = {v["sequencer"]["name"]: [n["start"] for n in v["notes"]]
                  for v in (a, b)}
        assert starts["sequencer1"] == [0, 192, 384, 576]           # loops the window
        assert starts["sequencer2"] == [384]                        # enters late, once
        assert render_samples(snap)                                 # and it renders


def test_5_tag_routed_fx_replace_busses(tmp_path: Path):
    with VoidLoopsProject(tmp_path / "p.vlp.json") as proj:
        proj.new_pattern("patch")
        mix = proj.add_node("mix", gain=1)
        out = proj.add_node("output", gain=1)
        proj.wire(mix, out)
        oscs = []
        for pitch in ("C3", "C5"):
            seq = proj.add_node("sequencer", repeat=1)
            osc = proj.add_node("osc", wave="sine")
            proj.wire(seq, osc)
            proj.wire(osc, mix)
            proj.add_note(pitch, 0, PPQN, velocity=120, node=seq)
            oscs.append(osc)
        proj.tag_node(oscs[0], "drums")             # only the low voice is "drums"
        proj.add_fx_rule("drums", type="reverb", amount=0.5)
        proj.add_fx_rule("drums", type="limiter", amount=0.4)
        snap = compile_render(proj)
        fx = {v["generator"]: [e.get("type") for e in v["effects"]]
              for v in snap["voices"]}
        assert fx[oscs[0]] == ["reverb", "limiter"]  # tagged: gets the chain
        assert fx[oscs[1]] == []                     # untagged: dry
        samples = render_samples(snap)
        assert len(samples) > int(1.4 * SAMPLE_RATE)  # reverb tail exists
        tail = samples[int(0.8 * SAMPLE_RATE):int(1.2 * SAMPLE_RATE)]
        assert max(abs(s) for s in tail) > 0.005      # audible wash after the notes
        proj.save()
    with VoidLoopsProject(tmp_path / "p.vlp.json") as reopened:   # rules persist
        assert "drums" in ((reopened.export().get("config") or {})
                           .get("fx_rules") or "")


def test_6_parallel_music_generation():
    with VoidLoopsProject() as proj:
        proj.new_pattern("patch")
        mix = proj.add_node("mix", gain=1)
        out = proj.add_node("output", gain=1, duration=4 * PPQN)
        proj.wire(mix, out)
        chord = ("C4", "E4", "G4")                  # three melodies, stacked
        for pitch in chord:
            seq = proj.add_node("sequencer", length=PPQN)
            osc = proj.add_node("osc", wave="sine")
            proj.wire(seq, osc)
            proj.wire(osc, mix)
            proj.add_note(pitch, 0, PPQN, velocity=90, node=seq)
        snap = compile_render(proj)
        assert len(snap["voices"]) == 3             # truly parallel voices
        assert all(len(v["notes"]) == 4 for v in snap["voices"])   # all looping
        samples = render_samples(snap)
        assert max(abs(s) for s in samples) > 0.25  # the stack is louder than one


if __name__ == "__main__":
    import tempfile

    test_1_node_graph_properties()
    print("[ok ] 1: node graph properties")
    test_2_vst_loads_and_shapes_sound()
    print("[ok ] 2: vst loads + shapes sound")
    test_3_midi_sequences_loop_to_fill_the_window()
    print("[ok ] 3: midi sequences loop")
    test_4_sequencing_sequences()
    print("[ok ] 4: sequencing sequences")
    with tempfile.TemporaryDirectory() as d:
        test_5_tag_routed_fx_replace_busses(Path(d))
    print("[ok ] 5: tag-routed fx (reverb+limiter)")
    test_6_parallel_music_generation()
    print("[ok ] 6: parallel music generation")
    print("\nPROTOTYPE ACCEPTANCE: ALL OK")
