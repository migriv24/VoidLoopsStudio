"""
voidloops — Void Loops Studio, a pattern-based DAW built on top of Void Core.

This package is the **application layer** (Machine B in `okf/concepts/daw-architecture.md`):
it owns the project/arrangement model and orchestrates a host audio engine. It computes
no audio itself — that is the host's job, reached across the effect-handler boundary.

Foundation: the `voidcore` package (rune/mantle/holiday model, the dispatcher, and the
Scry/Temper/Reduce transformation layers). Install it editable first:

    pip install -e ../VoidCore

Build order: this is step 0 — the project skeleton + a green dispatcher round-trip.
See `okf/roadmap.md`.
"""
from __future__ import annotations

from . import model
from .model import ProjectMeta, pitch, pitch_name, ticks_to_seconds
from .project import VoidLoopsProject
from .render import compile_render, render_reduce_spec

__all__ = [
    "VoidLoopsProject", "model", "ProjectMeta",
    "pitch", "pitch_name", "ticks_to_seconds",
    "compile_render", "render_reduce_spec",
]
__version__ = "0.0.1"
