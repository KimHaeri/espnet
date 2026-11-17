#!/usr/bin/env python3
"""Spjallromur (Icelandic conversations): two speaker files mixed.

Uses the re-aligned release's ready-made RTTM (github/combined/<id>/), which
covers 46 full conversations. The two speaker wavs (one speaker each, 16
kHz) are mixed, as the release's own convert2diarization.py does. The ASR
splits are per speaker side, so all conversations are used for training.
"""

import argparse
from pathlib import Path

from common import read_rttm, write_jsonl


def main():
    p = argparse.ArgumentParser()
    p.add_argument("root")
    p.add_argument("out")
    a = p.parse_args()
    recs = []
    audio_dir = Path(a.root) / "audio" / "spjallromur" / "data"
    for rttm in sorted(
        (Path(a.root) / "github" / "combined").glob("*/combined_*.rttm")
    ):
        cid = rttm.parent.name
        # the wavs sit next to the RTTM for some conversations and in the
        # original release (audio/.../full_conversations/<id>/) for the rest
        wavs = []
        for d in (
            rttm.parent,
            audio_dir / "full_conversations" / cid,
            audio_dir / "half_conversations" / cid,
        ):
            wavs = [d / f"speaker_{s}_convo_{cid}.wav" for s in ("a", "b")]
            if all(w.exists() for w in wavs):
                break
        if not all(w.exists() for w in wavs):
            print(f"skip {cid}: missing speaker wav")
            continue
        turns = [list(t) for ts in read_rttm(str(rttm)).values() for t in ts]
        recs.append(
            {
                "rec": f"spjallromur-{cid}",
                "sources": [{"path": str(w), "channel": 0} for w in wavs],
                "turns": turns,
            }
        )
    print(f"{write_jsonl(a.out, recs)} recordings")


if __name__ == "__main__":
    main()
