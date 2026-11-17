#!/usr/bin/env python3
"""CHiME-6 and DiPCo (dinner parties): one far-field channel, JSON turns.

Audio is channel 1 of array U01 (the first array present when U01 is
missing, as in some CHiME-6 sessions). CHiME-6 gives one time per segment;
DiPCo gives a time per device, and the one of the chosen array is used.
The UEM spans the first to the last annotated segment, because both corpora
have unannotated audio before the party starts.
"""

import argparse
import json
from pathlib import Path

from common import hms_to_sec, write_jsonl


def main():
    p = argparse.ArgumentParser()
    p.add_argument("corpus", choices=["chime6", "dipco"])
    p.add_argument("root")
    p.add_argument("split", choices=["train", "dev", "eval"])
    p.add_argument("out")
    a = p.parse_args()
    root = Path(a.root)
    if a.corpus == "chime6":
        audio = root / f"CHiME6_{a.split}" / "CHiME6" / "audio" / a.split
        trans = root / "transcriptions" / "transcriptions" / a.split
    else:
        audio = root / "audio" / a.split
        trans = root / "transcriptions" / a.split
    recs = []
    for js in sorted(trans.glob("S*.json")):
        sess = js.stem
        arrays = [
            u
            for u in ("U01", "U02", "U03", "U04", "U05", "U06")
            if (audio / f"{sess}_{u}.CH1.wav").exists()
        ]
        if not arrays:
            print(f"skip {sess}: no array audio")
            continue
        dev = arrays[0]
        turns = []
        for seg in json.loads(js.read_text()):
            s, e = seg["start_time"], seg["end_time"]
            if isinstance(s, dict):
                s, e = s.get(dev, s.get("close-talk")), e.get(dev, e.get("close-talk"))
            s, e = hms_to_sec(s), hms_to_sec(e)
            spk = seg.get("speaker") or seg.get("speaker_id")
            if e > s:
                turns.append([spk, s, e])
        uem = [[min(t[1] for t in turns), max(t[2] for t in turns)]]
        recs.append(
            {
                "rec": f"{a.corpus}-{sess}-{dev}",
                "sources": [
                    {"path": str(audio / f"{sess}_{dev}.CH1.wav"), "channel": 0}
                ],
                "turns": turns,
                "uem": uem,
            }
        )
    print(f"{write_jsonl(a.out, recs)} recordings")


if __name__ == "__main__":
    main()
