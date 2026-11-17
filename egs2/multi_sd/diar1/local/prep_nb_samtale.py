#!/usr/bin/env python3
"""NB Samtale: rebuild full recordings from the released segments.

Språkbanken releases NB Samtale only as cut segments (nb_samtale.zip, the
same as the HF copy). Each segment file is ``<source>_<start ms>-<end
ms>.wav``, so the 35 source recordings are rebuilt by placing every segment
(train, dev, test and background_noise) at its position:

* where segments overlap, the samples of the first one placed are kept
  (they are cut from the same source, so either copy is the source audio);
* positions no segment covers stay digital silence; the coverage is
  printed per recording.

Turns are the transcribed segments (metadata.jsonl, global speaker ids);
background_noise segments only fill the timeline. All splits are used for
training (user decision). The UEM spans the first to the last segment.
"""

import argparse
import json
import re
from pathlib import Path

import numpy as np
import soundfile as sf
from common import write_jsonl

NAME_RE = re.compile(r"(.+)_(\d+)-(\d+)\.wav")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("root", help="extracted nb_samtale dir (data/, metadata.jsonl)")
    p.add_argument("rebuilt_dir", help="where the rebuilt recordings are written")
    p.add_argument("out")
    a = p.parse_args()
    root, outdir = Path(a.root), Path(a.rebuilt_dir)
    outdir.mkdir(parents=True, exist_ok=True)

    turns = {}
    for line in open(root / "metadata.jsonl", encoding="utf-8"):
        m = json.loads(line)
        s, e = (int(x) / 1000 for x in m["segment_id"].split("-"))
        turns.setdefault(m["source_file_id"], []).append([m["speaker_id"], s, e])

    pieces = {}
    for wav in sorted((root / "data").glob("*/**/*.wav")):
        mm = NAME_RE.fullmatch(wav.name)
        if mm:
            pieces.setdefault(mm.group(1), []).append(
                (int(mm.group(2)), int(mm.group(3)), wav)
            )

    recs = []
    for src in sorted(turns):
        segs = sorted(pieces.get(src, []))
        if not segs:
            print(f"skip {src}: no segment audio")
            continue
        fs = sf.info(str(segs[0][2])).samplerate
        total = max(e for _, e, _ in segs) * fs // 1000 + fs
        audio = np.zeros(total, dtype=np.float32)
        filled = np.zeros(total, dtype=bool)
        for s_ms, _, wav in segs:
            x, sr = sf.read(str(wav), dtype="float32", always_2d=True)
            assert sr == fs, f"{wav}: {sr} != {fs}"
            x = x.mean(axis=1)
            st = s_ms * fs // 1000
            x = x[: total - st]
            free = ~filled[st : st + len(x)]
            audio[st : st + len(x)][free] = x[free]
            filled[st : st + len(x)] = True
        last = int(np.flatnonzero(filled)[-1]) + 1
        path = outdir / f"{src}.wav"
        sf.write(str(path), audio[:last], fs, subtype="PCM_16")
        ts = turns[src]
        span = [min(t[1] for t in ts), max(t[2] for t in ts)]
        cov = filled[int(span[0] * fs) : int(span[1] * fs)].mean()
        print(f"{src}: {last / fs / 60:.1f} min, {cov:.1%} of the turn span covered")
        recs.append(
            {
                "rec": f"nbsamtale-{src}",
                "sources": [{"path": str(path), "channel": 0}],
                "turns": ts,
                "uem": [span],
            }
        )
    print(f"{write_jsonl(a.out, recs)} recordings")


if __name__ == "__main__":
    main()
