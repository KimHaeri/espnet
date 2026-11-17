#!/usr/bin/env python3
"""Real-TurnTurk (Turkish video calls): two speaker files mixed.

Each recording has one webm (opus) per participant (L/R) and frame-level
speech activity per person on a 62.5 ms grid (recNN__speech_activity.csv);
active frames are joined into turns.
"""

import argparse
import csv
from pathlib import Path

from common import normalize_turns, write_jsonl


def main():
    p = argparse.ArgumentParser()
    p.add_argument("root", help="Real-TurnTurk dir (rec01 ...)")
    p.add_argument("out")
    a = p.parse_args()
    recs = []
    for d in sorted(Path(a.root).glob("rec*")):
        webms = sorted(d.glob(f"{d.name}__[LR]_*.webm"))
        act = d / f"{d.name}__speech_activity.csv"
        if len(webms) != 2 or not act.exists():
            print(f"skip {d.name}: expected 2 webm + speech activity")
            continue
        rows = list(csv.DictReader(open(act)))
        ts = sorted({float(r["t_sec"]) for r in rows})
        hop = ts[1] - ts[0] if len(ts) > 1 else 0.0625
        turns = [
            [r["person"], float(r["t_sec"]), float(r["t_sec"]) + hop]
            for r in rows
            if r["speaking"] == "1"
        ]
        recs.append(
            {
                "rec": f"turnturk-{d.name}",
                "sources": [{"path": str(w), "channel": 0} for w in webms],
                "turns": [list(t) for t in normalize_turns(turns, gap=1e-6)],
            }
        )
    print(f"{write_jsonl(a.out, recs)} recordings")


if __name__ == "__main__":
    main()
