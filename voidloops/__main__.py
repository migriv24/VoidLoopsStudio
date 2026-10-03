"""
`python -m voidloops` — a tiny live demo of the project skeleton (build-order step 0).

Not the real CLI yet (that arrives with the model, step 1). This just proves the
foundation is wired: open a project, run a few dispatcher commands through the superset,
and round-trip the state through disk.
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

from voidloops import VoidLoopsProject, pitch_name


def main() -> None:
    with VoidLoopsProject() as proj:
        m = proj.meta
        print(f"Void Loops Studio (step 1) - on Void Core {proj.version}")
        print(f"project: {m.ppqn} PPQN, {m.bpm:g} BPM, {m.beats_per_bar}/{m.beat_unit}\n")

        # build a one-bar C-major arpeggio: four quarter notes, lead track
        proj.new_pattern("c-major-arp")
        for i, note in enumerate(["C4", "E4", "G4", "C5"]):
            proj.add_note(note, start=i * m.ppqn, length=m.ppqn, velocity=90, track="lead")

        print("pattern 'c-major-arp':")
        for n in proj.notes():
            beat = n["start"] / m.ppqn
            secs = n["start"] / m.ppqn * 60 / m.bpm
            print(f"  {n['name']:>3}  {pitch_name(n['pitch']):<3} "
                  f"start={n['start']:>3}t (beat {beat:g}, {secs:.2f}s)  "
                  f"len={n['length']}t  vel={n['velocity']}")

        # build the first-sound topology as a node graph: clock → sequencer → osc → output,
        # with the melody held INSIDE the sequencer node (step 2)
        proj.new_pattern("first-sound")
        clk = proj.add_node("clock", rate=m.ppqn)
        seq = proj.add_node("sequencer", length=4 * m.ppqn)
        osc = proj.add_node("osc", wave="saw", tuning=0)
        outn = proj.add_node("output", gain=1)
        proj.wire(clk, seq)          # clock  → sequencer   (clock)
        proj.wire(seq, osc)          # events → oscillator  (events)
        proj.wire(osc, outn)         # audio  → output      (audio)
        for i, note in enumerate(["C4", "E4", "G4", "C5"]):
            proj.add_note(note, start=i * m.ppqn, length=m.ppqn, velocity=90, node=seq)

        print("\npatch 'first-sound' (node graph):")
        for n in proj.nodes():
            print(f"  {n['name']:<10} {n['kind']:<9} {n['content']}")
        for w in proj.wires():
            print(f"  {w['from']}.{w['src_port']} --{w['signal']}--> "
                  f"{w['to']}.{w['dst_port']}")
        held = [pitch_name(n["pitch"]) for n in proj.notes(node=seq)]
        print(f"  {seq} holds: {held}")

        v = proj.cmd("validate")
        print(f"\nvalidate: {'ok' if v['ok'] else 'FAIL'} - {'; '.join(v['lines'])}")

        # FIRST SOUND (step 4): compile → render mantle → snapshot → WAV, across the seam
        proj.attach_trivial_backend()
        wav = Path(tempfile.gettempdir()) / "voidloops-first-sound.wav"
        res = proj.cmd(f"deploy {wav}")
        print(f"deploy:   {'ok' if res['ok'] else 'FAIL'} - {res['data']}")
        print("          (run `python -m voidloops --play` to hear it)")

        out = Path(tempfile.gettempdir()) / "voidloops-demo.vlp.json"
        proj.save(out)
        print(f"saved -> {out}")

    # reopen from disk and confirm the pattern survived the round-trip
    with VoidLoopsProject(out) as reopened:
        reopened.cmd("use c-major-arp")
        pitches = [pitch_name(n["pitch"]) for n in reopened.notes()]
        print(f"reopened -> {pitches}")

    if "--play" in sys.argv:
        from voidloops.backend import play_wav
        print("playing...")
        play_wav(Path(tempfile.gettempdir()) / "voidloops-first-sound.wav")

    if "--ui" in sys.argv:
        ui()


def ui() -> None:
    """Open the editor on the user's own project (the desktop icon's path):
    ~/Documents/VoidLoopsProjects/default.vlp.json, created with a starter patch
    the first time."""
    from voidloops.ui import serve

    home = Path.home() / "Documents" / "VoidLoopsProjects"
    path = home / "default.vlp.json"
    fresh = not path.exists()
    with VoidLoopsProject(path) as proj:
        if fresh:
            m = proj.meta
            proj.new_pattern("main")
            clk = proj.add_node("clock", rate=m.ppqn)
            seq = proj.add_node("sequence", length=4 * m.ppqn)
            osc = proj.add_node("osc", wave="saw", tuning=0)
            outn = proj.add_node("output", gain=1)
            proj.wire(clk, seq, dst_port="clk")   # sequence also has an `arr` inlet
            proj.wire(seq, osc)
            proj.wire(osc, outn)
            for i, note in enumerate(["C4", "E4", "G4", "C5"]):
                proj.add_note(note, start=i * m.ppqn, length=m.ppqn,
                              velocity=90, node=seq)
            proj.save()
            print(f"created starter project: {path}")
        else:
            proj.cmd("use main")
        proj.attach_trivial_backend()
        proj.echo = True          # every editor click shows as CLI in this terminal

        # persist on exit too — the icon's project survives the session
        try:
            serve(proj)
        finally:
            proj.save()
            print(f"saved: {path}")


if __name__ == "__main__":
    if "--ui" in sys.argv and len(sys.argv) == 2:
        ui()                      # icon path: straight to the editor, no demo
    else:
        main()
