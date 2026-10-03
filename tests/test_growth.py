"""
Step-6 (model side) tests: the growth node wave, category-anchored — sampler,
sample-in, effect (gain/delay), and the honest VST refusal — all audible through the
trivial backend. The taxonomy pays rent here: the compiler pulls voices by CATEGORY,
so these kinds needed no compiler special-casing beyond the sampler's sample inlet.

Runnable via `pytest` or `python tests/test_growth.py`.
"""
from __future__ import annotations

import math
import struct
import wave as wave_mod
from pathlib import Path

from voidloops import VoidLoopsProject, compile_render
from voidloops.backend import SAMPLE_RATE, render_samples
from voidloops.model import NODE_KIND


def _fixture_wav(path: Path, seconds: float = 0.25, freq: float = 440.0) -> Path:
    """A tiny 16-bit mono sine WAV to sample."""
    n = int(seconds * SAMPLE_RATE)
    frames = b"".join(
        struct.pack("<h", int(0.8 * 32767 * math.sin(2 * math.pi * freq * i / SAMPLE_RATE)))
        for i in range(n))
    with wave_mod.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SAMPLE_RATE)
        w.writeframes(frames)
    return path


def test_categories_are_on_every_kind():
    cats = {k.glyph: k.category for k in NODE_KIND.values()}
    assert cats["sampler"] == "generator" and cats["sample-in"] == "input"
    assert cats["effect"] == "transform" and cats["mix"] == "combine"
    assert cats["sequencer"] == "time-event" and cats["loop"] == "loop"
    assert NODE_KIND["vst-instrument"].holiday and not NODE_KIND["osc"].holiday


def test_sampler_plays_the_sample_per_note(tmp_path: Path):
    wav = _fixture_wav(tmp_path / "hit.wav")
    with VoidLoopsProject() as proj:
        proj.new_pattern("patch")
        seq = proj.add_node("sequencer")
        smp = proj.add_node("sampler", root=60)
        src = proj.add_node("sample-in", path=str(wav), gain=1)
        out = proj.add_node("output", gain=1)
        proj.wire(seq, smp, dst_port="notes")
        proj.wire(src, smp, dst_port="sample")
        proj.wire(smp, out)
        proj.add_note("C4", 0, 96, node=seq)          # at root: plays as-is
        proj.add_note("C5", 96, 96, node=seq)         # +12: double-rate repitch
        snap = compile_render(proj)
        v = snap["voices"][0]
        assert v["kind"] == "sampler"
        assert v["sample"]["path"] == str(wav)
        samples = render_samples(snap)
        assert max(abs(s) for s in samples[:int(0.2 * SAMPLE_RATE)]) > 0.3   # note 1 sounds
        second = samples[int(0.55 * SAMPLE_RATE):int(0.6 * SAMPLE_RATE)]
        assert max(abs(s) for s in second) > 0.3                            # note 2 sounds
        # C5 repitches at 2x -> the 0.25 s sample lasts ~0.125 s: silent well before 0.7 s
        tail = samples[int(0.7 * SAMPLE_RATE):int(0.95 * SAMPLE_RATE)]
        assert max((abs(s) for s in tail), default=0.0) < 0.01


def test_bare_sample_in_is_a_voice(tmp_path: Path):
    wav = _fixture_wav(tmp_path / "bed.wav", seconds=0.5)
    with VoidLoopsProject() as proj:
        proj.new_pattern("patch")
        src = proj.add_node("sample-in", path=str(wav), gain=1)
        out = proj.add_node("output", gain=1)
        proj.wire(src, out)
        snap = compile_render(proj)
        assert snap["voices"][0]["kind"] == "sample-in"
        samples = render_samples(snap)
        assert len(samples) == int(0.5 * SAMPLE_RATE)     # duration = the file
        assert max(abs(s) for s in samples) > 0.3


def test_gain_effect_scales_the_voice():
    with VoidLoopsProject() as proj:
        proj.new_pattern("patch")
        seq = proj.add_node("sequencer")
        osc = proj.add_node("osc", wave="sine")
        fx = proj.add_node("effect", type="gain", amount=0.25)
        out = proj.add_node("output", gain=1)
        proj.wire(seq, osc)
        proj.wire(osc, fx)
        proj.wire(fx, out)
        proj.add_note("A4", 0, 96, velocity=127, node=seq)
        snap = compile_render(proj)
        v = snap["voices"][0]
        assert [e["type"] for e in v["effects"]] == ["gain"]
        assert v["route"] == ["osc1", "effect1", "output1"]
        quiet = max(abs(s) for s in render_samples(snap))
        loud = 0.5 * 127 / 127                            # the osc's dry peak amp
        assert abs(quiet - loud * 0.25) < 0.05


def test_delay_effect_echoes_past_the_note():
    with VoidLoopsProject() as proj:
        proj.new_pattern("patch")
        seq = proj.add_node("sequencer")
        osc = proj.add_node("osc", wave="sine")
        fx = proj.add_node("effect", type="delay", amount=0.3, feedback=0.5)
        out = proj.add_node("output", gain=1)
        proj.wire(seq, osc)
        proj.wire(osc, fx)
        proj.wire(fx, out)
        proj.add_note("A4", 0, 96, node=seq)              # 0.5 s note
        samples = render_samples(compile_render(proj))
        assert len(samples) > int(1.4 * SAMPLE_RATE)      # delay tail extends render
        echo = samples[int(0.85 * SAMPLE_RATE):int(1.05 * SAMPLE_RATE)]
        assert max(abs(s) for s in echo) > 0.05           # audible echo after note end


def test_vst_nodes_fail_honestly_when_plugin_missing():
    with VoidLoopsProject() as proj:
        proj.new_pattern("patch")
        seq = proj.add_node("sequencer")
        vst = proj.add_node("vst-instrument", plugin="no-such-plugin.dll")
        out = proj.add_node("output", gain=1)
        proj.wire(seq, vst)
        proj.wire(vst, out)
        proj.add_note("C4", 0, 96, node=seq)
        snap = compile_render(proj)                        # compiles fine (a voice)
        assert snap["voices"][0]["kind"] == "vst-instrument"
        try:
            render_samples(snap)                           # renders: honest not-found
            assert False, "expected ValueError"
        except ValueError as e:
            assert "not found" in str(e)


if __name__ == "__main__":
    import tempfile

    with tempfile.TemporaryDirectory() as d:
        tp = Path(d)
        test_categories_are_on_every_kind()
        print("[ok ] categories_are_on_every_kind")
        test_sampler_plays_the_sample_per_note(tp)
        print("[ok ] sampler_plays_the_sample_per_note")
        test_bare_sample_in_is_a_voice(tp)
        print("[ok ] bare_sample_in_is_a_voice")
        test_gain_effect_scales_the_voice()
        print("[ok ] gain_effect_scales_the_voice")
        test_delay_effect_echoes_past_the_note()
        print("[ok ] delay_effect_echoes_past_the_note")
        test_vst_nodes_fail_honestly_when_plugin_missing()
        print("[ok ] vst_nodes_fail_honestly_when_plugin_missing")
    print("\nSTEP 6 GROWTH: ALL OK")
