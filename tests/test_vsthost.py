"""
VST compute-holiday tests: the pure-Python RemoteVstPlugin client end-to-end with a
real commercial plugin (Xfer OTT). Skips gracefully when the exe or dll is absent.

Runnable via `pytest` or `python tests/test_vsthost.py`.
"""
from __future__ import annotations

import math
from pathlib import Path

from voidloops.vsthost import REMOTE_EXE, RemoteVstPlugin

OTT = Path("C:/Program Files/Common Files/VST2/OTT_x64.dll")


def _available() -> bool:
    return REMOTE_EXE.exists() and OTT.exists()


def test_load_process_shutdown():
    if not _available():
        print("      (skipped: RemoteVstPlugin exe or OTT dll not present)")
        return
    with RemoteVstPlugin(OTT, timeout_s=25) as vst:
        assert vst.info.get("name") == "OTT"
        assert vst.info.get("vendor") == "Xfer Records"
        assert (vst.inputs, vst.outputs) == (2, 2)
        sine = [0.5 * math.sin(2 * math.pi * 440 * i / 44100) for i in range(256)]
        # several blocks: output must be present and bounded
        peaks = []
        for _ in range(8):
            outs = vst.process(sine, sine)
            assert len(outs) == 2 and all(len(ch) == 256 for ch in outs)
            peaks.append(max(max(abs(s) for s in ch) for ch in outs))
        assert max(peaks) > 0.01                      # the plugin really processed
        assert max(peaks) <= 4.0                      # and didn't explode
        vst.midi(0x90, 60, 100)                       # midi queue doesn't wedge an fx
        vst.process(sine, sine)


def test_preset_roundtrip():
    """The window-face's persistence path, headless: save the plugin's state as a
    standard .fxp, load it into a FRESH instance (what every render does with a
    node's `preset`). savePreset handles chunk AND plain-parameter plugins."""
    if not _available():
        print("      (skipped: RemoteVstPlugin exe or OTT dll not present)")
        return
    import tempfile
    fxp = Path(tempfile.gettempdir()) / "vls-test-preset.fxp"
    if fxp.exists():
        fxp.unlink()
    with RemoteVstPlugin(OTT, timeout_s=25) as vst:
        vst.save_preset(fxp)
    assert fxp.exists() and fxp.stat().st_size > 0
    assert fxp.read_bytes()[:4] == b"CcnK"           # the VST preset magic
    with RemoteVstPlugin(OTT, timeout_s=25) as vst:
        vst.load_preset(fxp)                         # ack received = state applied
        sine = [0.1] * 256
        outs = vst.process(sine, sine)               # still processes after load
        assert len(outs) == 2
    fxp.unlink()


def test_missing_dll_fails_loud():
    if not REMOTE_EXE.exists():
        print("      (skipped: RemoteVstPlugin exe not present)")
        return
    try:
        RemoteVstPlugin("C:/does/not/exist.dll")
        assert False, "expected FileNotFoundError"
    except FileNotFoundError:
        pass


if __name__ == "__main__":
    test_load_process_shutdown()
    print("[ok ] load_process_shutdown")
    test_preset_roundtrip()
    print("[ok ] preset_roundtrip")
    test_missing_dll_fails_loud()
    print("[ok ] missing_dll_fails_loud")
    print("\nVST HOST: ALL OK")
