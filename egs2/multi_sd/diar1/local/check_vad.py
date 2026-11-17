#!/usr/bin/env python3
"""Measure the energy VAD against human turns on SpiCE's participant channel.

SpiCE transcribes the participant (left channel) but not the interviewer,
whose turns come from energy VAD. Running the same VAD on the participant
channel and comparing it with the TextGrid utterance tier gives a rough
accuracy figure for the VAD-derived labels (otoSpeech, SpiCE interviewer).
Prints frame-level (10 ms) precision, recall and miss/false-alarm rates.
"""

import argparse
import sys
from pathlib import Path

import numpy as np
import soundfile as sf

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import read_textgrid  # noqa: E402
from energy_vad import energy_vad  # noqa: E402

RES = 0.01


def to_mask(ivs, n):
    m = np.zeros(n, dtype=bool)
    for s, e in ivs:
        m[int(s / RES) : int(e / RES)] = True
    return m


def main():
    p = argparse.ArgumentParser()
    p.add_argument("spice_root")
    p.add_argument("--max_files", type=int, default=20)
    a = p.parse_args()
    tp = fp = fn = tot = 0
    files = sorted(Path(a.spice_root).glob("*/*.wav"))
    n_used = 0
    for wav in files:
        if n_used >= a.max_files:
            break
        tg = wav.with_suffix(".TextGrid")
        if not tg.exists() or sf.info(str(wav)).channels != 2:
            continue
        tiers = read_textgrid(str(tg))
        iv = [(s, e) for s, e, t in tiers.get("task", []) if t.strip() == "interview"]
        if not iv:
            continue
        s0, e0 = iv[0]
        fs = sf.info(str(wav)).samplerate
        x, _ = sf.read(str(wav), start=int(s0 * fs), stop=int(e0 * fs), dtype="float32")
        ref = [
            (max(s, s0) - s0, min(e, e0) - s0)
            for s, e, t in tiers.get("utterance", [])
            if t.strip() and e > s0 and s < e0
        ]
        hyp = energy_vad(x[:, 0], fs, refs=[x[:, 1]])
        n = int((e0 - s0) / RES) + 1
        r, h = to_mask(ref, n), to_mask(hyp, n)
        tp += (r & h).sum()
        fp += (~r & h).sum()
        fn += (r & ~h).sum()
        tot += r.sum()
        n_used += 1
        speech = max(r.sum(), 1)
        print(
            f"{wav.name}: ref {r.mean():.2f} hyp {h.mean():.2f} "
            f"miss {(r & ~h).sum() / speech:.3f} fa {(~r & h).sum() / speech:.3f}"
        )
    print(
        f"files {n_used}  precision {tp / max(tp + fp, 1):.3f}  "
        f"recall {tp / max(tp + fn, 1):.3f}  "
        f"miss/speech {fn / max(tot, 1):.3f}  fa/speech {fp / max(tot, 1):.3f}"
    )


if __name__ == "__main__":
    main()
