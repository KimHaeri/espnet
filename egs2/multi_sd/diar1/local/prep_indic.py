#!/usr/bin/env python3
"""Indic High-Fidelity MultiSpeaker ASR: mono mixed audio in parquet files.

Audio bytes stay in the parquet files (read by materialize.py through
``<parquet>::<row>::audio``). Turns are the speaker-labelled segments of
``transcript_json`` (HH:MM:SS.mmm strings).
"""

import argparse
import json
from pathlib import Path

import pyarrow.parquet as pq
from common import clean_id, hms_to_sec, write_jsonl


def main():
    p = argparse.ArgumentParser()
    p.add_argument("root")
    p.add_argument("out")
    a = p.parse_args()
    recs = []
    for pqf in sorted((Path(a.root) / "data").glob("*.parquet")):
        table = pq.read_table(pqf, columns=["file_name", "transcript_json"])
        for row, (name, tj) in enumerate(
            zip(
                table.column("file_name").to_pylist(),
                table.column("transcript_json").to_pylist(),
            )
        ):
            turns = []
            for seg in json.loads(tj):
                s, e = hms_to_sec(seg["start"]), hms_to_sec(seg["end"])
                if e > s:
                    turns.append([clean_id(seg["speaker"]), s, e])
            recs.append(
                {
                    "rec": f"indic-{clean_id(Path(name).stem)}",
                    "sources": [{"path": f"{pqf}::{row}::audio", "channel": 0}],
                    "turns": turns,
                }
            )
    print(f"{write_jsonl(a.out, recs)} recordings")


if __name__ == "__main__":
    main()
