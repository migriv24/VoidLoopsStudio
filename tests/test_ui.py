"""
Step-5 tests (extended for the v4 LiteGraph rebuild): the editor server is a
pure dispatcher client. Round-trips the page, the vendored LiteGraph files,
the state JSON (ports + kind specs + multi flags + sequencer notes + loop
ports), a dispatcher command, and a render, over real HTTP on an ephemeral
port.

Runnable via `pytest` or `python tests/test_ui.py`.
"""
from __future__ import annotations

import json
import threading
import urllib.request

from voidloops import VoidLoopsProject
from voidloops.ui import make_server

from test_patch import _first_sound


def _serve(proj):
    httpd = make_server(proj, port=0)
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    return httpd, f"http://127.0.0.1:{httpd.server_address[1]}"


def _get(url):
    with urllib.request.urlopen(url) as r:
        return r.read().decode()


def _post(url, obj):
    req = urllib.request.Request(url, data=json.dumps(obj).encode(), method="POST")
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read().decode())


def test_page_and_state():
    with VoidLoopsProject() as proj:
        _first_sound(proj)
        httpd, base = _serve(proj)
        try:
            page = _get(base + "/")
            assert "VOID LOOPS" in page and "canvas" in page
            state = json.loads(_get(base + "/state"))
            assert state["active"] == "first-sound"
            assert state["meta"]["bpm"] == 120.0
            names = {n["name"]: n for n in state["nodes"]}
            assert set(names) == {"clock1", "sequencer1", "osc1", "output1"}
            # ports ride along, typed — structural + the p:<field> param inlets
            assert names["osc1"]["inlets"] == [
                {"name": "notes", "signal": "events"},
                {"name": "p:tuning", "signal": "control", "param": True}]
            # the piano roll's data: notes inside the sequencer node
            assert [n["pitch"] for n in names["sequencer1"]["notes"]] == [60, 64, 67, 72]
            assert len(state["wires"]) == 3
        finally:
            httpd.shutdown()


def test_cmd_is_the_dispatcher():
    with VoidLoopsProject() as proj:
        _first_sound(proj)
        httpd, base = _serve(proj)
        try:
            res = _post(base + "/cmd", {"command": "ls --tag glyph:note"})
            assert res["ok"] and len(res["data"]) == 4
            res = _post(base + "/cmd", {"command": "bogus-verb"})
            assert res["ok"] is False                    # errors surface, don't crash
        finally:
            httpd.shutdown()


def test_loop_ports_in_state():
    with VoidLoopsProject() as proj:
        proj.new_pattern("melody")
        seq = proj.add_node("sequencer")
        osc = proj.add_node("osc")
        proj.wire(seq, osc)
        proj.new_pattern("main")
        proj.add_loop("melody")
        httpd, base = _serve(proj)
        try:
            state = json.loads(_get(base + "/state"))
            loop = next(n for n in state["nodes"] if n["kind"] == "loop")
            assert loop["inlets"] == [{"name": "sequencer1.clk", "signal": "clock"}]
            assert loop["outlets"] == [{"name": "osc1.out", "signal": "audio"}]
        finally:
            httpd.shutdown()


def test_litegraph_vendored():
    """v4: the page rides on a vendored LiteGraph.js — served locally, no CDN;
    kinds carry port specs so the page can register node types up front."""
    with VoidLoopsProject() as proj:
        _first_sound(proj)
        httpd, base = _serve(proj)
        try:
            page = _get(base + "/")
            assert "/vendor/litegraph.js" in page and "/vendor/litegraph.css" in page
            lib = _get(base + "/vendor/litegraph.js")
            assert "LiteGraph" in lib and len(lib) > 100_000
            css = _get(base + "/vendor/litegraph.css")
            assert "lgraphcanvas" in css or "litegraph" in css
            try:                                     # traversal / unknown → 404
                _get(base + "/vendor/../ui.py")
                assert False, "vendor route must whitelist"
            except Exception:
                pass
            state = json.loads(_get(base + "/state"))
            kinds = {k["kind"]: k for k in state["kinds"]}
            assert kinds["osc"]["inlets"] == [
                {"name": "notes", "signal": "events"},
                {"name": "p:tuning", "signal": "control", "param": True}]
            assert kinds["osc"]["outlets"] == [{"name": "out", "signal": "audio"}]
            # multi inlets flagged so the page can grow fan-in slots
            assert kinds["mix"]["inlets"][0]["multi"] is True
            arr = next(p for p in kinds["sequence"]["inlets"] if p["name"] == "arr")
            assert arr["multi"] is True
        finally:
            httpd.shutdown()


def test_render_endpoint():
    with VoidLoopsProject() as proj:
        _first_sound(proj)
        httpd, base = _serve(proj)
        try:
            res = _post(base + "/render", {})
            assert res["rendered"].endswith(".wav")
            from pathlib import Path
            assert Path(res["rendered"]).stat().st_size > 100_000
            # the leading-silence hint (jam feedback 2026-07-09): the melody
            # starts at tick 0, so the first sound is immediate
            assert res["first_sound_s"] == 0.0
        finally:
            httpd.shutdown()


def test_move_is_model_content():
    """Node positions are MODEL content (jam feedback #2/#6, 2026-07-09): /move
    batches x/y into ONE atomic op — a visible CLI action, persisted with the
    project, undoable like any edit."""
    with VoidLoopsProject() as proj:
        _first_sound(proj)
        httpd, base = _serve(proj)
        try:
            res = _post(base + "/move", {"moves": [
                {"node": "osc1", "x": 320, "y": 140},
                {"node": "output1", "x": 580, "y": 140}]})
            assert res["ok"]
            state = json.loads(_get(base + "/state"))
            names = {n["name"]: n for n in state["nodes"]}
            assert names["osc1"]["content"]["x"] == 320
            assert names["output1"]["content"]["y"] == 140
            # one batch = one undo frame: a single undo reverts BOTH moves
            _post(base + "/cmd", {"command": "undo"})
            state = json.loads(_get(base + "/state"))
            names = {n["name"]: n for n in state["nodes"]}
            assert "x" not in names["osc1"]["content"]
            assert "x" not in names["output1"]["content"]
        finally:
            httpd.shutdown()


if __name__ == "__main__":
    for name, fn in [
        ("page_and_state", test_page_and_state),
        ("cmd_is_the_dispatcher", test_cmd_is_the_dispatcher),
        ("loop_ports_in_state", test_loop_ports_in_state),
        ("litegraph_vendored", test_litegraph_vendored),
        ("render_endpoint", test_render_endpoint),
        ("move_is_model_content", test_move_is_model_content),
    ]:
        fn()
        print(f"[ok ] {name}")
    print("\nSTEP 5 UI: ALL OK")
