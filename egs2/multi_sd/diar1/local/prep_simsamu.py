#!/usr/bin/env python3
"""Simsamu (simulated French emergency calls): mono 8 kHz m4a + RTTM.

The shipped RTTM has <NA> as file id and channel, so only the onset,
duration and speaker fields are read. Speaker labels are roles (medecin,
patient, patient_1, ...).
"""

import argparse
from pathlib import Path

from common import write_jsonl


def main():
    p = argparse.ArgumentParser()
    p.add_argument("root", help="simsamu dir (one subdir per recording)")
    p.add_argument("out")
    a = p.parse_args()
    recs = []
    for d in sorted(x for x in Path(a.root).iterdir() if x.is_dir()):
        audio, rttm = d / f"{d.name}.m4a", d / f"{d.name}.rttm"
        if not audio.exists() or not rttm.exists():
            continue
        turns = []
        for line in rttm.read_text().splitlines():
            f = line.split()
            if len(f) >= 8 and f[0] == "SPEAKER":
                s, dur = float(f[3]), float(f[4])
                turns.append([f[7], s, s + dur])
        recs.append(
            {
                "rec": f"simsamu-{d.name}",
                "sources": [{"path": str(audio), "channel": 0}],
                "turns": turns,
            }
        )
    print(f"{write_jsonl(a.out, recs)} recordings")


if __name__ == "__main__":
    main()
