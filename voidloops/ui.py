"""
voidloops/ui.py — the node editor, v4: the canvas rebuilt on LiteGraph.js
(decided 2026-07-08, question #15 — "yes! litegraph!").

The architecture is unchanged and is the point: a stdlib HTTP server + ONE
self-contained page (`editor.html`), a **pure dispatcher client** — the page
never pokes the model, every mutation is a POST that becomes a visible CLI
action (`proj.echo`). LiteGraph.js (MIT, vendored in `voidloops/vendor/` —
no CDN, still fully offline) replaces only the hand-rolled canvas: it brings
multi-select, marquee, zoom/pan, native link dragging and a searchable
add-node box. The inspector (typed field editors), piano roll, library
panel and command footer carry over from v3.

Sync model: `/state` is the single source of truth; after every mutation the
page rebuilds the LiteGraph graph from it (server-rejected edits simply
vanish — auto-repair for free).

    GET  /            the editor        GET /state      the graph
    GET  /vendor/*    vendored libs     GET /vsts       discovered VST dlls
    GET  /library?q=  sample search     GET /wav        last render
    POST /...         mutations (see _post)
"""
from __future__ import annotations

import json
import tempfile
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from .model import LOOP_KIND, NODE_KIND, NOTE_KINDS
from .render import compile_render

_WAV = Path(tempfile.gettempdir()) / "voidloops-ui.wav"
_HERE = Path(__file__).parent
_VENDOR = {"litegraph.js": "application/javascript",
           "litegraph.css": "text/css"}

# per-kind field editors: how the inspector renders each content field.
# type: number | select | sample (library picker) | vst (plugin dropdown) |
#       patch (mantle dropdown) | text
_FIELD_UI: dict[str, dict[str, dict]] = {
    "clock": {"rate": {"type": "number", "hint": "ticks per second-ish; PPQN=1 beat"}},
    "sequencer": {"length": {"type": "number", "hint": "cycle ticks (0=auto)"},
                  "offset": {"type": "number", "hint": "entry tick"},
                  "repeat": {"type": "number", "hint": "cycles (0=fill window)"}},
    "sequence": {"length": {"type": "number", "hint": "cycle ticks (0=auto)"},
                 "offset": {"type": "number", "hint": "entry tick"},
                 "repeat": {"type": "number", "hint": "cycles (0=fill window)"},
                 "transpose": {"type": "number", "hint": "semitones"}},
    "midi": {"length": {"type": "number", "hint": "cycle ticks (0=auto)"},
             "offset": {"type": "number", "hint": "entry tick"},
             "repeat": {"type": "number", "hint": "cycles (0=fill window)"},
             "transpose": {"type": "number", "hint": "semitones"}},
    "osc": {"wave": {"type": "select", "options": ["saw", "sine", "square", "triangle"]},
            "tuning": {"type": "number", "min": -24, "max": 24, "hint": "semitones"}},
    "sampler": {"root": {"type": "number", "min": 0, "max": 127,
                         "hint": "sample's home MIDI pitch (60=C4)"}},
    "sample-in": {"path": {"type": "sample"},
                  "gain": {"type": "number", "min": 0, "max": 2, "step": 0.05}},
    "midi-in": {"path": {"type": "text", "hint": "path to a .mid file"}},
    "effect": {"type": {"type": "select",
                        "options": ["gain", "delay", "reverb", "limiter"]},
               "amount": {"type": "number", "min": 0, "max": 2, "step": 0.05,
                          "hint": "gain: xN · delay: sec · reverb: wet · limiter: ceil"},
               "feedback": {"type": "number", "min": 0, "max": 0.95, "step": 0.05,
                            "hint": "delay echoes"}},
    "vst-instrument": {"plugin": {"type": "vst"}, "preset": {"type": "text"}},
    "vst-effect": {"plugin": {"type": "vst"}, "preset": {"type": "text"}},
    "mix": {"gain": {"type": "number", "min": 0, "max": 2, "step": 0.05}},
    "output": {"gain": {"type": "number", "min": 0, "max": 2, "step": 0.05},
               "duration": {"type": "number", "hint": "render window ticks (0=auto)"}},
    "loop": {"patch": {"type": "patch"}},
    # utility (question #14: math/logic plumbing on `control` wires)
    "value": {"value": {"type": "number", "step": 0.1}},
    "math": {"op": {"type": "select",
                    "options": ["add", "sub", "mul", "div", "min", "max",
                                "pow", "mod"]},
             "a": {"type": "number", "step": 0.1, "hint": "used when inlet unwired"},
             "b": {"type": "number", "step": 0.1, "hint": "used when inlet unwired"}},
    "map": {"in_min": {"type": "number", "step": 0.1},
            "in_max": {"type": "number", "step": 0.1},
            "out_min": {"type": "number", "step": 0.1},
            "out_max": {"type": "number", "step": 0.1}},
    "compare": {"op": {"type": "select",
                       "options": ["lt", "le", "gt", "ge", "eq", "ne"]},
                "a": {"type": "number", "step": 0.1,
                      "hint": "used when inlet unwired"},
                "b": {"type": "number", "step": 0.1,
                      "hint": "used when inlet unwired"}},
    "time-of-day": {"override": {"type": "number", "min": 0, "max": 24,
                                 "step": 0.25,
                                 "hint": "pin the hour; empty = live clock"}},
}


def _vst_list() -> list[dict]:
    from .backend import scan_vsts
    return scan_vsts()


def _port(p) -> dict:
    """A port for the page; `multi`/`param` ride along only when true (lean +
    keeps the historical shape for the common case)."""
    d = {"name": p.name, "signal": p.signal}
    if p.multi:
        d["multi"] = True
    if p.name.startswith("p:"):
        d["param"] = True
    return d


def _inlets(spec) -> list[dict]:
    """A kind's inlets for the page: structural ports + its `p:<field>` param
    inlets (params as ports, question #14)."""
    return [_port(p) for p in spec.inlets + spec.param_ports()]


def _state(proj) -> dict:
    nodes = proj.nodes()
    for n in nodes:
        kind = n["kind"]
        if kind == LOOP_KIND:
            try:
                inlets, outlets = proj.loop_ports(n["name"])
                n["inlets"] = [_port(p) for p in inlets]
                n["outlets"] = [_port(p) for p in outlets]
            except ValueError as e:
                n["inlets"], n["outlets"], n["error"] = [], [], str(e)
        else:
            spec = NODE_KIND[kind]
            n["inlets"] = _inlets(spec)
            n["outlets"] = [_port(p) for p in spec.outlets]
        if kind in NOTE_KINDS:
            n["notes"] = proj.notes(node=n["name"])
    m = proj.meta
    return {"meta": {"ppqn": m.ppqn, "bpm": m.bpm,
                     "sig": f"{m.beats_per_bar}/{m.beat_unit}"},
            "mantles": proj.cmd("mantles")["data"] or [],
            "active": proj._active_mantle(),
            "kinds": [{"kind": k.glyph, "label": k.label, "category": k.category,
                       "editor": k.editor, "holiday": k.holiday,
                       "inlets": _inlets(k),
                       "outlets": [_port(p) for p in k.outlets]}
                      for k in NODE_KIND.values()],
            "field_ui": _FIELD_UI,
            "nodes": nodes, "wires": proj.wires()}


def _coerce(v):
    if isinstance(v, (int, float, bool)):
        return v
    s = str(v).strip()
    try:
        return int(s)
    except ValueError:
        try:
            return float(s)
        except ValueError:
            return s


# live plugin-editor windows, one per vst node (the VST-node-as-window face)
_VST_UI: dict[str, object] = {}


def _preset_dir(proj) -> Path:
    base = proj.state_path.parent / "presets" if proj.state_path else \
        Path(tempfile.gettempdir()) / "voidloops-presets"
    base.mkdir(parents=True, exist_ok=True)
    return base


def _vstui(proj, b: dict) -> dict:
    """POST /vstui {node, action: open|save|close}. `open` spawns the plugin with
    its own editor as a native window; `save` captures the knob state to a settings
    chunk next to the project and points the node's `preset` at it (renders load
    it); `close` tears the window down."""
    from .backend import _resolve_plugin
    from .vsthost import VstUiSession
    node, action = b["node"], b.get("action", "open")
    sess = _VST_UI.get(node)
    if action == "open":
        if sess is not None and getattr(sess, "alive", False):
            return {"ok": True, "lines": [f"{node}: plugin window already open"]}
        content = proj.cmd(f"get {node}")["data"] or {}
        plugin = (content.get("plugin") or "").strip()
        if not plugin:
            return {"ok": False, "lines": [f"{node}: set a plugin first"],
                    "data": None}
        _VST_UI[node] = VstUiSession(_resolve_plugin(plugin))
        return {"ok": True,
                "lines": [f"{node}: plugin window open — tweak away, then "
                          f"'apply' to bake the knobs into the node"]}
    if sess is None or not getattr(sess, "alive", False):
        _VST_UI.pop(node, None)
        return {"ok": False, "lines": [f"{node}: no plugin window open"],
                "data": None}
    if action == "save":
        path = _preset_dir(proj) / f"{node}.fxp"
        if not sess.save(path):
            return {"ok": False, "lines": [f"{node}: settings save failed"],
                    "data": None}
        proj._run_atomic([proj._set_cmd(node, "preset", str(path))])
        return {"ok": True,
                "lines": [f"{node}: knob state baked → {path.name} "
                          f"(renders now use it)"], "preset": str(path)}
    if action == "close":
        sess.close()
        _VST_UI.pop(node, None)
        return {"ok": True, "lines": [f"{node}: plugin window closed"]}
    return {"ok": False, "lines": [f"unknown vstui action {action!r}"], "data": None}


def make_server(proj, port: int = 0) -> HTTPServer:
    """The UI server (single-threaded on purpose: the C core sees one caller)."""

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def _send(self, obj, status=200, ctype="application/json"):
            body = obj if isinstance(obj, bytes) else \
                (obj.encode() if isinstance(obj, str) else json.dumps(obj).encode())
            try:
                self.send_response(status)
                self.send_header("Content-Type", ctype)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            except (ConnectionAbortedError, ConnectionResetError, BrokenPipeError):
                pass    # the browser aborted the fetch (audio src swap) — not an error

        def _body(self) -> dict:
            n = int(self.headers.get("Content-Length") or 0)
            return json.loads(self.rfile.read(n) or b"{}")

        def do_GET(self):
            url = urlparse(self.path)
            if url.path == "/":
                self._send((_HERE / "editor.html").read_bytes(),
                           ctype="text/html; charset=utf-8")
            elif url.path.startswith("/vendor/"):
                name = url.path[len("/vendor/"):]
                if name in _VENDOR and (_HERE / "vendor" / name).exists():
                    self._send((_HERE / "vendor" / name).read_bytes(),
                               ctype=_VENDOR[name])
                else:
                    self._send({"error": "not vendored"}, 404)
            elif url.path == "/state":
                self._send(_state(proj))
            elif url.path == "/library":
                from . import library
                q = (parse_qs(url.query).get("q") or [""])[0]
                self._send({"results": library.search(q, limit=80),
                            "categories": library.categories()})
            elif url.path == "/vsts":
                self._send({"plugins": _vst_list()})
            elif url.path == "/wav":
                if not _WAV.exists():
                    self._send({"error": "nothing rendered yet"}, 404)
                else:
                    self._send(_WAV.read_bytes(), ctype="audio/wav")
            else:
                self._send({"error": "not found"}, 404)

        def do_POST(self):
            try:
                self._send(self._post(urlparse(self.path).path, self._body()))
            except Exception as e:            # surface, don't die — it's a dev tool
                self._send({"ok": False, "lines": [f"{type(e).__name__}: {e}"],
                            "data": None}, 500)

        def _post(self, path: str, b: dict) -> dict:
            if path == "/cmd":
                return proj.cmd(b.get("command", ""))
            if path == "/use":
                return proj.cmd(f"use {b.get('mantle', '')}")
            if path == "/node":
                return {"ok": True, "name": proj.add_node(b["kind"])}
            if path == "/loop":
                return {"ok": True, "name": proj.add_loop(b["ref"])}
            if path == "/group":
                return {"ok": True,
                        "name": proj.group_loop(b["nodes"], b.get("ref") or None)}
            if path == "/wire":
                rel = proj.wire(b["src"], b["dst"],
                                src_port=b.get("src_port") or None,
                                dst_port=b.get("dst_port") or None)
                return {"ok": True, "relation": rel}
            if path == "/unwire":
                return proj.cmd(f"unlink {b['src']} {b['dst']}")
            if path == "/delete":
                return proj.cmd(f"rm {b['node']}")
            if path == "/set":
                return proj._run_atomic(
                    [proj._set_cmd(b["node"], b["field"], _coerce(b["value"]))])
            if path == "/move":
                # node positions are MODEL content (x/y), so layout is a visible
                # CLI action, persists in the project file, and undoes like any
                # other edit (the author's "log the UI itself" ask, 2026-07-09).
                # A batch of moves = one atomic op = one undo frame.
                cmds = []
                for m in b.get("moves") or []:
                    cmds += [proj._set_cmd(m["node"], "x", int(m["x"])),
                             proj._set_cmd(m["node"], "y", int(m["y"]))]
                return proj._run_atomic(cmds) if cmds else \
                    {"ok": True, "lines": [], "data": None}
            if path == "/note":
                name = proj.add_note(b.get("pitch", "C4"), int(b.get("start", 0)),
                                     int(b.get("length", 96)),
                                     int(b.get("velocity", 100)), node=b["node"])
                return {"ok": True, "name": name}
            if path == "/delnote":
                return proj.cmd(f"rm {b['name']}")
            if path == "/newpatch":
                return proj.new_pattern(b.get("name") or "patch")
            if path == "/instrument":
                return {"ok": True, "name": proj.add_instrument(b["ref"])}
            if path == "/meta":
                proj.set_meta(**{k: v for k, v in b.items()
                                 if k in ("bpm", "ppqn", "beats_per_bar", "beat_unit")})
                return {"ok": True}
            if path == "/vstui":
                return _vstui(proj, b)
            if path == "/render":
                from . import backend
                snap = compile_render(proj)
                backend.render_wav(snap, _WAV)
                # when the first audible note lands late, say so — a sequence
                # whose notes sit at tick 1344 plays 7s of silence first, which
                # reads as "the graph is broken" without this hint
                firsts = [n["start_s"] for v in snap["voices"]
                          for n in v["notes"] if n["length_s"] > 0]
                if any(v["kind"] == "sample-in" and (v.get("sample") or {}).get("path")
                       for v in snap["voices"]):
                    firsts.append(0.0)
                return {"ok": True, "rendered": str(_WAV),
                        "first_sound_s": min(firsts) if firsts else None}
            return {"ok": False, "lines": ["not found"], "data": None}

    return HTTPServer(("127.0.0.1", port), Handler)


def serve(proj, port: int = 7333, open_browser: bool = True) -> None:
    """Serve the editor for a project (blocking)."""
    httpd = make_server(proj, port)
    url = f"http://127.0.0.1:{httpd.server_address[1]}/"
    print(f"Void Loops Studio: {url}  (Ctrl+C to stop)")
    if open_browser:
        webbrowser.open(url)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        for sess in list(_VST_UI.values()):     # close any live plugin windows
            try:
                sess.close()
            except Exception:
                pass
        _VST_UI.clear()
        httpd.server_close()
