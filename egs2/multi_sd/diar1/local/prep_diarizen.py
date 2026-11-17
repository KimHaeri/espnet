#!/usr/bin/env python3
"""Eval sets taken from the DiariZen compound dataset copy.

VoxConverse, DIHARD III and the AliMeeting Eval set are on the lab storage
only inside DiariZen_Compound_dataset/{train,dev,test}/<subset>/ (wavs/,
rttm, all.uem). DiariZen moved part of the official VoxConverse and DIHARD
III dev sets into its own "train", so the official dev set is rebuilt by
taking the subset from several DiariZen splits (e.g. train + dev). The wav
paths in DiariZen's wav.scp point to another cluster and are not used.
Multi-channel files (AliMeeting far-field arrays) use channel 0.
"""

import argparse
from pathlib import Path

from common import clean_id, read_rttm, read_uem, write_jsonl


def main():
    p = argparse.ArgumentParser()
    p.add_argument("root", help="DiariZen_Compound_dataset dir")
    p.add_argument("subset", help="e.g. VoxConverse, DIHARD3, AliMeeting")
    p.add_argument("splits", help="comma-separated DiariZen splits, e.g. train,dev")
    p.add_argument("tag", help="corpus tag used in recording ids")
    p.add_argument("out")
    p.add_argument("--prefix", default="", help="keep only ids with this prefix")
    a = p.parse_args()
    recs = []
    for split in a.splits.split(","):
        d = Path(a.root) / split / a.subset
        rttm = read_rttm(str(d / "rttm"))
        uem = read_uem(str(d / "all.uem")) if (d / "all.uem").exists() else {}
        for wav in sorted((d / "wavs").glob("*.wav")):
            rid = wav.stem
            if not rid.startswith(a.prefix):
                continue
            if rid not in rttm:
                print(f"skip {rid}: not in rttm")
                continue
            recs.append(
                {
                    "rec": f"{a.tag}-{clean_id(rid)}",
                    "sources": [{"path": str(wav), "channel": 0}],
                    "turns": [list(t) for t in rttm[rid]],
                    "uem": [list(u) for u in uem.get(rid, [])] or None,
                }
            )
    print(f"{write_jsonl(a.out, recs)} recordings")


if __name__ == "__main__":
    main()
