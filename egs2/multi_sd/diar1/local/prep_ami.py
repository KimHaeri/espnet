#!/usr/bin/env python3
"""AMI: Array1-01 far-field channel, turns from the NXT segment files.

Splits are the official Full-ASR lists shipped with egs2/ami/asr1, except
that IB4005 is dropped from train: its speakers MIO036 and FIE038 also take
part in dev meetings (IB4001-IB4004, IS1008a-d), and the AMI diarization
setups (BUT, pyannote) leave it out too.
Meetings without array audio (IS1003b, IS1007d in train) are skipped.
"""

import argparse
import re
from pathlib import Path

from common import write_jsonl

SPLIT_DIR = Path(__file__).resolve().parents[3] / "ami" / "asr1" / "local"
# train meetings that share speakers with dev/eval
EXCLUDE = {"train": {"IB4005"}}
SEG_RE = re.compile(r'transcriber_start="([\d.]+)"\s+transcriber_end="([\d.]+)"')


def main():
    p = argparse.ArgumentParser()
    p.add_argument("root", help="AMI root (meeting dirs + annotations/)")
    p.add_argument("split", choices=["train", "dev", "eval"])
    p.add_argument("out")
    a = p.parse_args()
    root = Path(a.root)
    meetings = (SPLIT_DIR / f"split_{a.split}.orig").read_text().split()
    recs = []
    for m in meetings:
        if m in EXCLUDE.get(a.split, ()):
            print(f"skip {m}: shares speakers with dev/eval")
            continue
        wav = root / m / "audio" / f"{m}.Array1-01.wav"
        if not wav.exists():
            print(f"skip {m}: no Array1-01")
            continue
        turns = []
        for seg in sorted(
            (root / "annotations" / "segments").glob(f"{m}.*.segments.xml")
        ):
            spk = seg.name.split(".")[1]
            for s, e in SEG_RE.findall(seg.read_text()):
                turns.append([spk, float(s), float(e)])
        recs.append(
            {
                "rec": f"ami-{m}",
                "sources": [{"path": str(wav), "channel": 0}],
                "turns": turns,
            }
        )
    print(f"{write_jsonl(a.out, recs)} recordings")


if __name__ == "__main__":
    main()
