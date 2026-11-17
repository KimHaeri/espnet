#!/usr/bin/env python3
"""MSP-Conversation (podcasts), Development and Test partitions only.

Not used for training (user decision). Speaker numbers in the diarization
JSON are only consistent within a "part", and turn times are relative to
the part, so every part is its own recording: it is cut out of the
conversation wav at part_start - conversation_start (both in podcast time,
Time_Labels/). Licensed internally (research-only agreement).
"""

import argparse
import json
from pathlib import Path

from common import write_jsonl


def read_times(path: Path):
    out = {}
    for line in path.read_text().splitlines():
        if line.strip():
            name, s, e = line.strip().split(";")
            out[name] = (float(s), float(e))
    return out


def main():
    p = argparse.ArgumentParser()
    p.add_argument("root")
    p.add_argument("split", choices=["Development", "Test"])
    p.add_argument("out")
    a = p.parse_args()
    root = Path(a.root)
    convs = {
        c
        for c, s in (
            line.strip().split(";")
            for line in (root / "partitions.txt").read_text().splitlines()
            if line.strip()
        )
        if s == a.split
    }
    conv_t = read_times(root / "Time_Labels" / "conversations.txt")
    part_t = read_times(root / "Time_Labels" / "conversation_parts.txt")
    recs = []
    for part, (ps, pe) in sorted(part_t.items()):
        conv = part.rsplit("_", 1)[0]
        js = root / "Speaker_Diarization" / f"{part}.json"
        if conv not in convs or not js.exists():
            continue
        turns = [
            [str(t["Speaker"]), float(t["Start_Time"]), float(t["End_Time"])]
            for t in json.loads(js.read_text()).values()
            if float(t["End_Time"]) > float(t["Start_Time"])
        ]
        recs.append(
            {
                "rec": f"msp-{part}",
                "sources": [
                    {
                        "path": str(root / "Audio" / f"{conv}.wav"),
                        "channel": 0,
                        "offset": ps - conv_t[conv][0],
                        "duration": pe - ps,
                    }
                ],
                "turns": turns,
            }
        )
    print(f"{write_jsonl(a.out, recs)} recordings")


if __name__ == "__main__":
    main()
