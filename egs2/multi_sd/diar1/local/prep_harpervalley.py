#!/usr/bin/env python3
"""Gridspace-Stanford Harper Valley bank calls (full GitHub release).

Each call has one 8 kHz wav per side (agent, caller); they are mixed into
one channel. Turns are the transcript segments (start_ms, duration_ms),
labelled by speaker_role.
"""

import argparse
import json
from pathlib import Path

from common import write_jsonl


def main():
    p = argparse.ArgumentParser()
    p.add_argument("root", help="gridspace-stanford-harper-valley dir")
    p.add_argument("out")
    a = p.parse_args()
    data = Path(a.root) / "data"
    recs = []
    for tr in sorted((data / "transcript").glob("*.json")):
        sid = tr.stem
        wavs = [data / "audio" / side / f"{sid}.wav" for side in ("agent", "caller")]
        if not all(w.exists() for w in wavs):
            print(f"skip {sid}: missing audio")
            continue
        turns = [
            [
                seg["speaker_role"],
                seg["start_ms"] / 1000,
                (seg["start_ms"] + seg["duration_ms"]) / 1000,
            ]
            for seg in json.loads(tr.read_text())
            if seg.get("duration_ms", 0) > 0
        ]
        recs.append(
            {
                "rec": f"hvb-{sid}",
                "sources": [{"path": str(w), "channel": 0} for w in wavs],
                "turns": turns,
            }
        )
    print(f"{write_jsonl(a.out, recs)} recordings")


if __name__ == "__main__":
    main()
