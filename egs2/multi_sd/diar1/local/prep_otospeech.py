#!/usr/bin/env python3
"""otoSpeech full-duplex sets: stereo (one speaker per channel), VAD turns.

Sessions are read straight from the WebDataset tar shards (data/train/*.tar,
<id>.flac + <id>.json). Neither set has speech timing, so turns come from
energy VAD on each speaker's channel (materialize.py, "vad": true) with the
other channel as cross-talk reference. ``redacted_segments`` become exclude
regions, and chunks touching them are dropped.
"""

import argparse
import json
import tarfile
from pathlib import Path

from common import clean_id, write_jsonl


def main():
    p = argparse.ArgumentParser()
    p.add_argument("root", help="corpus dir with data/train/*.tar")
    p.add_argument("name", help="short corpus tag used in recording ids")
    p.add_argument("out")
    a = p.parse_args()
    recs = []
    for shard in sorted((Path(a.root) / "data" / "train").glob("*.tar")):
        with tarfile.open(shard) as tar:
            members = {m.name: m for m in tar.getmembers() if m.isfile()}
            for name in sorted(members):
                if not name.endswith(".json"):
                    continue
                stem = name[: -len(".json")]
                audio = stem + ".flac"
                if audio not in members:
                    continue
                meta = json.load(tar.extractfile(members[name]))
                spks = sorted(meta.get("speakers", []), key=lambda s: s["channel"])
                if len(spks) != 2:
                    print(f"skip {stem}: {len(spks)} speakers")
                    continue
                base = min(s["channel"] for s in spks)  # 0- or 1-based
                sources = [
                    {
                        "path": f"{shard}::{audio}",
                        "channel": s["channel"] - base,
                        "spk": clean_id(s.get("speaker_id") or f"ch{s['channel']}"),
                    }
                    for s in spks
                ]
                excl = [
                    [float(r["start_sec"]), float(r["end_sec"])]
                    for r in meta.get("redacted_segments") or []
                ]
                recs.append(
                    {
                        "rec": f"{a.name}-{clean_id(Path(stem).name)}",
                        "sources": sources,
                        "turns": [],
                        "vad": True,
                        "exclude": excl,
                    }
                )
    print(f"{write_jsonl(a.out, recs)} recordings")


if __name__ == "__main__":
    main()
