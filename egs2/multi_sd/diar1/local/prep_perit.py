#!/usr/bin/env python3
"""Perit duplex support role-plays (English): stereo, one speaker per channel.

No time-stamped transcripts: turns come from energy VAD per channel. Which
channel holds the agent varies between files, so the speakers are labelled by
channel only (labels are recording-local anyway).
"""

import argparse
from pathlib import Path

from common import clean_id, write_jsonl


def main():
    p = argparse.ArgumentParser()
    p.add_argument("root", help="perit-duplex-support-en dir")
    p.add_argument("out")
    a = p.parse_args()
    recs = [
        {
            "rec": f"perit-{clean_id(w.stem)}",
            "sources": [
                {"path": str(w), "channel": 0, "spk": "left"},
                {"path": str(w), "channel": 1, "spk": "right"},
            ],
            "turns": [],
            "vad": True,
        }
        for w in sorted((Path(a.root) / "data").glob("*.wav"))
    ]
    print(f"{write_jsonl(a.out, recs)} recordings")


if __name__ == "__main__":
    main()
