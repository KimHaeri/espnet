"""Energy-based voice activity detection for one-speaker-per-channel audio.

Used for corpora that record each speaker on their own channel but give no
speech timing (otoSpeech, the SpiCE interviewer channel). The labels are
approximate: a frame is speech when its log energy is well above the
channel's noise floor and, if a reference channel is given, not much quieter
than that channel (to reject cross-talk picked up from the other speaker).
"""

from typing import List, Optional, Tuple

import numpy as np
from scipy.ndimage import median_filter


def frame_log_energy(x: np.ndarray, fs: int, win: float, hop: float) -> np.ndarray:
    n_win, n_hop = int(win * fs), int(hop * fs)
    if len(x) < n_win:
        return np.zeros(0, dtype=np.float32)
    n = 1 + (len(x) - n_win) // n_hop
    # strided view: (n, n_win), no copy
    frames = np.lib.stride_tricks.as_strided(
        x, shape=(n, n_win), strides=(x.strides[0] * n_hop, x.strides[0])
    )
    power = np.mean(frames.astype(np.float64) ** 2, axis=1)
    return (10 * np.log10(power + 1e-12)).astype(np.float32)


def mask_to_intervals(mask: np.ndarray, hop: float) -> List[Tuple[float, float]]:
    if mask.size == 0:
        return []
    padded = np.concatenate([[0], mask.astype(np.int8), [0]])
    edges = np.flatnonzero(np.diff(padded))
    return [(s * hop, e * hop) for s, e in zip(edges[0::2], edges[1::2])]


def energy_vad(
    x: np.ndarray,
    fs: int,
    refs: Optional[List[np.ndarray]] = None,
    win: float = 0.025,
    hop: float = 0.010,
    floor_pct: float = 10.0,
    peak_pct: float = 95.0,
    rel_threshold: float = 0.35,
    min_margin_db: float = 6.0,
    crosstalk_db: float = 6.0,
    median_frames: int = 11,
    hangover: float = 0.10,
    min_speech: float = 0.30,
    merge_gap: float = 0.30,
) -> List[Tuple[float, float]]:
    """Return speech intervals (seconds) of ``x``.

    threshold = floor + max(min_margin_db, rel_threshold * (peak - floor)),
    with floor/peak the ``floor_pct``/``peak_pct`` percentiles of the frame
    log energy. With ``refs`` (the other speakers' channels), frames where a
    reference is more than ``crosstalk_db`` louder are not speech.
    """
    e = frame_log_energy(x, fs, win, hop)
    if e.size == 0:
        return []
    floor, peak = np.percentile(e, [floor_pct, peak_pct])
    thr = floor + max(min_margin_db, rel_threshold * (peak - floor))
    mask = e > thr
    for ref in refs or []:
        er = frame_log_energy(ref, fs, win, hop)
        n = min(len(e), len(er))
        mask[:n] &= e[:n] >= er[:n] - crosstalk_db
    if median_frames > 1:
        mask = median_filter(mask.astype(np.uint8), size=median_frames) > 0
    ivs = mask_to_intervals(mask, hop)
    total = len(x) / fs
    ivs = [(max(0.0, s - hangover), min(total, e + win + hangover)) for s, e in ivs]
    merged: List[List[float]] = []
    for s, e in ivs:
        if merged and s <= merged[-1][1] + merge_gap:
            merged[-1][1] = max(merged[-1][1], e)
        else:
            merged.append([s, e])
    return [(s, e) for s, e in merged if e - s >= min_speech]
