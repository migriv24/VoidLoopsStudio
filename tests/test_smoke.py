"""
Step-0 smoke test: the project skeleton stands up and the dispatcher round-trips.

Runnable two ways:
    pytest                       # discovered as test_* functions
    python tests/test_smoke.py   # plain-asserts runner, prints a summary

What it proves (and only this — the DAW model is step 1):
- a project opens on the live Void Core,
- the Dispatcher superset delegates C-core verbs unchanged (mantle/rune/ls),
- mutation + undo work,
- a transform verb (scry) is reachable through the same surface,
- state round-trips through disk and a fresh manager.
"""
from __future__ import annotations

import json
from pathlib import Path

from voidloops import VoidLoopsProject


def test_opens_on_voidcore():
    with VoidLoopsProject() as proj:
        assert proj.version  # e.g. "0.1.0" from the C core


def test_dispatcher_roundtrips_core_verbs():
    with VoidLoopsProject() as proj:
        assert proj.cmd("mantle new p1")["ok"]
        assert proj.cmd("rune new text kick")["ok"]
        assert proj.cmd('set kick value "boom"')["ok"]
        assert proj.cmd("ls")["data"] == ["kick"]
        assert proj.cmd("get kick value")["data"] == "boom"


def test_undo_redo():
    with VoidLoopsProject() as proj:
        proj.cmd("mantle new p1")
        proj.cmd("rune new text k")
        proj.cmd('set k value "v1"')
        proj.cmd('set k value "v2"')
        assert proj.cmd("get k value")["data"] == "v2"
        assert proj.cmd("undo")["ok"]
        assert proj.cmd("get k value")["data"] == "v1"


def test_transform_verb_reachable():
    # scry is added by the Dispatcher superset, not the C core — prove it routes.
    with VoidLoopsProject() as proj:
        proj.cmd("mantle new p1")
        proj.cmd("rune new text a")
        proj.cmd("rune new text b")
        res = proj.cmd('scry "a"')
        assert res["ok"] and res["data"] == ["a"]


def test_state_roundtrips_through_disk(tmp_path: Path):
    path = tmp_path / "proj.vlp.json"
    with VoidLoopsProject(path) as proj:
        proj.cmd("mantle new p1")
        proj.cmd("rune new text snare")
        proj.save()
    assert json.loads(path.read_text(encoding="utf-8"))["mantles"]
    with VoidLoopsProject(path) as reopened:
        assert reopened.cmd("use p1")["ok"]
        assert reopened.cmd("ls")["data"] == ["snare"]


if __name__ == "__main__":
    import tempfile

    tests = [
        ("opens_on_voidcore", test_opens_on_voidcore),
        ("dispatcher_roundtrips_core_verbs", test_dispatcher_roundtrips_core_verbs),
        ("undo_redo", test_undo_redo),
        ("transform_verb_reachable", test_transform_verb_reachable),
    ]
    for name, fn in tests:
        fn()
        print(f"[ok ] {name}")
    # the disk test needs a tmp dir
    with tempfile.TemporaryDirectory() as d:
        test_state_roundtrips_through_disk(Path(d))
    print("[ok ] state_roundtrips_through_disk")
    print("\nSTEP 0 SMOKE: ALL OK")
