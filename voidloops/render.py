"""
voidloops/render.py — build-order step 3: compile the node graph into the render
snapshot (model → render-graph, off the audio thread).

The pipeline honors the layer split (okf/concepts/reducer.md) and the render-mantle
decision (okf/concepts/render-domain.md):

    node graph  --Reduce (data-authored rules)-->  RENDER MANTLE  --resolve-->  SNAPSHOT
    (owned)          topology normalization        (derived net)   (Scry-side)  (host-ready)

- **Reduce** runs Void Core's interaction-net rewriter with rules authored as data in
  `state.config.transform.reduce` (dev-answer 4). Today the ruleset is empty — a straight
  chain has no active pairs, so normal form == the same topology — but the pass runs for
  real: Loop-expansion rules land here (code-registered `expand`, since data-form expand
  is deferred upstream) without touching this pipeline.
- **The render mantle** is the reduced net — generated description-runes; the sample
  buffers themselves never appear here (the drift test).
- **Resolution** is read-side: walk the render mantle's topology from each output node
  back to its generators, attach each sequencer's note-runes and timing meta, and emit
  the immutable snapshot dict the audio backend pulls (okf/concepts/realtime-boundary.md).

Port indices: the core's `to_net` wants each wire as `"i:j"` port indices with linear
ports (one wire per port). A node's canonical port order is **outlets then inlets**
(index 0 = the principal port). A `multi` inlet gets a fresh index per wire (allocated
past the static ports). Fan-out from one outlet is not yet compiled (v1 doesn't need it).
"""
from __future__ import annotations

from typing import Any, Optional

from voidcore import reducer_from_spec, to_net, from_net

from .model import (COMBINE, GENERATOR, INPUT, LOOP_KIND, NODE_KIND, NOTE_KINDS,
                    TRANSFORM, ticks_to_seconds)


# ── port indexing (named ports ⇄ the reducer's linear "i:j" form) ──────────────────
def port_order(kind: str) -> list[str]:
    """A node kind's canonical port list: outlets, inlets, then the `p:<field>`
    param inlets (params as ports, question #14); index 0 = principal."""
    spec = NODE_KIND[kind]
    return ([p.name for p in spec.outlets] + [p.name for p in spec.inlets] +
            [p.name for p in spec.param_ports()])


def static_aux(kind: str) -> int:
    """The kind's aux-port count (total static ports - 1 principal), min 0."""
    return max(len(port_order(kind)) - 1, 0)


def render_reduce_spec() -> dict:
    """The data-authored reduce spec seeded into `state.config.transform.reduce`:
    the node glyphs' port signatures + the (currently empty) rewrite ruleset."""
    return {"signatures": {k: static_aux(k) for k in NODE_KIND}, "rules": []}


# ── the compile ────────────────────────────────────────────────────────────────────
def compile_render(proj, patch: Optional[str] = None) -> dict[str, Any]:
    """Compile a patch (active mantle by default) into the render snapshot. Pure with
    respect to the project: reads only, installs nothing, touches no sample data.
    Loop nodes are expanded first — net composition undone into one flat net."""
    if patch is not None:
        proj.cmd(f"use {patch}")
    nodes = {n["name"]: n for n in proj.nodes()}
    wires = proj.wires()
    seen = frozenset(m for m in [proj._active_mantle()] if m)
    nodes, wires, loop_notes = _expand_loops(proj, nodes, wires, seen)
    mantle = _index_form_mantle(nodes, wires)
    reducer, signatures = _reducer_from_config(proj, mantle)
    render = from_net(reducer.reduce(to_net(mantle, signatures)), mantle_name="render")
    nodes = _apply_params(nodes, wires)
    return _resolve_snapshot(proj, render, nodes, loop_notes)


def _expand_loops(proj, nodes: dict, wires: list[dict],
                  seen: frozenset) -> tuple[dict, list[dict], dict]:
    """Flatten every Loop node: splice the referenced mantle's (recursively expanded)
    graph in, names prefixed `<loop>/`, and re-anchor the Loop's boundary wires onto
    the inner free ports (`inner.port` → node `<loop>/inner`, port `port`). Returns
    (nodes, wires, notes) where notes maps each spliced-in sequencer to its note list
    (prefetched from its home mantle — the resolve stage can't reach it by tag).

    CONTRACT (agreed with Void Core, 2026-07-07): this function + tests/test_loop.py
    are the REFERENCE SEMANTICS for the core's future data-form `expand` / general-LHS
    rule design. Flag any behavioral refactor through the message channel first."""
    nodes, wires, loop_notes = dict(nodes), [dict(w) for w in wires], {}
    while True:
        loop = next((n for n in nodes.values() if n["kind"] == LOOP_KIND), None)
        if loop is None:
            return nodes, wires, loop_notes
        name, ref = loop["name"], (loop["content"] or {}).get("patch")
        if not ref:
            raise ValueError(f"loop {name!r} has no `patch` reference set")
        if ref in seen:
            raise ValueError(f"Loop cycle: mantle {ref!r} contains itself")
        inner_nodes, inner_wires = proj._graph_of(ref)
        inner_notes = _prefetch_notes(proj, ref, inner_nodes)
        inner = {n["name"]: n for n in inner_nodes}
        inner, inner_wires, sub_notes = _expand_loops(proj, inner, inner_wires,
                                                      seen | {ref})
        inner_notes.update(sub_notes)
        pf = f"{name}/"
        del nodes[name]
        for iname, n in inner.items():
            nodes[pf + iname] = {**n, "name": pf + iname}
        for w in inner_wires:
            wires.append({**w, "from": pf + w["from"], "to": pf + w["to"]})
        loop_notes.update({pf + k: v for k, v in inner_notes.items()})
        for w in wires:
            if w["from"] == name:
                w["from"], w["src_port"] = _reanchor(pf, w["src_port"])
            if w["to"] == name:
                w["to"], w["dst_port"] = _reanchor(pf, w["dst_port"])


def _reanchor(prefix: str, qualified: str) -> tuple[str, str]:
    """A Loop boundary port `a.b(.c…)` → (node `<prefix>a(/b…)`, port = last part)."""
    parts = qualified.split(".")
    return prefix + "/".join(parts[:-1]), parts[-1]


def _prefetch_notes(proj, mantle: str, inner_nodes: list[dict]) -> dict:
    """Each inner sequencer's notes, read from its home mantle (active restored)."""
    prev = proj._active_mantle()
    try:
        proj.cmd(f"use {mantle}")
        return {n["name"]: proj.notes(node=n["name"])
                for n in inner_nodes if n["kind"] in NOTE_KINDS}
    finally:
        if prev is not None:
            proj.cmd(f"use {prev}")


# Synthetic port-index bands: the net needs LINEAR ports (one wire each), so extra
# wires on the same named port get fresh indices. The band encodes the SIDE, because
# direction must survive the reduce round-trip (from_net keeps only name + index):
# outlet fan-out allocates in [1000, 2000), multi-inlets in [2000, 3000). When the
# core grows directed-edge metadata, these bands retire.
_OUT_BAND, _IN_BAND = 1000, 2000


def _index_form_mantle(nodes: dict, wires: list[dict]) -> dict:
    """The node graph as a reducer-ready mantle dict: node runes + `"i:j"` edges.
    Notes are content, not topology — they stay behind for the resolve stage.
    Fan-out (one outlet, many wires) and `multi` inlets both allocate per-wire
    synthetic indices, so any wiring the editor allows is compilable."""
    runes = [{"spirit": {"id": f"rune_{n['name']}", "name": n["name"]},
              "glyph": n["kind"], "content": dict(n["content"])}
             for n in nodes.values()]
    edges, used = [], set()
    nxt = {}                                   # (node, port, band) -> next synthetic
    for w in wires:
        src_kind, dst_kind = nodes[w["from"]]["kind"], nodes[w["to"]]["kind"]
        i = _port_index(src_kind, w["src_port"], w["from"], used, nxt, _OUT_BAND)
        j = _port_index(dst_kind, w["dst_port"], w["to"], used, nxt, _IN_BAND)
        used.add((w["from"], i))
        used.add((w["to"], j))
        edges.append({"from": w["from"], "to": w["to"], "relation": f"{i}:{j}"})
    return {"runes": runes, "layout": {"edges": edges}}


def _port_index(kind: str, port: str, node: str, used: set, nxt: dict,
                band: int) -> int:
    """A wire-end's port index: the static index if free, else a fresh synthetic in
    the side's band."""
    j = port_order(kind).index(port)
    if (node, j) not in used:
        return j
    key = (node, port, band)
    nxt.setdefault(key, band)
    j = nxt[key]
    nxt[key] += 1
    return j


def _reducer_from_config(proj, mantle: dict):
    """The data-authored reducer (`state.config.transform.reduce`), signatures widened
    to any per-wire indices `multi` inlets allocated on this particular graph."""
    cfg = (proj.export().get("config") or {}).get("transform") or {}
    spec = cfg.get("reduce") or render_reduce_spec()
    reducer, signatures = reducer_from_spec(spec)
    for e in mantle["layout"]["edges"]:
        for name, idx in ((e["from"], int(e["relation"].split(":")[0])),
                          (e["to"], int(e["relation"].split(":")[1]))):
            glyph = next(r["glyph"] for r in mantle["runes"]
                         if r["spirit"]["name"] == name)
            signatures[glyph] = max(signatures.get(glyph, 0), idx)
    return reducer, signatures


# ── resolve: render mantle + owned content → the snapshot (the Scry side) ──────────
def _int(v) -> int:
    """Content fields arrive as ints (setjson) or strings (glyph defaults) — coerce."""
    try:
        return int(v)
    except (TypeError, ValueError):
        return 0


def _expand_sequence(notes: list[dict], seq_content: dict,
                     duration_ticks: int) -> list[dict]:
    """A sequencer's notes, looped: one cycle is `length` ticks (default: the notes'
    span), entering at `offset`, playing `repeat` cycles (default: fill the render
    window; 1 when there is no window). Looping is the default posture — see
    okf/concepts/time-without-timeline.md."""
    if not notes:
        return notes
    length = _int(seq_content.get("length")) or \
        max(n["start"] + max(n["length"], 0) for n in notes)
    offset = _int(seq_content.get("offset"))
    repeat = _int(seq_content.get("repeat"))
    if repeat <= 0:
        if duration_ticks and length:
            repeat = max(-(-(duration_ticks - offset) // length), 1)
        else:
            repeat = 1
    out = []
    for k in range(repeat):
        base = offset + k * length
        for n in notes:
            m = dict(n)
            m["start"] = n["start"] + base
            if duration_ticks and m["start"] >= duration_ticks:
                continue
            out.append(m)
    return out


# ── the control graph (params as ports, question #14) ─────────────────────────────
# Utility/`control` nodes are pure value plumbing: evaluated ONCE PER RENDER at
# compile time (Scry-side, before voices are built). A wire into a `p:<field>` inlet
# overrides that field's content value. Per-block automation (control values varying
# *during* playback) arrives with streaming playback — roadmap post-prototype item 3.
def _float(v) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


_MATH_OPS = {
    "add": lambda a, b: a + b, "sub": lambda a, b: a - b,
    "mul": lambda a, b: a * b, "div": lambda a, b: a / b if b else 0.0,
    "min": min, "max": max,
    "pow": lambda a, b: a ** b, "mod": lambda a, b: a % b if b else 0.0,
}
_CMP_OPS = {
    "lt": lambda a, b: a < b, "le": lambda a, b: a <= b,
    "gt": lambda a, b: a > b, "ge": lambda a, b: a >= b,
    "eq": lambda a, b: a == b, "ne": lambda a, b: a != b,
}


def _eval_control(node: str, nodes: dict, ctrl_in: dict,
                  _seen: frozenset = frozenset()) -> float:
    """A control node's output value, evaluated recursively. `ctrl_in` maps
    (node, inlet) -> source node for every control wire. Unwired math/compare
    inlets fall back to the node's own a/b content (inline constants)."""
    if node in _seen:
        raise ValueError(f"control cycle through {node!r}")
    seen = _seen | {node}
    kind = nodes[node]["kind"]
    content = nodes[node]["content"] or {}

    def inlet(name: str, default: float) -> float:
        src = ctrl_in.get((node, name))
        return _eval_control(src, nodes, ctrl_in, seen) if src else default

    if kind == "value":
        return _float(content.get("value"))
    if kind == "time-of-day":
        ov = content.get("override")
        if ov is not None and str(ov).strip() != "":
            return _float(ov)
        import datetime
        t = datetime.datetime.now()
        return t.hour + t.minute / 60.0 + t.second / 3600.0
    if kind == "math":
        op = _MATH_OPS.get(str(content.get("op") or "add"), _MATH_OPS["add"])
        return float(op(inlet("a", _float(content.get("a"))),
                        inlet("b", _float(content.get("b")))))
    if kind == "compare":
        op = _CMP_OPS.get(str(content.get("op") or "gt"), _CMP_OPS["gt"])
        return 1.0 if op(inlet("a", _float(content.get("a"))),
                         inlet("b", _float(content.get("b")))) else 0.0
    if kind == "map":
        x = inlet("in", 0.0)
        i0, i1 = _float(content.get("in_min")), _float(content.get("in_max"))
        o0, o1 = _float(content.get("out_min")), _float(content.get("out_max"))
        t = 0.0 if i1 == i0 else (x - i0) / (i1 - i0)
        t = min(max(t, 0.0), 1.0)
        return o0 + t * (o1 - o0)
    raise ValueError(f"{node!r} ({kind}) is not a control source")


def _apply_params(nodes: dict, wires: list[dict]) -> dict:
    """Overlay the control graph onto node content: every wire into a `p:<field>`
    inlet replaces that field's value with the evaluated control signal. Returns a
    new nodes dict (content copied where overridden); values are floats — downstream
    coercion (`_int`, the backend's floats) handles each field's own type."""
    ctrl_in = {(w["to"], w["dst_port"]): w["from"]
               for w in wires if w.get("signal") == "control"}
    out = dict(nodes)
    for (dst, port), src in ctrl_in.items():
        if not port.startswith("p:"):
            continue                          # a utility node's own inlet, not a param
        field = port[2:]
        val = _eval_control(src, nodes, ctrl_in)
        n = out[dst]
        out[dst] = {**n, "content": {**(n["content"] or {}), field: val}}
    return out


def _fx_rules(proj) -> list[dict]:
    """Tag-routed effect rules, authored as data in `config.fx_rules` (a JSON string —
    the bus replacement: 'everything tagged X gets this effect')."""
    import json
    raw = (proj.export().get("config") or {}).get("fx_rules") or "[]"
    try:
        rules = json.loads(raw)
        return rules if isinstance(rules, list) else []
    except (TypeError, ValueError):
        return []


def _resolve_snapshot(proj, render: dict, nodes: dict,
                      loop_notes: Optional[dict] = None) -> dict[str, Any]:
    """Walk the render mantle from each output node back to its generators (pull
    direction), attaching sequencer notes and timing meta. Deterministic ordering.
    `loop_notes` carries the notes of sequencers spliced in by Loop expansion."""
    loop_notes = loop_notes or {}
    kinds = {r["spirit"]["name"]: r["glyph"] for r in render["runes"]}
    inflows = _directed_inflows(render, kinds)
    meta = proj.meta
    outputs = sorted(n for n, k in kinds.items() if k == "output")
    duration_ticks = max((_int((nodes[o]["content"] or {}).get("duration"))
                          for o in outputs), default=0)
    fx_rules = _fx_rules(proj)
    voices = []
    for out in outputs:
        for gen, route in _pull_generators(out, inflows, kinds):
            seq = next((s for s in inflows.get(gen, [])
                        if kinds[s] in _EVENT_KINDS), None)
            clk = next((c for c in inflows.get(seq, []) if kinds[c] == "clock"),
                       None) if seq else None
            notes = _resolve_events(proj, seq, nodes, kinds, inflows, loop_notes,
                                    meta, duration_ticks) if seq else []
            for n in notes:
                n["start_s"] = ticks_to_seconds(n["start"], meta.ppqn, meta.bpm)
                n["length_s"] = ticks_to_seconds(n["length"], meta.ppqn, meta.bpm)
            # a sampler's sample source (its `sample` inlet); a bare sample-in used as
            # a generator is its own source
            sample = next((s for s in inflows.get(gen, [])
                           if kinds[s] == "sample-in"), None)
            if sample is None and kinds[gen] == "sample-in":
                sample = gen
            effects = [{"name": r, "kind": kinds[r], **nodes[r]["content"]}
                       for r in route
                       if NODE_KIND[kinds[r]].category == TRANSFORM]
            # tag-routed FX (the bus replacement): a rule's effect lands on every
            # voice whose generator or route carries the tag
            voice_tags = set()
            for r in [gen] + route:
                voice_tags.update(nodes.get(r, {}).get("tags") or [])
            for rule in fx_rules:
                if rule.get("tag") in voice_tags:
                    fx = {k: v for k, v in rule.items() if k != "tag"}
                    effects.append({"name": f"fx:{rule['tag']}", "kind": "effect",
                                    **fx})
            voices.append({
                "generator": gen, "kind": kinds[gen],
                "content": nodes[gen]["content"],
                "sequencer": ({"name": seq, **nodes[seq]["content"]} if seq else None),
                "clock": ({"name": clk, **nodes[clk]["content"]} if clk else None),
                "sample": ({"name": sample, **nodes[sample]["content"]}
                           if sample else None),
                "effects": effects,
                "notes": notes, "route": route,
            })
    voices.sort(key=lambda v: v["generator"])
    return {
        "meta": {"ppqn": meta.ppqn, "bpm": meta.bpm,
                 "beats_per_bar": meta.beats_per_bar, "beat_unit": meta.beat_unit,
                 "duration_ticks": duration_ticks,
                 "duration_s": ticks_to_seconds(duration_ticks, meta.ppqn, meta.bpm)
                 if duration_ticks else 0.0},
        "voices": voices,
        "outputs": [{"name": o, **nodes[o]["content"]} for o in outputs],
    }


def _midi_notes(node: dict, meta) -> list[dict]:
    """A midi-in node's notes, read from its file at the project's PPQN."""
    from .midi import read_midi_notes
    path = (node.get("content") or {}).get("path")
    if not path:
        return []
    return read_midi_notes(path, ppqn=meta.ppqn)


_EVENT_KINDS = NOTE_KINDS + ("midi-in",)


def _resolve_events(proj, node: str, nodes: dict, kinds: dict, inflows: dict,
                    loop_notes: dict, meta, window: int,
                    _seen: frozenset = frozenset()) -> list[dict]:
    """A node's outgoing notes, resolved recursively. A `sequence` (and the `midi`
    node — same semantics, its own piano-roll face) merges its own inline notes
    with every `arr` source (midi-in / sequencer / other sequences — composition),
    then applies its length/offset/repeat/transpose. Children expand one pass
    (window=0); only the top of the chain fills the render window."""
    if node in _seen:
        raise ValueError(f"event cycle through {node!r}")
    seen = _seen | {node}
    kind = kinds[node]
    content = nodes[node]["content"] or {}
    if kind == "midi-in":
        return _midi_notes(nodes[node], meta)
    if kind == "sequencer":
        base = loop_notes.get(node)
        base = [dict(n) for n in base] if base is not None else proj.notes(node=node)
        return _expand_sequence(base, content, window)
    if kind in ("sequence", "midi"):
        base = loop_notes.get(node)
        merged = [dict(n) for n in base] if base is not None else proj.notes(node=node)
        for src in inflows.get(node, []):
            if kinds[src] in _EVENT_KINDS:
                merged.extend(_resolve_events(proj, src, nodes, kinds, inflows,
                                              loop_notes, meta, 0, seen))
        merged.sort(key=lambda n: (n["start"], n["pitch"]))
        merged = _expand_sequence(merged, content, window)
        t = _int(content.get("transpose"))
        if t:
            for n in merged:
                n["pitch"] += t
        return merged
    return []


def _is_outlet_index(kind: str, idx: int) -> bool:
    return idx < len(NODE_KIND[kind].outlets) or _OUT_BAND <= idx < _IN_BAND


def _directed_inflows(render: dict, kinds: dict) -> dict[str, list[str]]:
    """Recover direction from the render mantle's undirected `"i:j"` edges: the outlet
    side (static outlet index, or the outlet synthetic band) is the source."""
    inflows: dict[str, list[str]] = {}
    for e in render["layout"]["edges"]:
        i, j = (int(x) for x in e["relation"].split(":"))
        a, b = e["from"], e["to"]
        src, dst = (a, b) if _is_outlet_index(kinds[a], i) else (b, a)
        inflows.setdefault(dst, []).append(src)
    for v in inflows.values():
        v.sort()
    return inflows


def _pull_generators(sink: str, inflows: dict, kinds: dict,
                     route: Optional[list] = None) -> list[tuple[str, list[str]]]:
    """From a sink, follow audio inflows back to voice sources; each hit returns
    (generator, route generator→…→output). Category-driven (the taxonomy at work):
    GENERATOR kinds and audio-producing INPUT kinds (a bare sample-in) are voices;
    COMBINE/TRANSFORM kinds are pass-through hops collected into the route."""
    route = [sink] + (route or [])
    found = []
    for src in inflows.get(sink, []):
        cat = NODE_KIND[kinds[src]].category
        if cat == GENERATOR or (cat == INPUT and kinds[src] == "sample-in"):
            found.append((src, [src] + route))
        elif cat in (COMBINE, TRANSFORM):
            found.extend(_pull_generators(src, inflows, kinds, route))
    return found
