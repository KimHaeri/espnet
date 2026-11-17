#!/usr/bin/env python3
"""Summary statistics of a diarization data dir (for local/CORPORA.md).

Prints recordings, audio hours, scored hours (UEM), speech hours, overlap
ratio of speech, and the speakers-per-recording distribution.
"""

import argparse
import sys
from collections import Counter
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import read_kaldi_dir  # noqa: E402

RES = 0.01  # 10 ms grid


def main():
    p = argparse.ArgumentParser()
    p.add_argument("datadir")
    a = p.parse_args()
    recs = read_kaldi_dir(a.datadir)
    audio = scored = speech = overlap = 0.0
    nspk = Counter()
    for r in recs:
        dur = r["duration"]
        audio += dur
        uem = r["uem"] or [(0.0, dur)]
        mask = np.zeros(int(dur / RES) + 1, dtype=bool)
        for s, e in uem:
            mask[int(s / RES) : int(e / RES)] = True
        scored += mask.sum() * RES
        count = np.zeros_like(mask, dtype=np.int16)
        for _, s, e in r["turns"]:
            count[int(s / RES) : int(e / RES)] += 1
        count[~mask] = 0
        speech += (count > 0).sum() * RES
        overlap += (count > 1).sum() * RES
        nspk[len({t[0] for t in r["turns"]})] += 1
    print(f"dir: {Path(a.datadir).name}")
    print(f"recordings: {len(recs)}")
    print(f"audio_hours: {audio / 3600:.2f}")
    print(f"scored_hours: {scored / 3600:.2f}")
    print(f"speech_hours: {speech / 3600:.2f}")
    print(f"speech_ratio: {speech / max(scored, 1e-9):.3f}")
    print(f"overlap_ratio_of_speech: {overlap / max(speech, 1e-9):.3f}")
    print(f"speakers_per_recording: {dict(sorted(nspk.items()))}")


if __name__ == "__main__":
    main()
