#!/usr/bin/env python3
"""DataHive conversation samples: stereo MP3, one speaker per channel, VAD.

Caller on the left channel, callee on the right, on a shared timeline. No
transcripts are released, so turns come from energy VAD per channel (the
other channel as cross-talk reference). The per-language repos repeat the
multilingual one's files, so files are de-duplicated by name.
"""

import argparse
from pathlib import Path

from common import write_jsonl


def main():
    p = argparse.ArgumentParser()
    p.add_argument("root", help="datahive_conversations_sample dir")
    p.add_argument("out")
    a = p.parse_args()
    seen = {}
    for mp3 in sorted(Path(a.root).glob("*-conversations-sample/preview/*.mp3")):
        seen.setdefault(mp3.name, mp3)
    recs = [
        {
            "rec": f"datahive-{mp3.stem}",
            "sources": [
                {"path": str(mp3), "channel": 0, "spk": "caller"},
                {"path": str(mp3), "channel": 1, "spk": "callee"},
            ],
            "turns": [],
            "vad": True,
        }
        for _, mp3 in sorted(seen.items())
    ]
    print(f"{write_jsonl(a.out, recs)} recordings")


if __name__ == "__main__":
    main()
