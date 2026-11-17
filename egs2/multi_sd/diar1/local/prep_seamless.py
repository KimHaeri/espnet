#!/usr/bin/env python3
"""Seamless Interaction (improvised, dev/test): two channels downmixed.

Each conversation is one stereo wav with one participant per channel and a
JSON whose ``channel_1``/``channel_2`` carry the corpus's own VAD segments;
those segments are the turns. The two channels are averaged into one.
Licence CC BY-NC 4.0: evaluation only.
"""

import argparse
import json
from pathlib import Path

from common import clean_id, write_jsonl


def main():
    p = argparse.ArgumentParser()
    p.add_argument("root")
    p.add_argument("split", choices=["dev", "test"])
    p.add_argument("out")
    a = p.parse_args()
    recs = []
    for js in sorted((Path(a.root) / a.split).glob("*.json")):
        wav = js.with_suffix(".wav")
        if not wav.exists():
            continue
        d = json.loads(js.read_text())
        turns = []
        for key in ("channel_1", "channel_2"):
            ch = d.get(key) or {}
            spk = clean_id(ch.get("id", key))
            for v in ch.get("metadata:vad") or []:
                if v["end"] > v["start"]:
                    turns.append([spk, float(v["start"]), float(v["end"])])
        recs.append(
            {
                "rec": f"seamless-{clean_id(js.stem)}",
                "sources": [{"path": str(wav), "channel": None}],
                "turns": turns,
            }
        )
    print(f"{write_jsonl(a.out, recs)} recordings")


if __name__ == "__main__":
    main()
