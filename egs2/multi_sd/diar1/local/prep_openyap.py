#!/usr/bin/env python3
"""OpenYAP-1K: two speaker files mixed, turns from word timestamps.

Each conversation has speaker_a.flac and speaker_b.flac (one speaker each,
48 kHz). They are mixed into one channel; each speaker's words are joined
into turns across pauses of at most --merge_gap seconds.
Licensed internally (signed agreement): never redistribute the outputs.
"""

import argparse
import json
from pathlib import Path

from common import words_to_turns, write_jsonl


def main():
    p = argparse.ArgumentParser()
    p.add_argument("root")
    p.add_argument("out")
    p.add_argument("--merge_gap", type=float, default=0.3)
    a = p.parse_args()
    recs = []
    for conv in sorted((Path(a.root) / "conversations").glob("conv_*")):
        sources, words = [], []
        for side in ("a", "b"):
            audio = conv / f"speaker_{side}.flac"
            tr = conv / f"speaker_{side}_transcript.json"
            if not audio.exists() or not tr.exists():
                break
            sources.append({"path": str(audio), "channel": 0})
            for w in json.loads(tr.read_text()).get("words", []):
                if w.get("start") is not None and w.get("end") is not None:
                    words.append((side, float(w["start"]), float(w["end"])))
        if len(sources) != 2:
            print(f"skip {conv.name}: missing audio or transcript")
            continue
        recs.append(
            {
                "rec": f"openyap-{conv.name}",
                "sources": sources,
                "turns": [list(t) for t in words_to_turns(words, a.merge_gap)],
            }
        )
    print(f"{write_jsonl(a.out, recs)} recordings")


if __name__ == "__main__":
    main()
