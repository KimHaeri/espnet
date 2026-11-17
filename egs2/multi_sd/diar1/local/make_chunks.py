#!/usr/bin/env python3
"""Cut recording-level data dirs into fixed-length training chunks.

Each chunk becomes its own recording in the output dir: wav.scp holds a sox
pipe that seeks into the recording, and turns are clipped to the chunk and
re-timed. Only speakers who are active in a chunk appear in its labels, so
EEND-EDA's attractor-existence target is right for every chunk.

Chunks are taken inside the UEM (whole recording when there is none). A chunk
is dropped when it overlaps an ``exclude`` region, has no speaker, or has
more than ``--max_spk`` speakers. ``utt2category`` gets the speaker count,
which the folded sampler uses to keep one speaker count per batch.
"""

import argparse
import logging
import random
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import read_kaldi_dir, write_kaldi_dir  # noqa: E402


def read_exclude(datadir: Path):
    out = {}
    f = datadir / "exclude"
    if f.exists():
        for line in f.read_text().splitlines():
            rec, s, e = line.split()
            out.setdefault(rec, []).append((float(s), float(e)))
    return out


def chunk_recording(rec, chunk, hop, min_chunk, exclude, max_spk, stats):
    regions = rec["uem"] or [(0.0, rec["duration"])]
    path = rec["wav"]
    if path.endswith("|"):
        raise ValueError(f"{rec['rec']}: chunking needs a file path, got a pipe")
    out = []
    for us, ue in regions:
        ue = min(ue, rec["duration"])
        t = us
        while t + min_chunk <= ue:
            s, e = t, min(t + chunk, ue)
            t += hop
            if any(xs < e and xe > s for xs, xe in exclude):
                stats["excluded"] += 1
                continue
            turns = [
                (spk, max(ts, s) - s, min(te, e) - s)
                for spk, ts, te in rec["turns"]
                if te > s and ts < e and min(te, e) - max(ts, s) > 0.01
            ]
            nspk = len({spk for spk, _, _ in turns})
            if nspk == 0:
                stats["no_speaker"] += 1
                continue
            if nspk > max_spk:
                stats["too_many_speakers"] += 1
                continue
            cid = f"{rec['rec']}-c{int(round(s * 100)):08d}"
            out.append(
                {
                    "rec": cid,
                    "wav": f"sox {path} -t wav - trim {s:.3f} {e - s:.3f} |",
                    "duration": e - s,
                    "turns": turns,
                    "nspk": nspk,
                }
            )
    return out


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("indirs", nargs="+", help="recording-level data dirs")
    p.add_argument("outdir")
    p.add_argument("--chunk_sec", type=float, default=30.0)
    p.add_argument("--hop_sec", type=float, default=None, help="default: chunk")
    p.add_argument("--min_chunk_sec", type=float, default=10.0)
    p.add_argument("--max_spk", type=int, default=8)
    p.add_argument(
        "--max_hours_per_dir",
        type=float,
        default=None,
        help="randomly keep at most this many hours from each input dir",
    )
    p.add_argument("--seed", type=int, default=0)
    args = p.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    hop = args.hop_sec or args.chunk_sec

    chunks = []
    for d in args.indirs:
        d = Path(d)
        stats = Counter()
        excl = read_exclude(d)
        mine = []
        for rec in read_kaldi_dir(str(d)):
            mine += chunk_recording(
                rec,
                args.chunk_sec,
                hop,
                args.min_chunk_sec,
                excl.get(rec["rec"], []),
                args.max_spk,
                stats,
            )
        if args.max_hours_per_dir is not None:
            random.Random(args.seed).shuffle(mine)
            keep, total = [], 0.0
            for c in mine:
                if total >= args.max_hours_per_dir * 3600:
                    break
                keep.append(c)
                total += c["duration"]
            mine = keep
        hours = sum(c["duration"] for c in mine) / 3600
        hist = Counter(c["nspk"] for c in mine)
        logging.info(
            "%s: %d chunks, %.1f h, speakers %s, dropped %s",
            d.name,
            len(mine),
            hours,
            dict(sorted(hist.items())),
            dict(stats),
        )
        chunks += mine

    write_kaldi_dir(args.outdir, chunks)
    with open(Path(args.outdir) / "utt2category", "w") as f:
        for c in sorted(chunks, key=lambda c: c["rec"]):
            f.write(f"{c['rec']} {c['nspk']}\n")
    logging.info(
        "total %d chunks, %.1f h",
        len(chunks),
        sum(c["duration"] for c in chunks) / 3600,
    )


if __name__ == "__main__":
    main()
