#!/usr/bin/env python3
"""PriMock57 (mock GP consultations): doctor + patient wavs mixed.

Each consultation has a time-aligned wav and a TextGrid per side; the wavs
are mixed (as the release's scripts/mix_audio.sh does) and the non-empty
intervals of each TextGrid are that speaker's turns (utterance level, so
turn boundaries are coarse).
"""

import argparse
from pathlib import Path

from common import read_textgrid, write_jsonl


def main():
    p = argparse.ArgumentParser()
    p.add_argument("root", help="primock57 repo dir (audio/, transcripts/)")
    p.add_argument("out")
    a = p.parse_args()
    root = Path(a.root)
    recs = []
    for doc in sorted((root / "audio").glob("*_doctor.wav")):
        cid = doc.name[: -len("_doctor.wav")]
        sources, turns = [], []
        for side in ("doctor", "patient"):
            wav = root / "audio" / f"{cid}_{side}.wav"
            tg = root / "transcripts" / f"{cid}_{side}.TextGrid"
            if not wav.exists() or not tg.exists():
                break
            sources.append({"path": str(wav), "channel": 0})
            for tier in read_textgrid(str(tg)).values():
                turns += [[side, s, e] for s, e, t in tier if t.strip()]
        if len(sources) == 2:
            recs.append({"rec": f"primock57-{cid}", "sources": sources, "turns": turns})
    print(f"{write_jsonl(a.out, recs)} recordings")


if __name__ == "__main__":
    main()
