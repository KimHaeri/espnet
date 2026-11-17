"""Shared helpers for the multi-corpus diarization data preparation.

Every ``prep_<corpus>.py`` describes its recordings as JSON lines (one object
per recording) and ``materialize.py`` turns that description into 8 kHz mono
audio and a Kaldi-style data directory. A recording object looks like::

    {
      "rec": "ami-ES2002a",                 # unique id, prefixed by corpus
      "sources": [                          # summed into one channel
        {"path": "/x/ES2002a.Array1-01.wav", "channel": 0,
         "offset": 0.0, "duration": null, "spk": null}
      ],
      "turns": [["A", 1.20, 3.45], ...],    # speaker, start, end (seconds)
      "vad": false,                          # derive turns of sources with
                                             # a "spk" by energy VAD instead
      "uem": [[0.0, 1834.2]],               # scored region (optional)
      "exclude": [[100.0, 103.5]]           # regions to drop (optional)
    }

``path`` may be ``<tar>::<member>`` (read from a tar shard) or
``<parquet>::<row>::<column>`` (audio bytes in a parquet file); ``.sph``
files are decoded with sph2pipe. ``channel`` is 0-based, ``null`` means
"average all channels".
"""

import json
import re
from pathlib import Path
from typing import Dict, Iterable, Iterator, List, Optional, Sequence, Tuple

Turn = Tuple[str, float, float]


def read_jsonl(path: str) -> Iterator[Dict]:
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                yield json.loads(line)


def write_jsonl(path: str, items: Iterable[Dict]) -> int:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with open(path, "w", encoding="utf-8") as f:
        for item in items:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
            n += 1
    return n


def hms_to_sec(value) -> float:
    """Parse ``HH:MM:SS.ss`` / ``MM:SS.ss`` / plain seconds."""
    if isinstance(value, (int, float)):
        return float(value)
    parts = str(value).strip().split(":")
    sec = 0.0
    for p in parts:
        sec = sec * 60 + float(p)
    return sec


def clean_id(text: str) -> str:
    """Make a string safe for Kaldi ids (no spaces or slashes)."""
    return re.sub(r"[^A-Za-z0-9_.\-]", "_", str(text))


def merge_intervals(
    intervals: Iterable[Tuple[float, float]], gap: float = 0.0
) -> List[Tuple[float, float]]:
    """Union of intervals, also joining pieces closer than ``gap`` seconds."""
    out: List[List[float]] = []
    for s, e in sorted((float(s), float(e)) for s, e in intervals if e > s):
        if out and s <= out[-1][1] + gap:
            out[-1][1] = max(out[-1][1], e)
        else:
            out.append([s, e])
    return [(s, e) for s, e in out]


def normalize_turns(turns: Iterable[Sequence], gap: float = 0.0) -> List[Turn]:
    """Merge overlapping (or ``gap``-close) turns of the same speaker."""
    by_spk: Dict[str, List[Tuple[float, float]]] = {}
    for spk, s, e in turns:
        by_spk.setdefault(str(spk), []).append((float(s), float(e)))
    out: List[Turn] = []
    for spk, ivs in by_spk.items():
        out += [(spk, s, e) for s, e in merge_intervals(ivs, gap)]
    return sorted(out, key=lambda t: (t[1], t[2], t[0]))


def words_to_turns(
    words: Iterable[Tuple[str, float, float]], gap: float = 0.3
) -> List[Turn]:
    """Join word timestamps of each speaker into turns (pauses <= gap)."""
    return normalize_turns(words, gap=gap)


def subtract_intervals(
    intervals: List[Tuple[float, float]], cut: List[Tuple[float, float]]
) -> List[Tuple[float, float]]:
    """Remove the ``cut`` regions from ``intervals``."""
    out = []
    cut = merge_intervals(cut)
    for s, e in intervals:
        pieces = [(s, e)]
        for cs, ce in cut:
            nxt = []
            for ps, pe in pieces:
                if ce <= ps or cs >= pe:
                    nxt.append((ps, pe))
                    continue
                if cs > ps:
                    nxt.append((ps, cs))
                if ce < pe:
                    nxt.append((ce, pe))
            pieces = nxt
        out += pieces
    return out


# ----------------------------------------------------------------- readers
def read_textgrid(path: str) -> Dict[str, List[Tuple[float, float, str]]]:
    """Minimal Praat TextGrid (long format) reader: tier -> intervals.

    Handles UTF-8 and UTF-16 files. Point tiers are skipped.
    """
    raw = Path(path).read_bytes()
    if raw[:2] in (b"\xff\xfe", b"\xfe\xff"):
        text = raw.decode("utf-16")
    else:
        text = raw.decode("utf-8", errors="replace").lstrip("﻿")
    tiers: Dict[str, List[Tuple[float, float, str]]] = {}
    name = None
    is_interval = False
    xmin = xmax = None
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("class ="):
            is_interval = "IntervalTier" in line
            name = None
        elif line.startswith("name =") and name is None:
            name = line.split("=", 1)[1].strip().strip('"')
            if is_interval:
                tiers[name] = []
        elif not is_interval or name is None:
            continue
        elif line.startswith("xmin ="):
            xmin = float(line.split("=", 1)[1])
        elif line.startswith("xmax ="):
            xmax = float(line.split("=", 1)[1])
        elif line.startswith("text ="):
            label = line.split("=", 1)[1].strip()
            if label.startswith('"') and label.endswith('"'):
                label = label[1:-1]
            tiers[name].append((xmin, xmax, label.replace('""', '"')))
    return tiers


def read_rttm(path: str) -> Dict[str, List[Turn]]:
    out: Dict[str, List[Turn]] = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            p = line.split()
            if len(p) < 8 or p[0] != "SPEAKER":
                continue
            s, d = float(p[3]), float(p[4])
            out.setdefault(p[1], []).append((p[7], s, s + d))
    return out


def read_uem(path: str) -> Dict[str, List[Tuple[float, float]]]:
    out: Dict[str, List[Tuple[float, float]]] = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            p = line.split()
            if len(p) >= 4:
                out.setdefault(p[0], []).append((float(p[2]), float(p[3])))
    return out


# ----------------------------------------------------------- kaldi output
def seg_id(spk_id: str, rec: str, s: float, e: float) -> str:
    return f"{spk_id}-{rec}-{int(round(s * 100)):08d}-{int(round(e * 100)):08d}"


def write_kaldi_dir(
    outdir: str,
    recs: List[Dict],
    min_turn: float = 0.0,
) -> None:
    """Write wav.scp/segments/utt2spk/spk2utt/rttm/reco2dur(/uem).

    Each item of ``recs`` needs ``rec``, ``wav`` (path or "cmd |"),
    ``duration`` and ``turns``; ``uem`` is optional. Speaker ids are made
    recording-local (``<rec>_<spk>``) so that utt2spk stays sorted and ids
    never collide across corpora.
    """
    out = Path(outdir)
    out.mkdir(parents=True, exist_ok=True)
    wav, dur, seg, u2s, rttm, uem = [], [], [], [], [], []
    for r in sorted(recs, key=lambda x: x["rec"]):
        rec = r["rec"]
        if not any(
            min(float(r["duration"]), e) - max(0.0, s) > min_turn
            for _, s, e in r["turns"]
        ):
            print(f"drop {rec}: no speaker turns")
            continue
        wav.append(f"{rec} {r['wav']}")
        dur.append(f"{rec} {r['duration']:.3f}")
        for spk, s, e in r["turns"]:
            s, e = max(0.0, s), min(float(r["duration"]), e)
            if e - s <= min_turn:
                continue
            sid = f"{rec}_{clean_id(spk)}"
            u = seg_id(sid, rec, s, e)
            seg.append(f"{u} {rec} {s:.3f} {e:.3f}")
            u2s.append(f"{u} {sid}")
            rttm.append(
                f"SPEAKER {rec} 1 {s:.3f} {e - s:.3f} <NA> <NA> {sid} <NA> <NA>"
            )
        for s, e in r.get("uem") or []:
            uem.append(f"{rec} 1 {s:.3f} {e:.3f}")
    seg_sorted = sorted(zip(seg, u2s))
    spk2utt: Dict[str, List[str]] = {}
    for _, line in seg_sorted:
        u, spk = line.split()
        spk2utt.setdefault(spk, []).append(u)

    def dump(name, lines):
        with open(out / name, "w", encoding="utf-8") as f:
            for line in lines:
                f.write(line + "\n")

    dump("wav.scp", wav)
    dump("reco2dur", dur)
    dump("segments", [a for a, _ in seg_sorted])
    dump("utt2spk", [b for _, b in seg_sorted])
    dump("spk2utt", [f"{k} {' '.join(v)}" for k, v in sorted(spk2utt.items())])
    dump("rttm", rttm)
    if uem:
        dump("uem", uem)


def read_kaldi_dir(datadir: str) -> List[Dict]:
    """Inverse of :func:`write_kaldi_dir` (turns use the speaker ids)."""
    d = Path(datadir)
    recs: Dict[str, Dict] = {}
    with open(d / "wav.scp", encoding="utf-8") as f:
        for line in f:
            rec, w = line.rstrip("\n").split(maxsplit=1)
            recs[rec] = {"rec": rec, "wav": w, "turns": [], "uem": []}
    with open(d / "reco2dur", encoding="utf-8") as f:
        for line in f:
            rec, v = line.split()
            if rec in recs:
                recs[rec]["duration"] = float(v)
    u2s = {}
    if (d / "utt2spk").exists():
        with open(d / "utt2spk", encoding="utf-8") as f:
            for line in f:
                u, s = line.split()
                u2s[u] = s
    if (d / "segments").exists():
        with open(d / "segments", encoding="utf-8") as f:
            for line in f:
                u, rec, s, e = line.split()
                if rec in recs:
                    recs[rec]["turns"].append((u2s[u], float(s), float(e)))
    if (d / "uem").exists():
        for rec, ivs in read_uem(str(d / "uem")).items():
            if rec in recs:
                recs[rec]["uem"] = ivs
    return [recs[k] for k in sorted(recs)]


def chunked(seq: List, n: int) -> List[List]:
    return [seq[i : i + n] for i in range(0, len(seq), n)]


def opt_float(value: Optional[str]) -> Optional[float]:
    return None if value in (None, "", "null") else float(value)
