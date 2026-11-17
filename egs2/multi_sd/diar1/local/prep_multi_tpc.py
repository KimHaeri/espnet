#!/usr/bin/env python3
"""Multi-TPC (three-party conversations): three participant files mixed.

Each participant of a session has their own recording (48 kHz stereo,
channels averaged) and a word file; the three recordings are mixed and each
participant's words are joined into turns. The recordings are assumed to
share one timeline (the corpus's per-session audio/gaze table is indexed by
a single clock); data_stats.py reports the overlap ratio to check this.
"""

import argparse
import csv
from pathlib import Path

from common import hms_to_sec, words_to_turns, write_jsonl


def main():
    p = argparse.ArgumentParser()
    p.add_argument("root", help="multi_tpc/Data")
    p.add_argument("out")
    p.add_argument("--merge_gap", type=float, default=0.3)
    a = p.parse_args()
    root = Path(a.root)
    sessions = {}
    for wav in sorted((root / "Audio").glob("*/Session_*_PC_*_audio.wav")):
        sess = wav.name.split("_PC_")[0]
        pc = wav.name.split("_PC_")[1].split("_")[0]
        sessions.setdefault((wav.parent.name, sess), []).append((pc, wav))
    recs = []
    for (date, sess), parts in sorted(sessions.items()):
        sources, words = [], []
        for pc, wav in sorted(parts):
            wf = root / "Word" / date / f"{sess}_PC_{pc}_words.csv"
            if not wf.exists():
                continue
            sources.append({"path": str(wav), "channel": None})
            with open(wf) as f:
                for row in csv.DictReader(f):
                    if not row.get("start") or not row.get("end"):
                        continue  # words without timing
                    s, e = hms_to_sec(row["start"]), hms_to_sec(row["end"])
                    if e > s:
                        words.append((f"PC{pc}", s, e))
        if len(sources) < 2:
            print(f"skip {date} {sess}: fewer than 2 participants with words")
            continue
        recs.append(
            {
                "rec": f"multitpc-{date}-{sess}",
                "sources": sources,
                "turns": [list(t) for t in words_to_turns(words, a.merge_gap)],
            }
        )
    print(f"{write_jsonl(a.out, recs)} recordings")


if __name__ == "__main__":
    main()
