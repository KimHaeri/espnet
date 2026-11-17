#!/usr/bin/env python3
"""LibriSpeech simulated meetings (lab simulation), clean condition only.

3000 meetings of about 600 s with 3-8 speakers, 16 kHz mono, one RTTM per
meeting in out/clean/shard*/rttm/. The noise/reverb conditions of the same
simulation are not used.
"""

import argparse
from pathlib import Path

from common import read_rttm, write_jsonl


def main():
    p = argparse.ArgumentParser()
    p.add_argument("root", help="librispeech_meetings_2k dir (with out/clean)")
    p.add_argument("out")
    p.add_argument("--condition", default="clean")
    a = p.parse_args()
    recs = []
    for shard in sorted((Path(a.root) / "out" / a.condition).glob("shard*")):
        for wav in sorted((shard / "audio").glob("*.wav")):
            rttm = shard / "rttm" / f"{wav.stem}.rttm"
            if not rttm.exists():
                print(f"skip {wav.stem}: no rttm")
                continue
            turns = [list(t) for ts in read_rttm(str(rttm)).values() for t in ts]
            recs.append(
                {
                    "rec": f"libmeet-{a.condition}-{wav.stem}",
                    "sources": [{"path": str(wav), "channel": 0}],
                    "turns": turns,
                }
            )
    print(f"{write_jsonl(a.out, recs)} recordings")


if __name__ == "__main__":
    main()
