"""
voidloops/vsthost.py — the VST compute holiday: a pure-Python client for LMMS's
RemoteVstPlugin (the out-of-process VST host harvested per the 2026-07-07 spike;
protocol read from LMMS **1.2.2** — the installed exe's vintage — RemotePlugin.h +
vst_base/communication.h).

No C++ on our side. The exe speaks LMMS's shm-FIFO protocol, which on Windows is
Qt 5 kernel objects; we recreate them with ctypes:

- **Qt name mangling** (Qt 5.x `makePlatformSafeKey`): `prefix + [A-Za-z of key] +
  sha1_hex(key)` — prefixes `qipc_sharedmemory_` / `qipc_systemsem_`.
- **A FIFO** = one shared-memory block: `sem32_t dataSem` (32-byte union, .semKey at
  +0), `sem32_t messageSem` (+32), `int32 startPtr` (+64), `int32 endPtr` (+68),
  `char data[512*1024]` (+72). The master (us) picks the smallest free integer shm
  key, stores fresh semaphore keys `(pid<<10)+n` in the struct, and creates the
  semaphores (data=1, message=0).
- **A message** = `int32 id, int32 argc, argc * (int32 len + bytes)` written under
  the data semaphore, then one release of the message semaphore. All argument values
  (ints included) travel as strings.
- **Spawn**: `RemoteVstPlugin.exe <our-out-key> <our-in-key>` (in/out swapped for the
  remote), cwd = the LMMS install dir (Qt DLLs).
- **Audio**: a separate float shm block announced with `IdChangeSharedMemoryKey
  (key, bytes)`; layout inputs then outputs, non-interleaved; per block:
  `IdStartProcessing` → wait `IdProcessingDone`.

This is Machine A territory: everything here is host-side I/O behind the holiday
boundary — the model never imports this module.
"""
from __future__ import annotations

import ctypes
import ctypes.wintypes as wt
import hashlib
import os
import re
import struct
import subprocess
import time
from pathlib import Path

_k32 = ctypes.WinDLL("kernel32", use_last_error=True)

_PAGE_READWRITE = 0x04
_FILE_MAP_ALL = 0x000F001F
_ERROR_ALREADY_EXISTS = 183
_INFINITE = 0xFFFFFFFF

LMMS_DIR = Path("C:/Program Files/LMMS")
REMOTE_EXE = LMMS_DIR / "plugins" / "RemoteVstPlugin.exe"      # 64-bit
REMOTE_EXE_32 = LMMS_DIR / "plugins" / "32" / "RemoteVstPlugin32.exe"


def dll_bits(path: str | Path) -> int:
    """A dll/exe's bitness from its PE header (0x14c = x86, 0x8664 = x64)."""
    with open(path, "rb") as f:
        f.seek(0x3C)
        pe_off = int.from_bytes(f.read(4), "little")
        f.seek(pe_off)
        if f.read(4) != b"PE\x00\x00":
            return 0
        machine = int.from_bytes(f.read(2), "little")
    return {0x14C: 32, 0x8664: 64}.get(machine, 0)


def exe_for(dll_path: str | Path) -> Path:
    """The RemoteVstPlugin exe matching the plugin's bitness."""
    return REMOTE_EXE_32 if dll_bits(dll_path) == 32 else REMOTE_EXE

SHM_FIFO_SIZE = 512 * 1024
_OFF_DATA_SEM, _OFF_MSG_SEM, _OFF_START, _OFF_END, _OFF_DATA = 0, 32, 64, 68, 72
_FIFO_BYTES = _OFF_DATA + SHM_FIFO_SIZE

# RemoteMessageIDs (1.2)
IdUndefined, IdHostInfoGotten, IdInitDone, IdQuit = 0, 1, 2, 3
IdSampleRateInformation, IdBufferSizeInformation, IdInformationUpdated = 4, 5, 6
IdMidiEvent, IdStartProcessing, IdProcessingDone, IdChangeSharedMemoryKey = 7, 8, 9, 10
IdChangeInputCount, IdChangeOutputCount, IdChangeInputOutputCount = 11, 12, 13
IdShowUI, IdHideUI, IdToggleUI, IdIsUIVisible = 14, 15, 16, 17
IdSaveSettingsToString, IdSaveSettingsToFile = 18, 19
IdLoadSettingsFromString, IdLoadSettingsFromFile = 20, 21
IdSavePresetFile, IdLoadPresetFile = 22, 23
IdDebugMessage = 24
IdUserBase = 64
# VstRemoteMessageIDs (1.2, from IdUserBase in order)
IdVstLoadPlugin = 64
IdVstFailedLoadingPlugin = 77
IdVstBadDllFormat = 78
IdVstPluginName = 81
IdVstPluginVersion = 82
IdVstPluginVendorString = 83
IdVstPluginProductString = 84
IdVstPluginUniqueID = 86


def _qt_name(key: str, prefix: str) -> str:
    return prefix + re.sub(r"[^A-Za-z]", "", key) + \
        hashlib.sha1(key.encode()).hexdigest()


class _QtSharedMemory:
    """A Qt-5-named file mapping we create (master side)."""

    def __init__(self, key: str, size: int):
        name = _qt_name(key, "qipc_sharedmemory_")
        self._h = _k32.CreateFileMappingW(wt.HANDLE(-1), None, _PAGE_READWRITE,
                                          0, size, name)
        if not self._h:
            raise OSError(f"CreateFileMapping failed: {ctypes.get_last_error()}")
        self.existed = ctypes.get_last_error() == _ERROR_ALREADY_EXISTS
        if self.existed:
            _k32.CloseHandle(self._h)
            self._h = None
            return
        _k32.MapViewOfFile.restype = ctypes.c_void_p
        self._addr = _k32.MapViewOfFile(self._h, _FILE_MAP_ALL, 0, 0, 0)
        if not self._addr:
            raise OSError(f"MapViewOfFile failed: {ctypes.get_last_error()}")
        self.buf = (ctypes.c_char * size).from_address(self._addr)
        ctypes.memset(self._addr, 0, size)

    def close(self):
        if getattr(self, "_addr", None):
            _k32.UnmapViewOfFile(ctypes.c_void_p(self._addr))
            self._addr = None
        if self._h:
            _k32.CloseHandle(self._h)
            self._h = None


def _alloc_shm(size: int, start_key: int = 1) -> tuple[int, _QtSharedMemory]:
    """The smallest free integer key (Qt's counter dance) + its created mapping."""
    key = start_key
    while True:
        shm = _QtSharedMemory(str(key), size)
        if not shm.existed:
            return key, shm
        key += 1


class _QtSemaphore:
    def __init__(self, key: str, initial: int):
        name = _qt_name(key, "qipc_systemsem_")
        self._h = _k32.CreateSemaphoreW(None, initial, 0x7FFFFFFF, name)
        if not self._h:
            raise OSError(f"CreateSemaphore failed: {ctypes.get_last_error()}")

    def acquire(self, timeout_s: float = None) -> bool:
        ms = _INFINITE if timeout_s is None else int(timeout_s * 1000)
        return _k32.WaitForSingleObject(self._h, ms) == 0

    def release(self):
        _k32.ReleaseSemaphore(self._h, 1, None)

    def close(self):
        if self._h:
            _k32.CloseHandle(self._h)
            self._h = None


_sem_counter = [0]


class ShmFifo:
    """Master side of one LMMS shm FIFO."""

    def __init__(self):
        self.key, self._shm = _alloc_shm(_FIFO_BYTES)
        _sem_counter[0] += 1
        data_key = (os.getpid() << 10) + _sem_counter[0]
        _sem_counter[0] += 1
        msg_key = (os.getpid() << 10) + _sem_counter[0]
        struct.pack_into("<i", self._shm.buf, _OFF_DATA_SEM, data_key)
        struct.pack_into("<i", self._shm.buf, _OFF_MSG_SEM, msg_key)
        struct.pack_into("<ii", self._shm.buf, _OFF_START, 0, 0)
        self._data_sem = _QtSemaphore(str(data_key), 1)
        self._msg_sem = _QtSemaphore(str(msg_key), 0)
        self._depth = 0

    # C++ shmFifo lock-depth semantics
    def lock(self):
        if self._depth == 0:
            self._data_sem.acquire()
        self._depth += 1

    def unlock(self):
        self._depth -= 1
        if self._depth == 0:
            self._data_sem.release()

    def _ptrs(self) -> tuple[int, int]:
        return struct.unpack_from("<ii", self._shm.buf, _OFF_START)

    def _write(self, payload: bytes):
        self.lock()
        try:
            start, end = self._ptrs()
            if len(payload) > SHM_FIFO_SIZE - end:
                data = bytes(self._shm.buf[_OFF_DATA + start:_OFF_DATA + end])
                self._shm.buf[_OFF_DATA:_OFF_DATA + len(data)] = data
                start, end = 0, len(data)
            self._shm.buf[_OFF_DATA + end:_OFF_DATA + end + len(payload)] = payload
            struct.pack_into("<ii", self._shm.buf, _OFF_START, start,
                             end + len(payload))
        finally:
            self.unlock()

    def _read(self, n: int, timeout_s: float) -> bytes:
        deadline = time.monotonic() + timeout_s
        while True:
            self.lock()
            start, end = self._ptrs()
            if end - start >= n:
                out = bytes(self._shm.buf[_OFF_DATA + start:_OFF_DATA + start + n])
                start += n
                if start == end:
                    start = end = 0
                struct.pack_into("<ii", self._shm.buf, _OFF_START, start, end)
                self.unlock()
                return out
            self.unlock()
            if time.monotonic() > deadline:
                raise TimeoutError("shm FIFO read timed out")
            time.sleep(0.001)

    # ── message framing ───────────────────────────────────────────────────────
    def send(self, mid: int, args: list = ()) -> None:
        self.lock()
        try:
            payload = struct.pack("<ii", mid, len(args))
            for a in args:
                s = str(a).encode() if not isinstance(a, bytes) else a
                payload += struct.pack("<i", len(s)) + s
            self._write(payload)
        finally:
            self.unlock()
        self._msg_sem.release()

    def recv(self, timeout_s: float = 10.0) -> tuple[int, list[bytes]]:
        if not self._msg_sem.acquire(timeout_s):
            raise TimeoutError("no message from remote plugin")
        mid, argc = struct.unpack("<ii", self._read(8, timeout_s))
        args = []
        for _ in range(argc):
            n = struct.unpack("<i", self._read(4, timeout_s))[0]
            args.append(self._read(n, timeout_s) if n else b"")
        return mid, args

    def close(self):
        for x in (self._data_sem, self._msg_sem, self._shm):
            x.close()


class RemoteVstPlugin:
    """Drive one VST plugin inside LMMS's RemoteVstPlugin.exe (64-bit).

        with RemoteVstPlugin("C:/.../OTT_x64.dll") as vst:
            out_l, out_r = vst.process(in_l, in_r)

    The exe hosts the plugin out-of-process; we are the LMMS-master side."""

    def __init__(self, dll_path: str | Path, *, sample_rate: int = 44100,
                 frames: int = 256, exe: Path = None, timeout_s: float = 20.0,
                 embed: str = "headless"):
        if not Path(dll_path).exists():
            raise FileNotFoundError(f"VST dll not found: {dll_path}")
        exe = Path(exe) if exe else exe_for(dll_path)   # match the plugin's bitness
        if not exe.exists():
            raise FileNotFoundError(f"RemoteVstPlugin exe not found: {exe}")
        self.sample_rate, self.frames = sample_rate, frames
        self.inputs = self.outputs = 2
        self.info: dict[str, str] = {}
        self._audio = None
        self._audio_key = None
        # remote's in = our out (arg order per RemotePlugin::init)
        self.fifo_out = ShmFifo()
        self.fifo_in = ShmFifo()
        env = dict(os.environ)
        env["PATH"] = str(LMMS_DIR) + os.pathsep + env.get("PATH", "")
        # argv: <our-out-key> <our-in-key> <embed-method>. "headless" = no editor;
        # "none" = the plugin's own editor as a detached native window (1.2's
        # official value — RemoteVstPlugin.cpp: "Starting detached.")
        self._proc = subprocess.Popen(
            [str(exe), str(self.fifo_out.key), str(self.fifo_in.key), embed],
            cwd=str(LMMS_DIR), env=env,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.fifo_out.send(IdSampleRateInformation, [sample_rate])
        self.fifo_out.send(IdBufferSizeInformation, [frames])
        self.fifo_out.send(IdVstLoadPlugin, [str(dll_path)])
        self._pump_until(IdInitDone, timeout_s)
        self._setup_audio_shm()

    # ── the message pump ──────────────────────────────────────────────────────
    def _handle(self, mid: int, args: list[bytes]) -> None:
        text = [a.decode(errors="replace") for a in args]
        if mid == IdVstFailedLoadingPlugin:
            raise RuntimeError("remote host failed to load the plugin")
        if mid == IdVstBadDllFormat:
            raise RuntimeError("bad dll format (32/64-bit mismatch?)")
        if mid == IdChangeInputCount:
            self.inputs = int(text[0])
        elif mid == IdChangeOutputCount:
            self.outputs = int(text[0])
        elif mid == IdChangeInputOutputCount:
            self.inputs, self.outputs = int(text[0]), int(text[1])
        elif mid == IdVstPluginName:
            self.info["name"] = text[0]
        elif mid == IdVstPluginVersion:
            self.info["version"] = text[0]
        elif mid == IdVstPluginVendorString:
            self.info["vendor"] = text[0]
        elif mid == IdVstPluginProductString:
            self.info["product"] = text[0]
        elif mid == IdVstPluginUniqueID:
            self.info["unique_id"] = text[0]
        elif mid == IdDebugMessage:
            pass                                    # remote-side chatter

    def _pump_until(self, target: int, timeout_s: float = 10.0) -> list[bytes]:
        deadline = time.monotonic() + timeout_s
        while True:
            if self._proc.poll() is not None:
                raise RuntimeError(
                    f"RemoteVstPlugin exited (code {self._proc.returncode}) "
                    f"before sending message {target}")
            mid, args = self.fifo_in.recv(max(deadline - time.monotonic(), 0.1))
            if mid == target:
                return args
            self._handle(mid, args)
            if time.monotonic() > deadline:
                raise TimeoutError(f"never received message {target}")

    # ── audio ────────────────────────────────────────────────────────────────
    def _setup_audio_shm(self):
        size = self.frames * (self.inputs + self.outputs) * 4
        self._audio_key, self._audio = _alloc_shm(size, start_key=1)
        self.fifo_out.send(IdChangeSharedMemoryKey, [self._audio_key, size])

    def process(self, *channels: list[float]) -> list[list[float]]:
        """One block: input channel lists (padded/truncated to `frames`) →
        output channel lists. Raises RuntimeError if the remote died (some plugins
        crash the 1.2 host on denormal-decay tails — feed a guard noise floor)."""
        fr = self.frames
        for c in range(self.inputs):
            ch = list(channels[c]) if c < len(channels) else []
            ch = (ch + [0.0] * fr)[:fr]
            struct.pack_into(f"<{fr}f", self._audio.buf, c * fr * 4, *ch)
        self.fifo_out.send(IdStartProcessing)
        try:
            self._pump_until(IdProcessingDone)
        except TimeoutError:
            if self._proc.poll() is not None:
                raise RuntimeError(
                    f"remote plugin process died mid-render "
                    f"(exit {self._proc.returncode})") from None
            raise
        out = []
        for c in range(self.outputs):
            off = (self.inputs + c) * fr * 4
            out.append(list(struct.unpack_from(f"<{fr}f", self._audio.buf, off)))
        return out

    def midi(self, mtype: int, data1: int, data2: int, offset: int = 0,
             channel: int = 0) -> None:
        """Queue a MIDI event for the next block. 1.2 wire format: five ints —
        type (0x90 note-on / 0x80 note-off), channel, param0, param1, frame offset."""
        self.fifo_out.send(IdMidiEvent, [mtype, channel, data1, data2, offset])

    # ── the plugin's own editor window + settings (the VST-node-as-window face) ──
    def show_ui(self) -> None:
        """Show the plugin's editor (a detached native window; requires
        `embed='none'` at spawn — under 'headless' the remote ignores this)."""
        self.fifo_out.send(IdShowUI)

    def hide_ui(self) -> None:
        self.fifo_out.send(IdHideUI)

    def save_preset(self, path: str | Path, timeout_s: float = 10.0) -> Path:
        """Save the plugin's current state as a standard VST preset file (.fxp;
        .fxb saves the whole bank) and wait for the remote's ack. Works for both
        chunk-style and plain-parameter plugins (RemoteVstPlugin::savePreset) —
        this is what knob tweaks in the editor window become."""
        path = Path(path)
        self.fifo_out.send(IdSavePresetFile, [str(path)])
        self._pump_until(IdSavePresetFile, timeout_s)
        return path

    def load_preset(self, path: str | Path, timeout_s: float = 10.0) -> None:
        """Load a .fxp/.fxb preset saved by `save_preset` and wait for the ack."""
        self.fifo_out.send(IdLoadPresetFile, [str(Path(path))])
        self._pump_until(IdLoadPresetFile, timeout_s)

    # ── lifecycle ────────────────────────────────────────────────────────────
    def close(self):
        try:
            if self._proc.poll() is None:
                self.fifo_out.send(IdQuit)
                try:
                    self._proc.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    self._proc.kill()
        finally:
            for x in (self.fifo_in, self.fifo_out, self._audio):
                if x is not None:
                    x.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


class VstUiSession:
    """A live, non-rendering plugin instance whose editor window is on screen —
    the 'VST node as a window' face. A daemon pump drains the remote's messages
    (knob moves stream `IdVstSetParameter`s; an undrained FIFO would freeze the
    plugin's GUI). Knob state is captured with `save()` → a settings chunk file
    the render-side instances load back (`preset` on the node)."""

    def __init__(self, dll_path: str | Path, **kw):
        import threading
        self.vst = RemoteVstPlugin(dll_path, embed="none", **kw)
        self.vst.show_ui()
        self._stop = threading.Event()
        self._save_req: list = []          # (path,) requests served by the pump
        self._saved: dict[str, bool] = {}
        self._pump = threading.Thread(target=self._run, daemon=True)
        self._pump.start()

    def _run(self):
        while not self._stop.is_set():
            if self.vst._proc.poll() is not None:
                break                                   # window closed / crashed
            if self._save_req:
                path = self._save_req.pop(0)
                try:
                    self.vst.save_preset(path)          # pump-thread FIFO reads
                    self._saved[str(path)] = path.exists()
                except Exception:
                    self._saved[str(path)] = False
                continue
            try:
                mid, args = self.vst.fifo_in.recv(timeout_s=0.25)
                self.vst._handle(mid, args)
            except TimeoutError:
                continue
            except Exception:
                break

    @property
    def alive(self) -> bool:
        return self.vst._proc.poll() is None and self._pump.is_alive()

    def save(self, path: str | Path, timeout_s: float = 10.0) -> bool:
        """Capture the plugin's current state (all knob positions) to `path`."""
        import time as _t
        key = str(Path(path))
        self._saved.pop(key, None)
        self._save_req.append(Path(path))
        deadline = _t.monotonic() + timeout_s
        while key not in self._saved and _t.monotonic() < deadline:
            _t.sleep(0.05)
        return self._saved.get(key, False)

    def close(self):
        self._stop.set()
        self._pump.join(timeout=2)
        self.vst.close()
