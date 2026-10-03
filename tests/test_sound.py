"""
Step-4 tests: FIRST SOUND — the trivial backend renders the compiled snapshot to real
audio, reached only across the effect-handler seam. The melody is verified *acoustically*
(zero-crossing pitch detection on the rendered samples), not just structurally.

Runnable via `pytest` or `python tests/test_sound.py`.
"""
from __future__ import annotations

import wave as wave_mod
from pathlib import Path

from voidloops import VoidLoopsProject, compile_render
from voidloops.backend import SAMPLE_RATE, render_samples, render_wav

from test_patch import _first_sound


def _dominant_freq(samples: list[float], start_s: float, end_s: float) -> float:
    """Estimate pitch by zero-crossing rate over [start_s, end_s) — crude, but plenty
    to tell C4 from E4."""
    lo, hi = int(start_s * SAMPLE_RATE), int(end_s * SAMPLE_RATE)
    seg = samples[lo:hi]
    crossings = sum(1 for a, b in zip(seg, seg[1:]) if (a < 0) <= (b >= 0) and a < 0 <= b)
    return crossings / (len(seg) / SAMPLE_RATE)


def test_first_sound_renders_the_melody():
    with VoidLoopsProject() as proj:
        _first_sound(proj)
        samples = render_samples(compile_render(proj))
        assert len(samples) == 2 * SAMPLE_RATE            # 4 quarter notes @ 120 BPM
        assert max(abs(s) for s in samples) > 0.1         # audibly non-silent
        # the arpeggio, heard: C4 E4 G4 C5 (zero-crossing estimate, ±6%)
        for i, expected in enumerate([261.63, 329.63, 392.0, 523.25]):
            f = _dominant_freq(samples, i * 0.5 + 0.05, i * 0.5 + 0.45)
            assert abs(f - expected) / expected < 0.06, (i, f, expected)


def test_limiter_keeps_full_scale():
    with VoidLoopsProject() as proj:
        proj.new_pattern("loud")
        mix = proj.add_node("mix", gain=1)
        out = proj.add_node("output", gain=8)             # absurd gain: model allows it
        proj.wire(mix, out)
        for _ in range(4):                                # four stacked max-velocity voices
            seq = proj.add_node("sequencer")
            osc = proj.add_node("osc", wave="square")
            proj.wire(seq, osc)
            proj.wire(osc, mix)
            proj.add_note("C4", 0, 96, velocity=127, node=seq)
        samples = render_samples(compile_render(proj))
        assert max(abs(s) for s in samples) <= 1.0        # the tier-3 limiter held


def test_zero_and_negative_length_skipped_not_fatal():
    with VoidLoopsProject() as proj:
        proj.new_pattern("weird")
        seq = proj.add_node("sequencer")
        osc = proj.add_node("osc")
        out = proj.add_node("output", gain=1)
        proj.wire(seq, osc)
        proj.wire(osc, out)
        proj.add_note("C4", 0, -96, node=seq)             # legal in the model (reversal)
        proj.add_note("C4", 0, 0, node=seq)
        samples = render_samples(compile_render(proj))    # boundary policy: skip, don't die
        assert samples == []                              # nothing renderable -> silence


def test_wav_roundtrip(tmp_path: Path):
    with VoidLoopsProject() as proj:
        _first_sound(proj)
        path = render_wav(compile_render(proj), tmp_path / "first-sound.wav")
        with wave_mod.open(str(path), "rb") as w:
            assert w.getframerate() == SAMPLE_RATE
            assert w.getnchannels() == 1
            assert w.getnframes() == 2 * SAMPLE_RATE


def test_effect_seam_deploy(tmp_path: Path):
    with VoidLoopsProject() as proj:
        _first_sound(proj)
        proj.attach_trivial_backend()
        target = tmp_path / "bounce.wav"
        res = proj.cmd(f"deploy {target}")
        assert res["ok"], res["lines"]
        assert target.exists() and target.stat().st_size > 100_000


if __name__ == "__main__":
    import tempfile

    flat = [
        ("first_sound_renders_the_melody", test_first_sound_renders_the_melody),
        ("limiter_keeps_full_scale", test_limiter_keeps_full_scale),
        ("zero_and_negative_length_skipped", test_zero_and_negative_length_skipped_not_fatal),
    ]
    for name, fn in flat:
        fn()
        print(f"[ok ] {name}")
    with tempfile.TemporaryDirectory() as d:
        test_wav_roundtrip(Path(d))
        print("[ok ] wav_roundtrip")
        test_effect_seam_deploy(Path(d))
        print("[ok ] effect_seam_deploy")
    print("\nSTEP 4 SOUND: ALL OK")
