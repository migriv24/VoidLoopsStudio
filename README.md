# Void Loops Studio

A **node-based DAW** (FL Studio / LMMS lineage, pivoted to dataflow), built from
scratch **on top of [Void Core](../VoidCore)** with interaction nets as its
structural foundation.

The design lives in the OKF bundle under [`okf/`](okf/) — start at
[`okf/index.md`](okf/index.md), [`okf/roadmap.md`](okf/roadmap.md), and the open decisions
in [`okf/developer_questions.md`](okf/developer_questions.md). The governing idea: a DAW is
two machines — an **audio engine that computes samples** and a **project model that only
describes**. Void Loops owns the second (on Void Core) and orchestrates the first; it never
touches a sample buffer (the *drift test*). The project is a **node graph** (dataflow /
patching), not a timeline.

> Studying the bundle: point **FaultSack** (`../FaultSack`) at this repo — it builds the
> module map + study site the old in-tree `okf/viz/` viewer used to provide.

## Status

**The native era (2026-07-09 →).** The Python prototype reached v1 (typed node
graph, real VSTs via the RemoteVstPlugin protocol, looping sequences, tag-routed
FX, the LiteGraph editor) and is now the **reference implementation + test
harness**. The real application is C++20 in [`native/`](native/), built on
**[Void Maiz](../VoidMaiz)** (our node-graph UI library; declared ready
2026-07-16) — milestone 1 (the shell skeleton: VLS glyph set, starter patch,
canvas/inspector/log/command-bar, project file) is in. The milestone list lives
in the roadmap's native build order.

## The native shell (`native/`)

```bash
cmake -S native -B native/build -G Ninja   # expects ../VoidMaiz (and its ../VoidCore) checked out
cmake --build native/build
ctest --test-dir native/build --output-on-failure
native/build/bin/vls_native                # opens ~/Documents/VoidLoopsProjects/default.native.vlp.json
```

The exe is self-contained (GCC runtime static-linked; only `libvoidcore.dll`
rides beside it). For a desktop launcher — the successor to the Python era's
`VoidLoops.bat` icon — run once after building:

```bash
powershell -ExecutionPolicy Bypass -File native/install_shortcut.ps1
```

Built with the msys64 **ucrt64** toolchain; if a test binary dies at load with
0xc0000139 under Git Bash, put `/c/msys64/ucrt64/bin` first on `PATH` (Git's
own `libstdc++-6.dll` shadows the right one).

## The Python reference implementation (`voidloops/`)

Depends on the `voidcore` package, installed **editable** from its repo (it
ships a native `libvoidcore.dll`, so it is not a PyPI package):

```bash
pip install -e ../VoidCore   # the foundation
pip install -e .                                             # this package
python -m voidloops --ui     # the LiteGraph editor on ~/Documents/VoidLoopsProjects/default.vlp.json
pytest                       # the 16-file behavioral spec the native build must match
```

Maintenance only (bug fixes, capture); new features land native-side.

## Layout

```
native/          the C++20 application (on Void Maiz) — where development happens
  src/glyphs.*   the VLS glyph set (ported from voidloops/model.py; numeric "i:j" wires)
  src/app.cpp    the shell: canvas + inspector + log strip + command bar
voidloops/       the Python reference implementation (model/render semantics = the spec)
tests/           the Python test suite (the behavioral spec)
okf/             the design bundle (Open Knowledge Format) — the source of truth
```
