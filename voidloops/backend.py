"""
voidloops/backend.py — build-order step 4: the trivial audio backend. FIRST SOUND.

This is the *host that computes* (Machine A), in its smallest possible form: a pure-
Python additive synth that renders a compiled snapshot (voidloops/render.py) to a WAV,
reached only across Void Core's effect-handler seam (okf/concepts/render-domain.md).
It exists to prove the model by ear before the LMMS/VST harvest replaces it behind the
same seam — the backend is swappable by design.

Boundary policies (tier 3, okf/concepts/rules-and-reversibility.md) live HERE, not in
the model: the output **limiter** (hard clamp to full scale — speaker safety, the Q9
constraint), and the interpretation of model-legal-but-unrenderable content (this
backend skips zero/negative-length notes; the model keeps them — reversal is a future
backend's job, never a model rule).

Void Core never touches these samples; it only hands over the snapshot (drift test).
"""
from __future__ import annotations

import math
import struct
import wave
from pathlib import Path
from typing import Any

SAMPLE_RATE = 44100
_ENVELOPE_S = 0.005            # 5 ms attack/release ramp — declick, not an ADSR


def _freq(midi_pitch: float) -> float:
    """MIDI pitch → Hz (equal temperament, A4=440=69)."""
    return 440.0 * 2.0 ** ((midi_pitch - 69) / 12.0)


def _osc_sample(wave_name: str, phase: float) -> float:
    """One oscillator sample at `phase` (cycles); naive shapes are fine at this stage."""
    t = phase % 1.0
    if wave_name == "sine":
        return math.sin(2 * math.pi * t)
    if wave_name == "square":
        return 1.0 if t < 0.5 else -1.0
    if wave_name == "triangle":
        return 4 * abs(t - 0.5) - 1.0
    return 2 * t - 1.0             # default: saw


_SAMPLE_CACHE: dict[tuple, list[float]] = {}


def _load_sample(path: str, sample_rate: int) -> list[float]:
    """Load an audio file as mono floats, memoized (decoding may cost a subprocess).
    WAV (16-bit PCM) reads natively; anything else (ogg/flac/mp3 — most of LMMS's
    sample library) decodes through ffmpeg at this boundary (host-side I/O — the
    model never sees codecs)."""
    key = (str(path), sample_rate)
    if key not in _SAMPLE_CACHE:
        if len(_SAMPLE_CACHE) > 64:
            _SAMPLE_CACHE.clear()
        _SAMPLE_CACHE[key] = _load_sample_uncached(path, sample_rate)
    return _SAMPLE_CACHE[key]


def _load_sample_uncached(path: str, sample_rate: int) -> list[float]:
    p = Path(path)
    if not p.exists():                         # a library ref (drums/bassdrum01)?
        from . import library
        p = library.resolve(str(path))
    if p.suffix.lower() != ".wav":
        return _decode_via_ffmpeg(p, sample_rate)
    with wave.open(str(path), "rb") as w:
        n, ch, width = w.getnframes(), w.getnchannels(), w.getsampwidth()
        raw = w.readframes(n)
    if width != 2:
        return _decode_via_ffmpeg(p, sample_rate)   # odd widths: let ffmpeg normalize
    ints = struct.unpack(f"<{n * ch}h", raw)
    return [sum(ints[i * ch:(i + 1) * ch]) / ch / 32768.0 for i in range(n)]


def _decode_via_ffmpeg(path: Path, sample_rate: int) -> list[float]:
    """Decode any audio file to mono 16-bit floats via ffmpeg (piped, no temp file)."""
    import shutil
    import subprocess
    if shutil.which("ffmpeg") is None:
        raise ValueError(f"sample {path}: not a 16-bit WAV and ffmpeg is not on PATH "
                         f"to decode it")
    res = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(path), "-f", "s16le", "-acodec",
         "pcm_s16le", "-ac", "1", "-ar", str(sample_rate), "-"],
        capture_output=True)
    if res.returncode != 0:
        raise ValueError(f"sample {path}: ffmpeg decode failed: "
                         f"{res.stderr.decode(errors='replace').strip()[:200]}")
    n = len(res.stdout) // 2
    return [v / 32768.0 for v in struct.unpack(f"<{n}h", res.stdout[:n * 2])]


def _render_voice(v: dict, total: int, sample_rate: int) -> list[float]:
    """One voice's dry buffer. osc: additive synth per note. sampler: the sample
    replayed per note, naively repitched from its root. sample-in: the file at t=0."""
    kind = v["kind"]
    if kind == "vst-instrument":
        return _render_vst_voice(v, total, sample_rate)
    out = [0.0] * total
    ramp = max(int(_ENVELOPE_S * sample_rate), 1)
    content = v["content"] or {}
    if kind == "osc":
        wave_name = content.get("wave") or "saw"
        tuning = float(content.get("tuning") or 0)
        for n in v["notes"]:
            if n["length_s"] <= 0:
                continue                       # boundary policy: legal in the model, silent here
            f = _freq(n["pitch"] + tuning)
            amp = 0.5 * (n.get("velocity", 100) / 127.0)
            first = int(round(n["start_s"] * sample_rate))
            count = int(round(n["length_s"] * sample_rate))
            for k in range(count):
                idx = first + k
                if not 0 <= idx < total:
                    continue
                env = min(k / ramp, (count - 1 - k) / ramp, 1.0)
                out[idx] += amp * env * _osc_sample(wave_name, f * k / sample_rate)
    elif kind in ("sampler", "sample-in"):
        src = v.get("sample") or {}
        path = src.get("path")
        if not path:
            return out                         # unwired/unset sample: silence, not death
        data = _load_sample(path, sample_rate)
        sgain = float(src.get("gain") or 1)
        if kind == "sample-in":                # raw source: the file, once, at t=0
            for i in range(min(len(data), total)):
                out[i] += data[i] * sgain
        else:                                  # sampler: replay per note, repitched
            root = int(content.get("root") or 60)
            for n in v["notes"]:
                if n["length_s"] <= 0:
                    continue
                step = 2.0 ** ((n["pitch"] - root) / 12.0)
                amp = sgain * (n.get("velocity", 100) / 127.0)
                first = int(round(n["start_s"] * sample_rate))
                count = min(int(len(data) / step),
                            int(round(n["length_s"] * sample_rate)))
                for k in range(count):
                    idx = first + k
                    if not 0 <= idx < total:
                        continue
                    env = min(k / ramp, (count - 1 - k) / ramp, 1.0)
                    out[idx] += amp * env * data[int(k * step)]
    return out


def _apply_effect(buf: list[float], fx: dict, sample_rate: int) -> list[float]:
    """One effect node over a voice buffer. Native types: `gain` (amount =
    multiplier), `delay` (amount = seconds, feedback = echo decay), `reverb`
    (amount = wet mix 0..1; a small Schroeder network), `limiter` (amount =
    ceiling). A `vst-effect` streams the buffer through the plugin."""
    if fx.get("kind") == "vst-effect":
        return _vst_effect(buf, fx, sample_rate)
    ftype = (fx.get("type") or "gain").strip()
    if ftype == "gain":
        g = float(fx.get("amount") or 1)
        return [s * g for s in buf]
    if ftype == "delay":
        d = max(int(float(fx.get("amount") or 0.25) * sample_rate), 1)
        fb = min(max(float(fx.get("feedback") or 0.4), 0.0), 0.95)
        out = list(buf)
        for i in range(d, len(out)):
            out[i] += fb * out[i - d]
        return out
    if ftype == "reverb":
        return _reverb(buf, float(fx.get("amount") or 0.3), sample_rate)
    if ftype == "limiter":
        c = float(fx.get("amount") or 1.0) or 1.0
        return [max(-c, min(c, s)) for s in buf]
    raise ValueError(f"effect {fx.get('name')}: unknown type {ftype!r} "
                     f"(trivial backend knows: gain, delay, reverb, limiter)")


def _reverb(buf: list[float], wet: float, sample_rate: int) -> list[float]:
    """A small Schroeder reverb: four parallel combs + two series allpasses,
    tail included (~1.2 s). Simple and unmistakably a room."""
    wet = min(max(wet, 0.0), 1.0)
    if not buf or wet == 0.0:
        return list(buf)
    tail = int(1.2 * sample_rate)
    n = len(buf) + tail
    src = buf + [0.0] * tail
    combs = [(int(t * sample_rate), g) for t, g in
             ((0.0297, 0.77), (0.0371, 0.74), (0.0411, 0.72), (0.0437, 0.70))]
    acc = [0.0] * n
    for d, g in combs:
        line = [0.0] * n
        for i in range(n):
            line[i] = src[i] + (g * line[i - d] if i >= d else 0.0)
            acc[i] += line[i] * 0.25
    for d in (int(0.005 * sample_rate), int(0.0017 * sample_rate)):
        g, prev = 0.7, acc
        acc = [0.0] * n
        for i in range(n):
            back = acc[i - d] if i >= d else 0.0
            acc[i] = -g * prev[i] + (prev[i - d] if i >= d else 0.0) + g * back
    return [(1.0 - wet) * (src[i] if i < len(buf) else 0.0) + wet * acc[i]
            for i in range(n)]


# ── the VST compute holiday, in the render path ─────────────────────────────────────
# VST2 search paths — mirrors the author's FL Studio plugin manager (2026-07-08),
# including their own downloads (CustomVSTs). Scanned RECURSIVELY: plugins often
# live in vendor subfolders. VST3/CLAP are not loadable (RemoteVstPlugin is VST2).
_VST_DIRS = [Path("C:/Users/migri/Documents/Image-Line/CustomVSTs"),
             Path("C:/Program Files/Common Files/VST2"),
             Path("C:/Program Files/Image-Line/FL Studio 2025/Plugins/VST"),
             Path("C:/Program Files/VstPlugins"),
             Path("C:/Program Files/Steinberg/VstPlugins")]
_VST_BLOCK = 256
_VST_TAIL_S = 1.0                  # let releases/reverbs inside the plugin ring out
# Denormal guard: a nyquist-frequency buzz at -80 dBFS mixed into every VST input
# block. Plugins decaying to denormals crash the 1.2-era remote host (verified with
# OTT); 22 kHz at 1e-4 is inaudible and keeps their internal state energized — the
# same trick real DAW hosts use.
_GUARD = [1e-4 if i % 2 == 0 else -1e-4 for i in range(_VST_BLOCK)]


def _resolve_plugin(name: str) -> Path:
    """A plugin reference: an absolute path, or a dll name searched (recursively)
    through the VST2 folders."""
    p = Path(name)
    if p.is_absolute() and p.exists():
        return p
    want = name if name.lower().endswith(".dll") else f"{name}.dll"
    for d in _VST_DIRS:
        cand = d / want
        if cand.exists():
            return cand
        if d.is_dir():
            hit = next((f for f in d.rglob(want)), None)
            if hit:
                return hit
    raise ValueError(f"VST plugin not found: {name!r} (searched {len(_VST_DIRS)} dirs)")


def scan_vsts() -> list[dict]:
    """Every VST2 dll under the search paths (recursive), with its bitness —
    the plugin picker's source. 32-bit plugins load through RemoteVstPlugin32."""
    from .vsthost import dll_bits
    seen, out = set(), []
    for d in _VST_DIRS:
        if not d.is_dir():
            continue
        for p in sorted(d.rglob("*.dll")):
            if p.name.lower() in seen:
                continue
            seen.add(p.name.lower())
            try:
                bits = dll_bits(p)
            except OSError:
                bits = 0
            if bits:
                out.append({"name": p.name, "bits": bits, "dir": str(p.parent)})
    return sorted(out, key=lambda x: x["name"].lower())


def _load_preset(vst, preset) -> None:
    """Load a node's `preset` into a render instance when it's a .fxp/.fxb file
    (e.g. captured from the plugin's editor window — VstUiSession.save). Missing
    or unloadable presets degrade to the plugin's defaults — never fail a render."""
    p = str(preset or "").strip()
    if not p:
        return
    from pathlib import Path as _P
    if _P(p).suffix.lower() in (".fxp", ".fxb") and _P(p).exists():
        try:
            vst.load_preset(p)
        except Exception:
            pass


def _render_vst_voice(v: dict, total: int, sample_rate: int) -> list[float]:
    """A vst-instrument voice: schedule the notes as MIDI, stream silent input
    blocks through the plugin, mix its stereo output to mono."""
    from .vsthost import RemoteVstPlugin
    plugin = (v["content"] or {}).get("plugin")
    if not plugin:
        return [0.0] * total
    events = []                     # (frame, type, pitch, velocity)
    for n in v["notes"]:
        if n["length_s"] <= 0:
            continue
        first = int(round(n["start_s"] * sample_rate))
        last = first + int(round(n["length_s"] * sample_rate))
        events.append((first, 0x90, n["pitch"], n.get("velocity", 100)))
        events.append((last, 0x80, n["pitch"], 0))
    events.sort(key=lambda e: e[0])
    out = [0.0] * total
    with RemoteVstPlugin(_resolve_plugin(plugin), sample_rate=sample_rate,
                         frames=_VST_BLOCK) as vst:
        _load_preset(vst, (v["content"] or {}).get("preset"))
        ei = 0
        for base in range(0, total, _VST_BLOCK):
            while ei < len(events) and events[ei][0] < base + _VST_BLOCK:
                f, t, p, vel = events[ei]
                vst.midi(t, p, vel, offset=max(f - base, 0))
                ei += 1
            try:
                blk = vst.process(_GUARD, _GUARD)
            except RuntimeError:               # plugin died: keep what it played
                break
            for k in range(min(_VST_BLOCK, total - base)):
                out[base + k] += (blk[0][k] + blk[1][k]) / 2.0
    return out


def _vst_effect(buf: list[float], fx: dict, sample_rate: int) -> list[float]:
    """Stream a voice buffer through a vst-effect plugin, block by block (mono
    duplicated to stereo in, stereo averaged back), with a tail for its decay."""
    from .vsthost import RemoteVstPlugin
    plugin = (fx.get("plugin") or "").strip()
    if not plugin:
        return list(buf)
    total = len(buf) + int(_VST_TAIL_S * sample_rate)
    src = buf + [0.0] * (total - len(buf))
    out = [0.0] * total
    with RemoteVstPlugin(_resolve_plugin(plugin), sample_rate=sample_rate,
                         frames=_VST_BLOCK) as vst:
        _load_preset(vst, fx.get("preset"))
        for base in range(0, total, _VST_BLOCK):
            chunk = src[base:base + _VST_BLOCK]
            chunk += [0.0] * (_VST_BLOCK - len(chunk))
            chunk = [chunk[k] + _GUARD[k] for k in range(_VST_BLOCK)]
            try:
                blk = vst.process(chunk, chunk)
            except RuntimeError:               # plugin died: dry tail from here on
                out[base:] = src[base:total]
                break
            for k in range(min(_VST_BLOCK, total - base)):
                out[base + k] = (blk[0][k] + blk[1][k]) / 2.0
    return out


def render_samples(snapshot: dict[str, Any], *,
                   sample_rate: int = SAMPLE_RATE) -> list[float]:
    """Render a snapshot to float samples in [-1, 1] (mono): each voice dry, then its
    route's effect chain in order, then the additive sum, output gain, and the
    limiter. The window = the output node's `duration` when set (looping sequencers
    fill it), else the last note end / raw sample tail; effect tails extend it."""
    end_s = float((snapshot.get("meta") or {}).get("duration_s") or 0.0)
    has_tail = False
    for v in snapshot["voices"]:
        if not end_s:
            for n in v["notes"]:
                if n["length_s"] > 0:
                    end_s = max(end_s, n["start_s"] + n["length_s"])
            if v["kind"] == "sample-in" and (v.get("sample") or {}).get("path"):
                end_s = max(end_s, len(_load_sample(v["sample"]["path"],
                                                    sample_rate)) / sample_rate)
        if v["kind"] == "vst-instrument":
            has_tail = True
        for fx in v.get("effects") or []:
            if (fx.get("type") or "") in ("delay", "reverb") or \
                    fx.get("kind") == "vst-effect":
                has_tail = True
    if has_tail and end_s:
        end_s += 1.2                           # let echoes/releases ring out
    total = int(round(end_s * sample_rate))
    mix = [0.0] * total
    for v in snapshot["voices"]:
        buf = _render_voice(v, total, sample_rate)
        for fx in v.get("effects") or []:
            buf = _apply_effect(buf, fx, sample_rate)
        for i, s in enumerate(buf):
            if i < len(mix):
                mix[i] += s
            else:
                mix.append(s)                  # an effect tail grew past the window
    gain = 1.0
    for o in snapshot.get("outputs") or []:
        try:
            gain *= float(o.get("gain", 1) or 1)
        except (TypeError, ValueError):
            pass
    # the tier-3 limiter: nothing leaves this function outside full scale
    return [max(-1.0, min(1.0, s * gain)) for s in mix]


def write_wav(samples: list[float], path: str | Path, *,
              sample_rate: int = SAMPLE_RATE) -> Path:
    """Write mono 16-bit PCM WAV."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    frames = b"".join(struct.pack("<h", int(s * 32767)) for s in samples)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sample_rate)
        w.writeframes(frames)
    return path


def render_wav(snapshot: dict[str, Any], path: str | Path, *,
               sample_rate: int = SAMPLE_RATE) -> Path:
    """snapshot → WAV file. The whole backend in one call."""
    return write_wav(render_samples(snapshot, sample_rate=sample_rate), path,
                     sample_rate=sample_rate)


def play_wav(path: str | Path) -> None:
    """Play a WAV on the default device (Windows: stdlib winsound; else best-effort)."""
    try:
        import winsound
        winsound.PlaySound(str(path), winsound.SND_FILENAME)
    except ImportError:                        # non-Windows fallback: leave the file
        pass
