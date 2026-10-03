"""
voidloops/project.py — the project handle: Void Core wrapped for a DAW.

`VoidLoopsProject` is the single object the rest of Void Loops (CLI, UI, engine adapter)
talks to. It owns:

- a `VoidCore` manager (the in-memory rune/mantle model), and
- a `Dispatcher` over it (the drop-in superset that adds `scry`/`temper`/`reduce`/
  `materialize` to every C-core verb).

It also adds the one thing the binding leaves to the app: **state-file persistence**.
The C binding holds state in memory and round-trips it as a dict (`export_state` /
`VoidCore(state=...)`); persisting that to disk is application work (the adapter seam in
`okf/concepts/render-domain.md`). Audio I/O is a *separate* seam (the effect handler),
wired in a later build-order step — not here.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

from voidcore import Dispatcher, VoidCore

from . import model
from .model import (DAW_GLYPHS, LOOP_KIND, NODE_KIND, NOTE_KINDS, Port,
                    ProjectMeta, pitch as _pitch)
from .render import render_reduce_spec


class VoidLoopsProject:
    """One open Void Loops project = a Void Core manager + a transform dispatcher, with a
    JSON state file on the side."""

    def __init__(self, state_path: Optional[str | Path] = None, *,
                 state: Optional[dict] = None):
        self.state_path = Path(state_path) if state_path else None
        if state is None and self.state_path and self.state_path.exists():
            state = json.loads(self.state_path.read_text(encoding="utf-8"))
        # Seed config BEFORE constructing the manager: the C core hydrates state.config
        # at creation but exposes no `config` verb to write it afterwards (SPEC lists
        # one; the C core doesn't implement it yet — reported upstream 2026-07-06).
        state = self._with_seeded_config(state)
        self.vc = VoidCore(state=state)
        # Glyphs are host app config, NOT part of exported state — so a reopened project
        # must re-register the DAW glyphs every time (built-ins are always present).
        for glyph in DAW_GLYPHS:
            self.vc.register_glyph(glyph)
        # The superset dispatcher. Transformation rules (Temper/selectors/reduce) are
        # authored as data in state.config["transform"] and loaded here, so a reopened
        # project restores its own rules with no code. The reduce spec (node-glyph
        # signatures + ruleset) is seeded above — build-order step 3 compiles with it.
        self._d = Dispatcher(self.vc).load_from_config()

    @staticmethod
    def _with_seeded_config(state: Optional[dict]) -> dict:
        """Ensure project meta and the data-authored transform spec exist in
        `state.config` (existing values win — a saved project keeps its own)."""
        if state is None:
            tmp = VoidCore()
            state = tmp.export_state()
            tmp.close()
        cfg = state.setdefault("config", {})
        defaults = ProjectMeta()
        for key, val in {
            "ppqn": defaults.ppqn, "bpm": defaults.bpm,
            "beats_per_bar": defaults.beats_per_bar, "beat_unit": defaults.beat_unit,
        }.items():
            cfg.setdefault(key, val)
        cfg.setdefault("transform", {}).setdefault("reduce", render_reduce_spec())
        return state

    #: when True, every dispatcher command is echoed to stdout — the UI runs with
    #: this on, so every click in the editor is visible as its CLI action in the
    #: terminal (the author's observability ask, 2026-07-08)
    echo: bool = False

    # ── the one command surface (CLI, UI, scripts all call this) ──────────────────
    def cmd(self, command: str) -> dict[str, Any]:
        """Run one dispatcher command; return the `{ok, lines, data}` contract."""
        if self.echo and not command.startswith(("ls", "get ", "cat ", "where",
                                                 "mantles", "links", "config get")):
            print(f"[vls] {command}", flush=True)
        return self._d.dispatch(command)

    @property
    def dispatcher(self) -> Dispatcher:
        return self._d

    @property
    def version(self) -> str:
        return self.vc.version

    # ── project meta (ppqn / bpm / time signature), persisted in state.config ──────
    @property
    def meta(self) -> ProjectMeta:
        cfg = self.export().get("config") or {}
        return ProjectMeta(
            ppqn=int(cfg.get("ppqn", model.DEFAULT_PPQN)),
            bpm=float(cfg.get("bpm", model.DEFAULT_BPM)),
            beats_per_bar=int(cfg.get("beats_per_bar", model.DEFAULT_BEATS_PER_BAR)),
            beat_unit=int(cfg.get("beat_unit", model.DEFAULT_BEAT_UNIT)),
        )

    def set_meta(self, **kw) -> ProjectMeta:
        """Change project meta live (the BPM knob): `set_meta(bpm=140, ppqn=192, ...)`.
        Uses the core's `config` verb (v0.2.2+): config is session/host meta, so this
        pushes NO undo frame and leaves undo/redo history untouched — by contract
        (Void Core conformance case 09-config). Returns the updated meta."""
        allowed = {"ppqn", "bpm", "beats_per_bar", "beat_unit"}
        bad = set(kw) - allowed
        if bad:
            raise ValueError(f"unknown meta field(s) {sorted(bad)}; allowed: {sorted(allowed)}")
        for key, val in kw.items():
            res = self.cmd(f"config set {key} {val}")
            if not res["ok"]:
                raise RuntimeError(f"config set {key} failed (need Void Core >= 0.2.2): "
                                   f"{res['lines']}")
        return self.meta

    # ── the DAW model (build-order step 1) ─────────────────────────────────────────
    def new_pattern(self, name: str) -> dict:
        """Create a pattern (a mantle) and make it active."""
        return self.cmd(f"mantle new {name}")

    def add_note(self, pitch, start: int, length: int, velocity: int = 100, *,
                 pattern: Optional[str] = None, name: Optional[str] = None,
                 track: Optional[str] = None, node: Optional[str] = None) -> str:
        """Add a note-rune to a pattern. `pitch` accepts a MIDI int or a name ('C4').
        `start`/`length` are ticks. Returns the note's rune name. Created atomically
        (one undo frame) with integer-typed content via `setjson`.

        `node` places the note *inside* a sequencer node (step 2): the note is tagged
        `node:<seq>`, so the sequencer's contents are a tag-selection — first-class
        runes that Scry/Temper rules can still reach."""
        if pattern is not None:
            self.cmd(f"use {pattern}")
        if node is not None:
            kind = self._glyph_of(node)
            if kind not in NOTE_KINDS:
                raise ValueError(
                    f"notes live inside a {'/'.join(NOTE_KINDS)} node; "
                    f"{node!r} is a {kind!r}")
        p = _pitch(pitch)
        note_name = name or self._next_note_name()
        cmds = [
            f"rune new note {note_name}",
            f"setjson {note_name} pitch {int(p)}",
            f"setjson {note_name} start {int(start)}",
            f"setjson {note_name} length {int(length)}",
            f"setjson {note_name} velocity {int(velocity)}",
        ]
        tags = [f"+track:{track}" if track is not None else "",
                f"+node:{node}" if node is not None else ""]
        tags = [t for t in tags if t]
        if tags:
            cmds.append(f"tag {note_name} {' '.join(tags)}")
        res = self._run_atomic(cmds)
        if not res["ok"]:
            raise RuntimeError(f"add_note failed: {res['lines']}")
        return note_name

    def notes(self, pattern: Optional[str] = None, *,
              node: Optional[str] = None) -> list[dict]:
        """The note-runes of a pattern (active mantle by default), each as
        `{name, pitch, start, length, velocity}`, sorted by start then pitch.
        `node` narrows to the notes held by one sequencer node."""
        if pattern is not None:
            self.cmd(f"use {pattern}")
        expr = f'"glyph:note AND node:{node}"' if node is not None else "glyph:note"
        names = self.cmd(f"ls --tag {expr}")["data"] or []
        out = []
        for n in names:
            c = self.cmd(f"get {n}")["data"] or {}
            out.append({"name": n, "pitch": c.get("pitch"), "start": c.get("start"),
                        "length": c.get("length"), "velocity": c.get("velocity")})
        return sorted(out, key=lambda r: (r["start"] or 0, r["pitch"] or 0))

    # ── the node graph (build-order step 1, post-pivot) ───────────────────────────
    # The project is a signal-flow graph of coarse nodes (okf/concepts/node-graph.md).
    # A node is a rune whose glyph fixes its typed ports; a wire is a core `link` whose
    # relation encodes the ports it joins. Port-type compatibility is enforced here.
    def add_node(self, kind: str, name: Optional[str] = None, *,
                 patch: Optional[str] = None, **content) -> str:
        """Create a node of `kind` (a node glyph: clock/sequencer/osc/mix/output) in a
        patch (active mantle by default). Keyword args set the node's content fields
        (validated against the glyph). Returns the node's rune name."""
        if kind not in NODE_KIND:
            raise ValueError(f"unknown node kind {kind!r}; "
                             f"expected one of {sorted(NODE_KIND)}")
        if patch is not None:
            self.cmd(f"use {patch}")
        node_name = name or self._next_name(kind)
        spec = NODE_KIND[kind]
        cmds = [f"rune new {kind} {node_name}"]
        for field, value in content.items():
            if field not in spec.fields:
                raise ValueError(f"{kind!r} has no field {field!r}; "
                                 f"fields: {list(spec.fields)}")
            cmds.append(self._set_cmd(node_name, field, value))
        res = self._run_atomic(cmds)
        if not res["ok"]:
            raise RuntimeError(f"add_node failed: {res['lines']}")
        return node_name

    def wire(self, src: str, dst: str, *, src_port: Optional[str] = None,
             dst_port: Optional[str] = None, patch: Optional[str] = None) -> str:
        """Wire an outlet of `src` to an inlet of `dst`, type-checked. Ports default to
        the node's sole outlet/inlet when unambiguous. A single (non-`multi`) inlet
        rejects a second wire. Returns the relation label written to the core link."""
        if patch is not None:
            self.cmd(f"use {patch}")
        out = self._resolve_port(src, "out", src_port)
        inp = self._resolve_port(dst, "in", dst_port)
        if out.signal != inp.signal:
            raise TypeError(
                f"cannot wire {src}.{out.name} ({out.signal}) -> "
                f"{dst}.{inp.name} ({inp.signal}): signal types differ")
        if not inp.multi:
            occupied = [w for w in self.wires()
                        if w["to"] == dst and w["dst_port"] == inp.name]
            if occupied:
                raise ValueError(
                    f"{dst}.{inp.name} is a single inlet, already wired from "
                    f"{occupied[0]['from']}")
        relation = f"{out.signal}:{out.name}->{inp.name}"
        res = self.cmd(f"link {src} {dst} --relation {relation}")
        if not res["ok"]:
            raise RuntimeError(f"wire failed: {res['lines']}")
        return relation

    def nodes(self, patch: Optional[str] = None) -> list[dict]:
        """The node-runes of a patch (active mantle by default), each as
        `{name, kind, content, tags}`, sorted by name."""
        if patch is not None:
            self.cmd(f"use {patch}")
        out = []
        for kind in NODE_KIND:
            for n in self.cmd(f"ls --tag glyph:{kind}")["data"] or []:
                doc = self.cmd(f"cat {n}")["data"] or {}
                out.append({"name": n, "kind": kind,
                            "content": doc.get("content") or {},
                            "tags": doc.get("tags") or []})
        return sorted(out, key=lambda r: r["name"])

    def tag_node(self, node: str, *tags: str) -> None:
        """Tag a node (`tag_node('osc1', 'drums', 'wet')`) — the substrate the
        tag-routed FX rules select on (the bus replacement)."""
        joined = " ".join(f"+{t}" for t in tags)
        res = self.cmd(f"tag {node} {joined}")
        if not res["ok"]:
            raise RuntimeError(f"tag_node failed: {res['lines']}")

    def add_fx_rule(self, tag: str, **effect) -> list[dict]:
        """Route an effect to every voice whose generator/route carries `tag` —
        'everything tagged drums → reverb', authored as data in `config.fx_rules`
        (persists with the project). Returns the full rule list."""
        rules = json.loads((self.export().get("config") or {}).get("fx_rules") or "[]")
        rules.append({"tag": tag, **effect})
        blob = json.dumps(rules, separators=(",", ":"))
        res = self.cmd(f"config set fx_rules '{blob}'")   # single-quoted: the CLI
        # tokenizer preserves the JSON's double quotes inside (same as `batch`)
        if not res["ok"]:
            raise RuntimeError(f"add_fx_rule failed: {res['lines']}")
        return rules

    def wires(self, patch: Optional[str] = None) -> list[dict]:
        """The wires of a patch (active mantle by default): each
        `{from, to, src_port, dst_port, signal}`, parsed from the typed link relations.
        Non-wire links (relations not in `signal:a->b` form) are skipped."""
        if patch is not None:
            self.cmd(f"use {patch}")
        out = []
        for e in self.cmd("links")["data"] or []:
            signal, src_port, dst_port = self._parse_relation(e.get("relation", ""))
            if signal is None:
                continue
            out.append({"from": e["from"], "to": e["to"], "src_port": src_port,
                        "dst_port": dst_port, "signal": signal})
        return out

    def add_instrument(self, ref: str, name: Optional[str] = None, *,
                       root=60, patch: Optional[str] = None) -> str:
        """Drop a ready-to-play instrument from the sound library into the patch:
        a `sample-in` (the library sample) wired into a `sampler`. Returns the
        sampler's name — wire a sequencer into it and it plays. `ref` is a library
        ref like 'drums/bassdrum01' (see voidloops.library; sounds: LMMS)."""
        from . import library
        path = library.resolve(ref)
        if patch is not None:
            self.cmd(f"use {patch}")
        src = self.add_node("sample-in", path=str(path), gain=1)
        smp = self.add_node("sampler", name, root=int(root))
        self.wire(src, smp, dst_port="sample")
        return smp

    # ── the Loop (okf/concepts/loop.md): a mantle used as a single node ────────────
    def add_loop(self, ref: str, name: Optional[str] = None, *,
                 patch: Optional[str] = None) -> str:
        """Drop a Loop node into a patch: a node whose contents are the whole mantle
        `ref`. Its ports are the free (unwired) ports of that inner graph, qualified
        `<inner-node>.<port>` — net composition through boundary ports."""
        if ref not in (self.cmd("mantles")["data"] or []):
            raise ValueError(f"no such mantle to loop: {ref!r}")
        if patch is not None:
            self.cmd(f"use {patch}")
        if self._active_mantle() == ref:
            raise ValueError(f"a Loop cannot be dropped into its own mantle ({ref!r})")
        node_name = name or self._next_name(LOOP_KIND)
        res = self._run_atomic([f"rune new {LOOP_KIND} {node_name}",
                                f"set {node_name} patch {ref}"])
        if not res["ok"]:
            raise RuntimeError(f"add_loop failed: {res['lines']}")
        return node_name

    def group_loop(self, names: list[str], ref: Optional[str] = None) -> str:
        """Group nodes of the active patch into a Loop (the editor's Ctrl+G): move
        them (content, tags, notes, internal wires) into a NEW mantle `ref`, replace
        them here with one Loop node, and re-anchor every boundary wire onto the
        Loop's `<inner>.<port>` ports. Returns the Loop node's name.

        Limits (documented, not silent): boundary wires into `p:<field>` param
        inlets are dropped (Loop boundaries are structural — params are not
        exposed as Loop ports); the move spans several undo frames."""
        cur = self._active_mantle()
        if not cur:
            raise ValueError("no active patch to group from")
        names = list(dict.fromkeys(names))
        if not names:
            raise ValueError("group_loop needs at least one node")
        nodes = {n["name"]: n for n in self.nodes()}
        missing = [n for n in names if n not in nodes]
        if missing:
            raise ValueError(f"no such node(s): {missing}")
        ref = ref or self._next_mantle_name("part")
        if ref in (self.cmd("mantles")["data"] or []):
            raise ValueError(f"mantle {ref!r} already exists")
        sel = set(names)
        wires = self.wires()
        inner_w = [w for w in wires if w["from"] in sel and w["to"] in sel]
        in_w = [w for w in wires if w["from"] not in sel and w["to"] in sel]
        out_w = [w for w in wires if w["from"] in sel and w["to"] not in sel]
        dropped = [w for w in in_w if w["dst_port"].startswith("p:")]
        in_w = [w for w in in_w if not w["dst_port"].startswith("p:")]
        notes = {nm: self.notes(node=nm) for nm in names
                 if nodes[nm]["kind"] in NOTE_KINDS}
        # build the inner patch
        self.new_pattern(ref)
        for nm in names:
            n = nodes[nm]
            content = {k: v for k, v in (n["content"] or {}).items()
                       if v not in ("", None)}
            self.add_node(n["kind"], nm, **content)
            tags = [t for t in (n["tags"] or [])
                    if not t.startswith(("glyph:", "node:"))]
            if tags:
                self.tag_node(nm, *tags)
            for t in notes.get(nm, []):
                self.add_note(t["pitch"], t["start"], t["length"],
                              t["velocity"] or 100, node=nm)
        for w in inner_w:
            self.wire(w["from"], w["to"],
                      src_port=w["src_port"], dst_port=w["dst_port"])
        # back home: swap the originals for the Loop
        self.cmd(f"use {cur}")
        for nm in names:
            for t in notes.get(nm, []):
                self.cmd(f"rm {t['name']}")
            self.cmd(f"rm {nm}")
        loop_name = self.add_loop(ref)
        for w in in_w:
            self.wire(w["from"], loop_name, src_port=w["src_port"],
                      dst_port=f"{w['to']}.{w['dst_port']}")
        for w in out_w:
            self.wire(loop_name, w["to"],
                      src_port=f"{w['from']}.{w['src_port']}",
                      dst_port=w["dst_port"])
        if dropped:
            print(f"[vls] group_loop: dropped {len(dropped)} param wire(s) at the "
                  f"Loop boundary: " +
                  ", ".join(f"{w['from']}->{w['to']}.{w['dst_port']}"
                            for w in dropped))     # ascii: cp1252 consoles
        return loop_name

    def _next_mantle_name(self, prefix: str) -> str:
        existing = set(self.cmd("mantles")["data"] or [])
        i = 1
        while f"{prefix}{i}" in existing:
            i += 1
        return f"{prefix}{i}"

    def loop_ports(self, node: str) -> tuple[list[Port], list[Port]]:
        """A Loop node's (inlets, outlets): the free ports of its referenced mantle,
        as `Port`s named `<inner>.<port>` (signal/multi from the inner port)."""
        ref = (self.cmd(f"get {node}")["data"] or {}).get("patch")
        if not ref:
            raise ValueError(f"loop {node!r} has no `patch` reference set")
        return self._free_ports(ref)

    def _free_ports(self, mantle: str,
                    _seen: Optional[frozenset] = None) -> tuple[list[Port], list[Port]]:
        """The unwired ports of a mantle's node graph (a wired `multi` inlet counts as
        occupied — exposing partially-fed mixers is deferred). Nested Loops contribute
        their own free ports, doubly qualified."""
        seen = (_seen or frozenset()) | {mantle}
        nodes, wires = self._graph_of(mantle)
        taken_out = {(w["from"], w["src_port"]) for w in wires}
        taken_in = {(w["to"], w["dst_port"]) for w in wires}
        inlets, outlets = [], []
        for n in nodes:
            if n["kind"] == LOOP_KIND:
                ref = (n["content"] or {}).get("patch")
                if ref in seen:
                    raise ValueError(f"Loop cycle: mantle {ref!r} contains itself")
                sub_in, sub_out = self._free_ports(ref, seen)
                cand_in = [Port(f"{n['name']}.{p.name}", p.signal, p.multi)
                           for p in sub_in]
                cand_out = [Port(f"{n['name']}.{p.name}", p.signal, p.multi)
                            for p in sub_out]
            else:
                spec = NODE_KIND[n["kind"]]
                cand_in = [Port(f"{n['name']}.{p.name}", p.signal, p.multi)
                           for p in spec.inlets]
                cand_out = [Port(f"{n['name']}.{p.name}", p.signal, p.multi)
                            for p in spec.outlets]
            for p in cand_in:
                inner, port = p.name.split(".", 1)
                if (inner, port) not in taken_in:
                    inlets.append(p)
            for p in cand_out:
                inner, port = p.name.split(".", 1)
                if (inner, port) not in taken_out:
                    outlets.append(p)
        return inlets, outlets

    def _active_mantle(self) -> Optional[str]:
        res = self.cmd("where")
        if isinstance(res.get("data"), dict):           # core >= 0.2.2: structured
            return res["data"].get("mantle")
        for line in res["lines"]:                       # older cores: parse the text
            if line.startswith("mantle:"):
                name = line.split(":", 1)[1].strip()
                return None if name in ("", "(none)") else name
        return None

    def _graph_of(self, mantle: str) -> tuple[list[dict], list[dict]]:
        """A mantle's (nodes, wires), leaving the active mantle as it was."""
        prev = self._active_mantle()
        try:
            self.cmd(f"use {mantle}")
            return self.nodes(), self.wires()
        finally:
            if prev is not None:
                self.cmd(f"use {prev}")

    # ── node helpers ──────────────────────────────────────────────────────────────
    def _glyph_of(self, name: str) -> str:
        res = self.cmd(f"cat {name}")
        if not res["ok"] or not res["data"]:
            raise ValueError(f"no such rune: {name}")
        return res["data"].get("glyph")

    def _resolve_port(self, node: str, side: str, port_name: Optional[str]):
        """Look up a node's inlet/outlet Port. Defaults to the sole port on that side.
        A Loop node's ports are dynamic — its referenced mantle's free ports. Inlets
        include the kind's `p:<field>` param ports (params as ports, question #14);
        Loop boundaries stay structural (inner params are not exposed)."""
        kind = self._glyph_of(node)
        if kind not in NODE_KIND:
            raise ValueError(f"{node!r} (glyph {kind!r}) is not a node")
        if kind == LOOP_KIND:
            inlets, outlets = self.loop_ports(node)
            ports = tuple(outlets if side == "out" else inlets)
        elif side == "out":
            ports = NODE_KIND[kind].outlets
        else:
            spec = NODE_KIND[kind]
            ports = spec.inlets + spec.param_ports()
        by_name = {p.name: p for p in ports}
        word = "outlet" if side == "out" else "inlet"
        kwarg = "src_port" if side == "out" else "dst_port"
        if port_name is None:
            # default = the sole STRUCTURAL port; param inlets are named-only
            structural = [p for p in ports if not p.name.startswith("p:")]
            if len(structural) != 1:
                raise ValueError(f"{node} ({kind}) has {len(structural)} {word}s "
                                 f"{sorted(p.name for p in structural)}; "
                                 f"specify {kwarg}")
            return structural[0]
        if port_name not in by_name:
            raise ValueError(f"{node} ({kind}) has no {word} {port_name!r}; "
                             f"{word}s: {sorted(by_name)}")
        return by_name[port_name]

    @staticmethod
    def _parse_relation(rel: str) -> tuple:
        """`'audio:out->in'` → `('audio', 'out', 'in')`; `(None, None, None)` if not a
        wire relation."""
        if ":" not in rel or "->" not in rel:
            return (None, None, None)
        signal, rest = rel.split(":", 1)
        src_port, dst_port = rest.split("->", 1)
        return (signal, src_port, dst_port)

    @staticmethod
    def _set_cmd(name: str, field: str, value) -> str:
        """`setjson` for numbers/bools (typed), `set` for plain strings — quoted when
        they contain whitespace (paths!) so the dispatcher tokenizer keeps them whole."""
        if isinstance(value, (bool, int, float)):
            return f"setjson {name} {field} {json.dumps(value)}"
        s = str(value)
        if any(c.isspace() for c in s):
            return f'set {name} {field} "{s}"'
        return f"set {name} {field} {s}"

    def _next_name(self, prefix: str) -> str:
        existing = set(self.cmd("ls")["data"] or [])
        i = 1
        while f"{prefix}{i}" in existing:
            i += 1
        return f"{prefix}{i}"

    def _next_note_name(self) -> str:
        return self._next_name("n")

    def _run_atomic(self, cmds: list[str]) -> dict:
        """Apply several commands as one undo frame via the C core's `batch` (rolled back
        on any failure). One command runs directly."""
        cmds = [c for c in cmds if c]
        if not cmds:
            return {"ok": True, "lines": ["no change"], "data": None}
        if len(cmds) == 1:
            return self.cmd(cmds[0])
        arg = json.dumps(cmds).replace("'", "\\'")
        return self.cmd("batch '" + arg + "'")

    # ── the audio seam (build-order step 4): the host that computes ────────────────
    def attach_trivial_backend(self) -> None:
        """Bind the built-in Python synth behind Void Core's effect-handler seam — the
        ONLY door audio work goes through (okf/concepts/render-domain.md). After this:
        `deploy <path>` / `effect render <path>` bounce the active patch to WAV, and
        `preview` renders + plays it. The LMMS/VST backend later replaces this handler
        behind the same seam."""
        from . import backend
        from .render import compile_render

        def handler(op: str, args):
            if op in ("deploy", "render"):
                arglist = (args or {}).get("args") or []
                if not arglist:
                    return "render: missing output path"
                path = backend.render_wav(compile_render(self), arglist[0])
                return {"rendered": str(path)}
            if op == "preview":
                import tempfile
                out = Path(tempfile.gettempdir()) / "voidloops-preview.wav"
                backend.render_wav(compile_render(self), out)
                backend.play_wav(out)
                return {"rendered": str(out), "played": True}
            return None                        # save/build/…: nothing to do here

        self.vc.set_effect_handler(handler)

    # ── persistence (the app's job, not the core's) ───────────────────────────────
    def export(self) -> dict[str, Any]:
        return self.vc.export_state()

    def save(self, path: Optional[str | Path] = None) -> Path:
        """Write the project state to disk as JSON. Returns the path written."""
        target = Path(path) if path else self.state_path
        if target is None:
            raise ValueError("no state_path set; pass save(path=...)")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(self.export(), indent=2), encoding="utf-8")
        self.state_path = target
        return target

    # ── lifecycle ─────────────────────────────────────────────────────────────────
    def close(self) -> None:
        self.vc.close()

    def __enter__(self) -> "VoidLoopsProject":
        return self

    def __exit__(self, *exc) -> None:
        self.close()
