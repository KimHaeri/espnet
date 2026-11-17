#!/usr/bin/env python3
"""Turn a recordings.jsonl (see common.py) into 8 kHz audio + a data dir.

For every recording each source is decoded, trimmed, reduced to one channel
and resampled to 8 kHz with sox; several sources are mixed with ``sox -m``
(which scales each input by 1/N, so the sum cannot clip). Sources carrying a
``spk`` get their turns from energy VAD when the recording has ``"vad": true``.
Finished audio is reused on a rerun, so the step can be resumed.
"""

import argparse
import json
import logging
import shutil
import subprocess
import sys
import tarfile
import tempfile
import traceback
from multiprocessing import Pool
from pathlib import Path

import soundfile as sf

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (  # noqa: E402
    normalize_turns,
    read_jsonl,
    write_jsonl,
    write_kaldi_dir,
)
from energy_vad import energy_vad  # noqa: E402

FS = 8000
ARGS = None


def _source_bytes(path: str):
    """Return (bytes, sox type) for tar/parquet members, else None."""
    if "::" not in path:
        return None
    parts = path.split("::")
    if parts[0].endswith(".tar"):
        with tarfile.open(parts[0]) as tar:
            data = tar.extractfile(parts[1]).read()
        return data, Path(parts[1]).suffix.lstrip(".")
    if parts[0].endswith(".parquet"):
        import pyarrow.parquet as pq

        row, col = int(parts[1]), parts[2]
        table = pq.read_table(parts[0], columns=[col])
        cell = table.column(col)[row].as_py()
        data = cell["bytes"] if isinstance(cell, dict) else cell
        name = cell.get("path") if isinstance(cell, dict) else None
        ext = Path(name).suffix.lstrip(".") if name else "wav"
        return data, ext or "wav"
    raise ValueError(f"unknown container in {path}")


def decode_source(src: dict, out_wav: str) -> None:
    effects = []
    off, dur = src.get("offset") or 0.0, src.get("duration")
    if off or dur:
        effects += ["trim", f"{off:.4f}"] + ([f"{dur:.4f}"] if dur else [])
    ch = src.get("channel")
    effects += ["remix", "-" if ch is None else str(int(ch) + 1)]
    effects += ["rate", "-v", str(FS)]
    out = ["-b", "16", "-e", "signed-integer", out_wav]
    path = src["path"]
    blob = _source_bytes(path)
    if blob is not None:
        data, ext = blob
        cmd = ["sox", "-t", ext, "-"] + out + effects
        subprocess.run(cmd, input=data, check=True, capture_output=True)
    elif Path(path).suffix in (".mp3", ".m4a", ".webm", ".opus"):
        # compressed formats sox may not read: decode with ffmpeg first
        p1 = subprocess.Popen(
            ["ffmpeg", "-nostdin", "-v", "error", "-i", path, "-f", "wav", "-"],
            stdout=subprocess.PIPE,
        )
        cmd = ["sox", "-t", "wav", "-"] + out + effects
        subprocess.run(cmd, stdin=p1.stdout, check=True, capture_output=True)
        p1.wait()
        if p1.returncode:
            raise RuntimeError(f"ffmpeg failed on {path}")
    elif path.endswith(".sph"):
        p1 = subprocess.Popen(
            ["sph2pipe", "-f", "wav", "-p", path], stdout=subprocess.PIPE
        )
        cmd = ["sox", "-t", "wav", "-"] + out + effects
        subprocess.run(cmd, stdin=p1.stdout, check=True, capture_output=True)
        p1.wait()
        if p1.returncode:
            raise RuntimeError(f"sph2pipe failed on {path}")
    else:
        subprocess.run(["sox", path] + out + effects, check=True, capture_output=True)


def process(rec: dict) -> dict:
    audio = Path(ARGS.audio_dir) / f"{rec['rec']}.flac"
    meta = audio.with_suffix(".json")
    if audio.exists() and meta.exists():
        return json.loads(meta.read_text())
    tmp = Path(tempfile.mkdtemp(dir=ARGS.tmp_dir))
    try:
        wavs = []
        for i, src in enumerate(rec["sources"]):
            w = str(tmp / f"src{i}.wav")
            decode_source(src, w)
            wavs.append(w)
        turns = [tuple(t) for t in rec.get("turns") or []]
        if rec.get("vad"):
            sigs = [sf.read(w, dtype="float32")[0] for w in wavs]
            for i, src in enumerate(rec["sources"]):
                if not src.get("spk"):
                    continue
                refs = [sigs[j] for j in range(len(sigs)) if j != i]
                for s, e in energy_vad(sigs[i], FS, refs=refs):
                    turns.append((src["spk"], s, e))
            del sigs
        part = audio.with_suffix(".part.flac")
        if len(wavs) == 1:
            subprocess.run(["sox", wavs[0], str(part)], check=True, capture_output=True)
        else:
            cmd = ["sox", "-m"] + wavs + [str(part)]
            subprocess.run(cmd, check=True, capture_output=True)
        duration = sf.info(str(part)).frames / FS
        part.rename(audio)
        out = {
            "rec": rec["rec"],
            "wav": str(audio),
            "duration": duration,
            "turns": normalize_turns(turns),
            "uem": rec.get("uem"),
            "exclude": rec.get("exclude"),
        }
        meta.write_text(json.dumps(out))
        return out
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def init_worker(args):
    # Python >= 3.14 starts workers with forkserver, so globals set in main()
    # are not inherited
    global ARGS
    ARGS = args


def safe_process(rec: dict):
    try:
        return process(rec), None
    except Exception:
        return None, (rec["rec"], traceback.format_exc())


def main():
    global ARGS
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("recordings", help="recordings.jsonl from a prep_*.py")
    p.add_argument("outdir", help="Kaldi-style data dir to write")
    p.add_argument("--audio_dir", required=True)
    p.add_argument("--tmp_dir", default=None)
    p.add_argument("--nj", type=int, default=8)
    ARGS = p.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    Path(ARGS.audio_dir).mkdir(parents=True, exist_ok=True)
    recs = list(read_jsonl(ARGS.recordings))
    done, failed = [], []
    with Pool(ARGS.nj, initializer=init_worker, initargs=(ARGS,)) as pool:
        for i, (res, err) in enumerate(pool.imap_unordered(safe_process, recs), 1):
            if err:
                failed.append(err)
                logging.warning("failed %s\n%s", *err)
            else:
                done.append(res)
            if i % 50 == 0 or i == len(recs):
                logging.info("%d/%d recordings (%d failed)", i, len(recs), len(failed))
    write_kaldi_dir(ARGS.outdir, done)
    excl = [
        f"{r['rec']} {s:.3f} {e:.3f}"
        for r in sorted(done, key=lambda r: r["rec"])
        for s, e in r.get("exclude") or []
    ]
    if excl:
        Path(ARGS.outdir, "exclude").write_text("\n".join(excl) + "\n")
    write_jsonl(str(Path(ARGS.outdir) / "recordings.done.jsonl"), done)
    if failed:
        Path(ARGS.outdir, "failed.txt").write_text(
            "".join(f"{k}\n{tb}\n" for k, tb in failed)
        )
        logging.error(
            "%d recordings failed, see %s/failed.txt", len(failed), ARGS.outdir
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
