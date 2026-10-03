"""
voidloops/library.py — the sound library: LMMS's harvested sample corpus, browsable.

The first concrete "sample library as a query-backed source"
(okf/concepts/instrument-as-holiday.md): an index over LMMS's `data/samples`
(drums, basses, beats, latin, instruments, …) — every format the backend can decode
(wav natively; ogg/flac/mp3 via the ffmpeg boundary). Credit where due: this content
is the LMMS community's work — https://github.com/LMMS/lmms · https://lmms.io

`refs` are stable, path-shaped ids like `drums/bassdrum01` (extension elided when
unambiguous). `search("kick")` finds; `resolve(ref)` yields the absolute path;
`VoidLoopsProject.add_instrument(ref)` drops a ready-to-play sampler into the patch.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

PLAYABLE = {".wav", ".ogg", ".flac", ".mp3", ".aiff"}

LIBRARY_DIRS = [
    Path("C:/Users/migri/Documents/Projects/lmms/data/samples"),   # the clone
    Path("C:/Program Files/LMMS/data/samples"),                    # the install
]

_index: Optional[dict[str, Path]] = None


def _build_index() -> dict[str, Path]:
    idx: dict[str, Path] = {}
    for root in LIBRARY_DIRS:
        if not root.is_dir():
            continue
        for p in sorted(root.rglob("*")):
            if p.suffix.lower() not in PLAYABLE or not p.is_file():
                continue
            rel = p.relative_to(root).as_posix()
            short = rel[:-len(p.suffix)]
            for ref in (short, rel):
                idx.setdefault(ref, p)         # first root wins; ext form always valid
    return idx


def _idx() -> dict[str, Path]:
    global _index
    if _index is None:
        _index = _build_index()
    return _index


def refresh() -> int:
    """Rebuild the index (e.g. after adding library dirs); returns entry count."""
    global _index
    _index = None
    return len(_idx())


def search(query: str = "", limit: int = 50) -> list[dict]:
    """Samples whose ref contains every word of `query` (case-insensitive), as
    `{ref, category, name}` — category = the top folder (drums, basses, …)."""
    words = [w.lower() for w in query.split() if w]
    out = []
    for ref, path in _idx().items():
        if "." in Path(ref).name:              # skip the extension-duplicate form
            continue
        hay = ref.lower()
        if all(w in hay for w in words):
            parts = ref.split("/")
            out.append({"ref": ref,
                        "category": parts[0] if len(parts) > 1 else "",
                        "name": parts[-1]})
            if len(out) >= limit:
                break
    return out


def resolve(ref: str) -> Path:
    """A library ref (or an absolute path) → the sample's absolute path."""
    p = Path(ref)
    if p.is_absolute() and p.exists():
        return p
    hit = _idx().get(ref)
    if hit is None:
        raise ValueError(f"sample not in library: {ref!r} (try search())")
    return hit


def categories() -> list[str]:
    """The library's top-level folders (the browser's sidebar)."""
    return sorted({r.split("/")[0] for r in _idx() if "/" in r})
