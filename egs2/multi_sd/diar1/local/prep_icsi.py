#!/usr/bin/env python3
"""ICSI meetings: one tabletop (far-field) channel, NXT segment turns.

Audio is the first tabletop channel present (chanA..chanF, shorten-compressed
SPHERE, decoded by sph2pipe). Turns are the segments in ICSI/Segments of
ICSI_core_NXT.zip, read straight from the zip (it is not extracted).
"""

import argparse
import re
import zipfile
from pathlib import Path

from common import write_jsonl

SEG_RE = re.compile(r"<segment\b([^>]*)>")
ATTR_RE = re.compile(r'([\w:-]+)="([^"]*)"')


def main():
    p = argparse.ArgumentParser()
    p.add_argument("root", help="ICSI dir with Signals/ and ICSI_core_NXT.zip")
    p.add_argument("out")
    a = p.parse_args()
    root = Path(a.root)
    turns = {}
    with zipfile.ZipFile(root / "ICSI_core_NXT.zip") as z:
        for name in z.namelist():
            if not (name.startswith("ICSI/Segments/") and name.endswith(".segs.xml")):
                continue
            mtg = Path(name).name.split(".")[0]
            for attrs in SEG_RE.findall(z.read(name).decode("latin-1")):
                d = dict(ATTR_RE.findall(attrs))
                if d.get("starttime") and d.get("endtime") and d.get("participant"):
                    s, e = float(d["starttime"]), float(d["endtime"])
                    if e > s:
                        turns.setdefault(mtg, []).append([d["participant"], s, e])
    recs = []
    for mdir in sorted((root / "Signals").iterdir()):
        chans = [
            mdir / f"chan{c}.sph" for c in "ABCDEF" if (mdir / f"chan{c}.sph").exists()
        ]
        if not chans or mdir.name not in turns:
            print(f"skip {mdir.name}: no tabletop channel or no segments")
            continue
        recs.append(
            {
                "rec": f"icsi-{mdir.name}-{chans[0].stem}",
                "sources": [{"path": str(chans[0]), "channel": 0}],
                "turns": turns[mdir.name],
            }
        )
    print(f"{write_jsonl(a.out, recs)} recordings")


if __name__ == "__main__":
    main()
