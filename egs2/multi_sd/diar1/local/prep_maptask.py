#!/usr/bin/env python3
"""HCRC Map Task: stereo dialogue recordings, word-level timed units.

Each dialogue is one 20 kHz stereo mix.wav; the two channels are averaged,
so it does not matter which channel holds the giver. Turns are the giver's
and follower's <tu> words (Data/timed-units/<dlg>.{g,f}.timed-units.xml,
NXT v2.1) joined across pauses of at most --merge_gap seconds.
"""

import argparse
import re
from pathlib import Path

from common import words_to_turns, write_jsonl

TU_RE = re.compile(r'<tu\b[^>]*\bstart="([\d.]+)"[^>]*\bend="([\d.]+)"')


def main():
    p = argparse.ArgumentParser()
    p.add_argument("root", help="maptask dir (signals/, annotations/)")
    p.add_argument("out")
    p.add_argument("--merge_gap", type=float, default=0.3)
    a = p.parse_args()
    root = Path(a.root)
    tu_dir = root / "annotations" / "maptaskv2-1" / "Data" / "timed-units"
    recs = []
    for wav in sorted((root / "signals" / "dialogues").glob("*.mix.wav")):
        dlg = wav.name.split(".")[0]
        words = []
        for agent in ("g", "f"):
            xml = tu_dir / f"{dlg}.{agent}.timed-units.xml"
            if xml.exists():
                words += [
                    (agent, float(s), float(e))
                    for s, e in TU_RE.findall(xml.read_text(errors="replace"))
                    if float(e) > float(s)
                ]
        if not words:
            print(f"skip {dlg}: no timed units")
            continue
        recs.append(
            {
                "rec": f"maptask-{dlg}",
                "sources": [{"path": str(wav), "channel": None}],
                "turns": [list(t) for t in words_to_turns(words, a.merge_gap)],
            }
        )
    print(f"{write_jsonl(a.out, recs)} recordings")


if __name__ == "__main__":
    main()
