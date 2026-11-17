#!/usr/bin/env python3
"""EgoCom: one wearer's glasses audio per conversation part, word turns.

Every conversation part was filmed by 2-3 wearers; their recordings are
synchronised views of the same conversation, so only the lowest-numbered
wearer's file is used (the others would duplicate the data). Both glasses
channels are averaged. Word timestamps of ground_truth_transcriptions.csv
(relative to the conversation part) are joined into turns.
"""

import argparse
import csv
import re
from pathlib import Path

from common import words_to_turns, write_jsonl

NAME_RE = re.compile(r"vid_\d+__(day_\d+__con_\d+)__person_(\d+)(?:_(part\d+))?\.wav")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("root")
    p.add_argument("out")
    p.add_argument("--merge_gap", type=float, default=0.3)
    a = p.parse_args()
    root = Path(a.root)
    words = {}
    with open(root / "metadata" / "ground_truth_transcriptions.csv") as f:
        for row in csv.DictReader(f):
            try:
                s, e = float(row["startTime"]), float(row["endTime"])
            except (TypeError, ValueError):
                continue
            if row["speaker_id"] and e > s:
                words.setdefault(row["conversation_id"], []).append(
                    (row["speaker_id"], s, e)
                )
    views = {}
    for wav in sorted((root / "egocom_audio_only").glob("*.wav")):
        m = NAME_RE.fullmatch(wav.name)
        if m:
            # conversations recorded in one piece have no _partK suffix
            cid = m.group(1) + (f"__{m.group(3)}" if m.group(3) else "")
            views.setdefault(cid, []).append((int(m.group(2)), wav))
    recs = []
    for cid, vs in sorted(views.items()):
        if cid not in words:
            print(f"skip {cid}: no transcription")
            continue
        wav = min(vs)[1]
        recs.append(
            {
                "rec": f"egocom-{cid}",
                "sources": [{"path": str(wav), "channel": None}],
                "turns": [list(t) for t in words_to_turns(words[cid], a.merge_gap)],
            }
        )
    print(f"{write_jsonl(a.out, recs)} recordings")


if __name__ == "__main__":
    main()
