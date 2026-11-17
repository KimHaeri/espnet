#!/usr/bin/env python3
"""Kallaama (Wolof, Pulaar, Sereer radio): mono wav, Transcriber turns.

The revised .trs in checked_transcriptions/<N>/ is used when it exists.
A turn listing several speakers ("spk1 spk2") marks all of them active for
the whole turn. Speaker ids are local to each file.
"""

import argparse
import re
from pathlib import Path

from common import write_jsonl

TURN_RE = re.compile(r"<Turn\b([^>]*)>")
ATTR_RE = re.compile(r'(\w+)="([^"]*)"')


def read_trs(path: Path):
    text = path.read_bytes().decode("latin-1")
    turns = []
    for attrs in TURN_RE.findall(text):
        d = dict(ATTR_RE.findall(attrs))
        if not d.get("speaker"):
            continue
        s, e = float(d["startTime"]), float(d["endTime"])
        for spk in d["speaker"].split():
            turns.append([spk, s, e])
    return turns


def main():
    p = argparse.ArgumentParser()
    p.add_argument("root", help="clean_dataset_ready4release dir")
    p.add_argument("out")
    a = p.parse_args()
    recs = []
    for lang in ("wolof", "pulaar", "sereer"):
        base = Path(a.root) / lang / "speech_dataset"
        checked = base / "checked_transcriptions"
        for wav in sorted(base.glob("*/*.wav")):
            trs = checked / wav.parent.name / f"{wav.stem}.trs"
            if not trs.exists():
                trs = wav.with_suffix(".trs")
            if not trs.exists():
                print(f"skip {wav.name}: no .trs")
                continue
            recs.append(
                {
                    "rec": f"kallaama-{wav.stem}",
                    "sources": [{"path": str(wav), "channel": 0}],
                    "turns": read_trs(trs),
                }
            )
    print(f"{write_jsonl(a.out, recs)} recordings")


if __name__ == "__main__":
    main()
