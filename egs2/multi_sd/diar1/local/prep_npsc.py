#!/usr/bin/env python3
"""NPSC (Norwegian parliament): full meeting audio, sentence-level turns.

The 48 kHz stereo meeting recording is downmixed. Turns are the transcribed
sentences (global speaker ids); the UEM spans the first to the last sentence
because the recordings start and end with untranscribed audio. The official
split is the ``data_split`` field: train, eval (used as dev) and test.
"""

import argparse
import json
from pathlib import Path

from common import write_jsonl


def main():
    p = argparse.ArgumentParser()
    p.add_argument("root")
    p.add_argument("split", choices=["train", "eval", "test"])
    p.add_argument("out")
    a = p.parse_args()
    recs = []
    for js in sorted(Path(a.root).glob("*/*_sentence_data.json")):
        d = json.loads(js.read_text())
        if d.get("data_split") != a.split:
            continue
        wav = js.parent / d["full_audio_file"]
        turns = [
            [str(s["speaker_id"]), s["start_time"] / 1000, s["end_time"] / 1000]
            for s in d["sentences"]
            if s["end_time"] > s["start_time"]
        ]
        uem = [[min(t[1] for t in turns), max(t[2] for t in turns)]]
        recs.append(
            {
                "rec": f"npsc-{d['meeting_date']}",
                "sources": [{"path": str(wav), "channel": None}],
                "turns": turns,
                "uem": uem,
            }
        )
    print(f"{write_jsonl(a.out, recs)} recordings")


if __name__ == "__main__":
    main()
