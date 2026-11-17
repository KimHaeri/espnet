#!/usr/bin/env python3
"""SpiCE (Cantonese/English interviews): interview section, two channels.

Only the ``interview`` interval of the task tier is kept; the read sentences
and the storyboard narration have a single talker. The left channel is the
participant, whose turns are the non-empty intervals of the utterance tier.
The right channel is the interviewer, who was never transcribed, so the
interviewer's turns come from energy VAD (participant channel as cross-talk
reference). The one mono file (participant only) is skipped.
"""

import argparse
from pathlib import Path

import soundfile as sf
from common import read_textgrid, write_jsonl


def main():
    p = argparse.ArgumentParser()
    p.add_argument("root")
    p.add_argument("out")
    a = p.parse_args()
    recs = []
    for lang in ("cantonese", "english"):
        for wav in sorted((Path(a.root) / lang).glob("*.wav")):
            tg = wav.with_suffix(".TextGrid")
            if not tg.exists() or sf.info(str(wav)).channels != 2:
                print(f"skip {wav.name}: no TextGrid or not stereo")
                continue
            tiers = read_textgrid(str(tg))
            iv = [
                (s, e) for s, e, t in tiers.get("task", []) if t.strip() == "interview"
            ]
            if not iv:
                print(f"skip {wav.name}: no interview interval")
                continue
            s0, e0 = iv[0]
            turns = [
                ["participant", max(s, s0) - s0, min(e, e0) - s0]
                for s, e, t in tiers.get("utterance", [])
                if t.strip() and e > s0 and s < e0
            ]
            src = {"path": str(wav), "offset": s0, "duration": e0 - s0}
            recs.append(
                {
                    "rec": f"spice-{wav.stem}",
                    "sources": [
                        dict(src, channel=0),
                        dict(src, channel=1, spk="interviewer"),
                    ],
                    "turns": turns,
                    "vad": True,
                }
            )
    print(f"{write_jsonl(a.out, recs)} recordings")


if __name__ == "__main__":
    main()
