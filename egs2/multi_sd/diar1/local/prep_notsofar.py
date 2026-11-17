#!/usr/bin/env python3
"""NOTSOFAR-1: first single-channel far-field device, gt_transcription turns.

Splits: train (240501.1_train), dev (240415.2_dev_with_GT) and the small
evaluation set with ground truth (240629.1_eval_small_with_GT).
"""

import argparse
import json
from pathlib import Path

from common import clean_id, write_jsonl

SETS = {
    "train": "train/train_set/240501.1_train/MTG",
    "dev": "dev/dev_set/240415.2_dev_with_GT/MTG",
    "eval": "eval/eval_set/240629.1_eval_small_with_GT/MTG",
}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("root")
    p.add_argument("split", choices=list(SETS))
    p.add_argument("out")
    a = p.parse_args()
    recs = []
    for mtg in sorted((Path(a.root) / SETS[a.split]).glob("MTG_*")):
        sc = sorted(d for d in mtg.glob("sc_*") if (d / "ch0.wav").exists())
        gt = mtg / "gt_transcription.json"
        if not sc or not gt.exists():
            print(f"skip {mtg.name}: no sc device or transcription")
            continue
        turns = [
            [clean_id(t["speaker_id"]), float(t["start_time"]), float(t["end_time"])]
            for t in json.loads(gt.read_text())
        ]
        recs.append(
            {
                "rec": f"notsofar1-{mtg.name}-{sc[0].name}",
                "sources": [{"path": str(sc[0] / "ch0.wav"), "channel": 0}],
                "turns": turns,
            }
        )
    print(f"{write_jsonl(a.out, recs)} recordings")


if __name__ == "__main__":
    main()
