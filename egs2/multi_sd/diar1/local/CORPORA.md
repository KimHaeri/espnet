# Per-corpus handling

This file records what `local/data.sh` does to each corpus beyond the common
steps. Corpus roots are the variables at the top of `local/data.sh`, set in
`db.sh` or as `downloads/<name>` symlinks.

## Common steps (every corpus)

- **Output.** Audio becomes 8 kHz, 16-bit, mono FLAC (`local/materialize.py`,
  sox `rate -v`). The data dir is recording-level: `wav.scp`, `segments` +
  `utt2spk` (speaker turns), `rttm`, `reco2dur`, and `uem` where coverage is
  partial.
- **Several sources.** When a recording has more than one source (one file or
  channel per speaker), they are mixed with `sox -m`, which scales each input
  by 1/N.
- **Ids.** Recording ids carry a corpus prefix. Speaker ids are local to the
  recording (`<rec>_<spk>`).
- **Speaker turns.** Turns of the same speaker that overlap are merged. When
  turns come from word timestamps, words of one speaker are joined across
  pauses of at most 0.3 s (`--merge_gap`).
- **Training chunks.** Training data are 30 s chunks inside the UEM
  (`local/make_chunks.py`). A tail of at least 10 s is kept. Chunks are
  dropped when they:
  - touch an `exclude` region,
  - have no speaker, or
  - have more than 8 speakers.

  `utt2category` holds the speaker count of each chunk.
- **Validation.** Up to 1 h of chunks from each dev set, sampled with seed 0.
- **Energy VAD** (`local/energy_vad.py`; used only where noted below).
  - Frames are 25 ms with a 10 ms hop.
  - A frame is speech when its log energy is above
    `p10 + max(6 dB, 0.35 * (p95 - p10))` of the channel.
  - Frames where another speaker's channel is more than 6 dB louder are
    rejected as cross-talk.
  - Smoothing: 11-frame median filter, 0.1 s hangover, gaps under 0.3 s
    joined, segments under 0.3 s dropped.

## Training data

### AMI (`ami_train`)

- **Audio.** `Array1-01` far-field channel.
- **Turns.** `annotations/segments/<mtg>.<spk>.segments.xml`
  (`transcriber_start` / `transcriber_end`).
- **Split.** Official Full-ASR train list (`egs2/ami/asr1/local/split_train.orig`).
- **Skipped.** IS1003b and IS1007d have no array audio. IB4005 is in that
  list but is dropped: its speakers MIO036 and FIE038 also appear in dev
  meetings (IB4001-IB4004, IS1008a-d; `corpusResources/meetings.xml`), and
  the BUT and pyannote AMI diarization setups leave it out as well.
- **Licence.** CC BY 4.0.

### ICSI (`icsi`)

- **Audio.** The first tabletop channel present (`chanA`..`chanF`,
  shorten-compressed SPHERE, decoded by `sph2pipe`).
- **Turns.** `ICSI/Segments/*.segs.xml` inside `ICSI_core_NXT.zip`, read from
  the zip without extracting it.
- **Split.** All meetings (no official split).
- **Licence.** CC BY 4.0.

### CHiME-6 (`chime6_train`)

- **Audio.** `U01.CH1`. When U01 is missing, the first array present is used
  (S05 and S22 each lack one array).
- **Turns.** Transcription JSON (`start_time` / `end_time`, one time per segment).
- **UEM.** First to last segment: the recordings start before the party.
- **Split.** Official train.
- **Note.** The plan lists CHiME-6 as CC BY-SA 4.0; check the copy's licence
  file (see the sd_dataset_db note).

### NOTSOFAR-1 (`notsofar1_train`)

- **Audio.** The first single-channel device of each meeting (`sc_*/ch0.wav`).
- **Turns.** `gt_transcription.json` (`speaker_id`, `start_time`, `end_time`).
- **Split.** `train_set/240501.1_train`.
- **Licence.** CC BY 4.0.

### Kallaama (`kallaama`)

- **Audio.** Mono wav of each radio programme (Wolof, Pulaar, Sereer).
- **Turns.** Transcriber `.trs` `<Turn>` elements.
  - The revised copy in `checked_transcriptions/<N>/` is used when it exists.
  - A turn naming several speakers (`speaker="spk1 spk2"`) marks all of them
    active for the whole turn.
  - Turns are whole speaker turns, so short pauses inside a turn count as
    speech.
- **Split.** All files (no official split).
- **Licence.** CC BY 4.0.

### NPSC (`npsc_train`)

- **Audio.** Full meeting recording, 48 kHz stereo, downmixed.
- **Turns.** Transcribed sentences (`*_sentence_data.json`, global
  `speaker_id`).
- **UEM.** First to last sentence; the meetings start and end with
  untranscribed audio.
- **Split.** `data_split == "train"`.
- **Licence.** CC0 1.0.

### OpenYAP-1K (`openyap`)

- **Audio.** `speaker_a.flac` + `speaker_b.flac` (one speaker each, 48 kHz),
  mixed.
- **Turns.** Word timestamps of `speaker_?_transcript.json`, joined into turns.
- **Split.** All conversations.
- **Licence.** Signed agreement, internal use only. Never redistribute audio,
  data dirs or dumps.

### otoSpeech: full-duplex 141h, task-oriented 20h, task-oriented v2 (`otospeech141`, `otospeech_task20`, `otospeech_task_v2`)

- **Audio.** Stereo FLAC with one speaker per channel, read straight from the
  WebDataset tar shards (`data/train/*.tar`). The two channels are mixed.
- **Turns.** Energy VAD on each speaker's channel, with the other channel as
  the cross-talk reference. These sets have no speech timing, so the labels
  are approximate.
- **Exclude.** `redacted_segments` become exclude regions; chunks touching them
  are dropped.
- **Licence.**
  - All three sets are CC BY 4.0.
  - task-oriented v2's `export-manifest.json` says `release_eligible: false`
    (pending privacy and redistribution review). Internal use only.

### SpiCE (`spice`)

- **Section kept.** Only the `interview` interval of the `task` tier. The
  sentence reading and the storyboard narration have a single talker.
- **Participant.** Left channel; turns are the non-empty intervals of the
  `utterance` tier (TextGrids are UTF-16).
- **Interviewer.** Right channel; turns come from energy VAD with the
  participant channel as the cross-talk reference. The interviewer was never
  transcribed.
- **Skipped.** The one mono file (participant only).
- **Licence.** CC BY 4.0.

### Spjallromur (`spjallromur`)

- **Turns.** The re-aligned release's ready-made RTTM
  (`github/combined/<id>/combined_<id>.rttm`, 46 full conversations).
- **Audio.** The two speaker wavs, mixed (as the release's
  `convert2diarization.py` does).
- **Split.** The ASR splits are per speaker side, so all conversations are
  used for training.
- **Licence.** CC BY 4.0.

### EgoCom (`egocom`)

- **Audio.** Each conversation part was filmed by 2-3 wearers whose recordings
  are synchronised views. Only the lowest-numbered wearer's file is used, with
  its two channels averaged.
- **Turns.** Word timestamps in `metadata/ground_truth_transcriptions.csv`,
  joined into turns. Rows without times are skipped.
- **Split.** All parts.
- **Licence.** MIT.

### Multi-TPC (`multi_tpc`)

- **Audio.** The three participants' recordings (48 kHz stereo, channels
  averaged), mixed.
- **Turns.** Each participant's word CSV, joined into turns.
- **Timeline.** The three recordings are assumed to share one timeline; this
  is not stated in the corpus documentation.
- **Licence.** CC BY 4.0.

### Indic High-Fidelity MultiSpeaker (`indic`)

- **Audio.** Mono mixed audio, read from the parquet files
  (`<parquet>::<row>::audio`).
- **Turns.** `transcript_json` segments (HH:MM:SS.mmm).
- **Split.** All recordings.
- **Licence.** CC BY 4.0.

### LibriSpeech simulated meetings (`libmeet_clean`)

- **Source.** Lab simulation, **clean condition only** (`out/clean/shard*/`),
  3-8 speakers per meeting.
- **Turns.** The simulation's RTTM per meeting.
- **Storage.** It lives on /scratch, which can be purged. Stage 1 writes our
  own 8 kHz copy.
- **Licence.** LibriSpeech CC BY 4.0.

### Harper Valley (`harpervalley`)

- **Source.** The full Gridspace-Stanford release, downloaded from GitHub.
- **Audio.** Agent and caller wavs (8 kHz), mixed.
- **Turns.** Transcript segments (`start_ms`, `duration_ms`, `speaker_role`).
- **Split.** All calls.
- **Licence.** CC BY 4.0.

### NB Samtale (`nb_samtale`)

- **Source.** Språkbanken releases NB Samtale only as cut segments. The
  original `nb_samtale.zip` matches the HF copy: 12,080 segment wavs plus
  metadata, with no full recordings.
- **Rebuilt recordings** (`local/prep_nb_samtale.py`). Every segment is placed
  at its source position: train, dev, test, and also `background_noise`, which
  fills music and noise stretches.
  - Overlapping segments: the samples of the first one placed are kept. They
    are cut from the same source, so either copy is the source audio.
  - Positions that no segment covers stay digital silence. The coverage of
    each recording is printed in the stage-1 log.
- **Turns.** The transcribed segments (`metadata.jsonl`, global speaker ids).
- **UEM.** First to last segment.
- **Split.** All splits are used for training (user decision). The published
  splits are not session-disjoint anyway.
- **Licence.** CC0 1.0.

### DataHive conversation samples (`datahive`)

- **Audio.** Stereo MP3, 48 kHz: caller on the left channel, callee on the
  right, on a shared timeline. Decoded with ffmpeg.
- **Turns.** Energy VAD per channel. No transcripts are released.
- **Files used.**
  - All `*-conversations-sample/preview/*.mp3`, de-duplicated by file name:
    the per-language repos repeat the multilingual repo's files.
  - Arabic and Italian exist only in their own repos, so the set is larger
    than the multilingual sample alone.
- **Audio quality.** Lossy twice: Opus capture, then MP3.
- **Licence.** CC BY 4.0.

### Perit duplex support, English (`perit`)

- **Audio.** Stereo wav, one performer per channel. Which channel holds the
  agent varies between files, so speakers are labelled `left` and `right`.
- **Turns.** Energy VAD per channel. There are no time-stamped transcripts.
- **Content.** Scripted role-plays.
- **Licence.** CC BY 4.0.

### Simsamu (`simsamu`)

- **Audio.** Mono 8 kHz AAC (m4a), decoded with ffmpeg. The caller is played
  through a phone speaker into the doctor's microphone.
- **Turns.** The shipped RTTM has `<NA>` as file id and channel, so only the
  onset, duration and speaker fields are read. Speaker labels are roles
  (`medecin`, `patient`, `patient_1`, ...).
- **Licence.** MIT.

### PriMock57 (`primock57`)

- **Audio.** Time-aligned doctor and patient wavs, mixed (as the release's
  `scripts/mix_audio.sh` does).
- **Turns.** The non-empty intervals of each side's TextGrid. They are
  utterance-level, so turn boundaries are coarse.
- **Licence.** CC BY 4.0.

### HCRC Map Task (`maptask`)

- **Audio.** 20 kHz stereo `mix.wav` per dialogue, channels averaged. It is
  not documented which channel holds the giver, and averaging makes that
  irrelevant.
- **Turns.** Giver and follower `<tu>` words (NXT v2.1 `timed-units`), joined
  into turns.
- **Licence.** Conflicting statements. The site manifest and download script
  say CC BY 4.0; the v2.1 annotation README says CC BY-NC-SA 2.5. To be
  confirmed.

### Real-TurnTurk (`turnturk`)

- **Audio.** One Opus webm per participant (video calls), mixed.
- **Turns.** The corpus's frame-level speech activity per person (62.5 ms
  grid), with active frames joined into turns.
- **Licence.** Apache 2.0.

### Not included

- **MSP-Conversation.** Dev/eval only.
- **Ego4D.** Not used for now.
- **Kenya-PH.** VAD clips with no shared clock between tracks.
- **Fearless Steps.** Not on storage.

## Label checks

- **Energy VAD against human labels.**
  - On 30 SpiCE files, the VAD was run on the transcribed participant channel
    and compared with the TextGrid utterance tier (`local/check_vad.py`,
    10 ms frames).
  - Result: precision 0.990, recall 0.889, miss 11.1 % and false alarm 0.9 %
    of reference speech.
  - The VAD-derived labels (otoSpeech, DataHive, Perit, SpiCE interviewer)
    therefore tend to miss quiet speech rather than invent speech.
- **Multi-TPC timeline.** The corpus's own common-clock activity table
  (`AudioGazeGBack`, Session 1 of 01-28-2022) has each participant's first
  speech at 1.07-1.18 s. That matches the word timestamps used here, so the
  three recordings share one timeline.
  - The table gives 0.33 overlap of speech for that session.
  - The word-based turns give a higher overall figure (see the table below),
    because pauses of up to 0.3 s are joined.

## Dev / eval data

- **DiPCo (`dipco_dev`, `dipco_eval`).** `U01.CH1`. DiPCo gives a time per
  device, and the U01 one is used. UEM: first to last segment.
- **AMI (`ami_dev`, `ami_eval`).** As for training, with the Full-ASR dev and
  eval lists.
- **CHiME-6 (`chime6_dev`, `chime6_eval`).** As for training.
- **NOTSOFAR-1 (`notsofar1_dev`, `notsofar1_eval`).** `dev_set/240415.2_dev_with_GT`
  and `eval_set/240629.1_eval_small_with_GT`.
- **NPSC (`npsc_dev`, `npsc_eval`).** The NPSC documentation calls the dev set
  "eval" and the test set "test". They map to `npsc_dev` and `npsc_eval`.
- **AliMeeting, VoxConverse and DIHARD III (`*_dev`, `*_eval`).**
  - On the lab storage these three exist only inside DiariZen_Compound_dataset.
  - DiariZen moved part of the official VoxConverse and DIHARD III dev sets
    into its "train". The official dev sets are rebuilt from DiariZen's
    train + dev (DIHARD III: `DH_DEV_*` ids only).
  - AliMeeting dev is the 8-session Eval set (DiariZen dev); AliMeeting eval is
    the 20-session Test set.
  - Far-field array files use channel 0.
  - DiariZen's UEMs span each whole file, so they are probably not the official
    DIHARD III UEMs.
  - DIHARD III is LDC: internal use only.
- **Seamless Interaction (`seamless_dev`, `seamless_eval`).** Improvised
  conversations, one participant per channel, averaged. Turns are the corpus's
  own per-channel VAD segments (`metadata:vad`). CC BY-NC 4.0, evaluation only.
- **MSP-Conversation (`msp_dev`, `msp_eval`).** Development and Test
  partitions.
  - Speaker numbers are consistent only within a part, so each part is its own
    recording.
  - A part is cut from the conversation wav at
    `part_start - conversation_start`.
  - Research-only agreement, internal use.
- **Excluded from dev/eval.** These have no recorded dev/eval split in
  sd_dataset_db: AISHELL-4 (test only), SpokenWOZ, RT-03, HUB5, CALLHOME,
  AISHELL-5, Earnings-22, Expresso.

## Produced data

`data/<set>/stats.txt` (`local/data_stats.py`) is written by stage 1. The table
below is filled from those files.

| set | recordings | audio h | scored h | speech h | overlap / speech | speakers per recording |
|---|---|---|---|---|---|---|
| `alimeeting_dev` | 8 | 4.21 | 4.21 | 3.88 | 0.216 | {2: 3, 3: 1, 4: 4} |
| `alimeeting_eval` | 20 | 10.72 | 10.72 | 9.86 | 0.202 | {2: 8, 3: 4, 4: 8} |
| `ami_dev` | 18 | 9.67 | 9.67 | 7.94 | 0.202 | {4: 18} |
| `ami_eval` | 16 | 9.06 | 9.06 | 7.55 | 0.194 | {3: 1, 4: 15} |
| `ami_train` | 135 | 80.21 | 80.21 | 68.17 | 0.193 | {3: 4, 4: 128, 5: 3} |
| `chime6_dev` | 2 | 4.46 | 4.43 | 3.88 | 0.501 | {4: 2} |
| `chime6_eval` | 2 | 5.21 | 5.19 | 4.10 | 0.339 | {4: 2} |
| `chime6_train` | 16 | 40.51 | 39.82 | 31.01 | 0.319 | {4: 16} |
| `datahive` | 102 | 25.41 | 25.41 | 22.62 | 0.143 | {2: 102} |
| `dihard3_dev` | 254 | 34.15 | 34.15 | 27.26 | 0.107 | {1: 16, 2: 157, 3: 16, 4: 16, 5: 12, 6: 12, 7: 12, 8: 10, 9: 1, 10: 2} |
| `dihard3_eval` | 259 | 33.01 | 33.01 | 26.11 | 0.094 | {1: 15, 2: 159, 3: 27, 4: 18, 5: 11, 6: 10, 7: 10, 8: 5, 9: 4} |
| `dipco_dev` | 5 | 2.73 | 2.72 | 2.52 | 0.279 | {4: 5} |
| `dipco_eval` | 5 | 2.60 | 2.60 | 2.36 | 0.275 | {4: 5} |
| `egocom` | 63 | 13.70 | 13.70 | 8.40 | 0.001 | {1: 1, 3: 62} |
| `harpervalley` | 1446 | 23.94 | 23.94 | 11.46 | 0.049 | {2: 1446} |
| `icsi` | 75 | 71.69 | 71.69 | 60.95 | 0.187 | {3: 1, 4: 3, 5: 14, 6: 21, 7: 18, 8: 10, 9: 6, 10: 2} |
| `indic` | 37 | 8.35 | 8.35 | 8.09 | 0.000 | {1: 1, 2: 36} |
| `kallaama` | 337 | 124.82 | 124.82 | 123.13 | 0.041 | {1: 40, 2: 122, 3: 63, 4: 37, 5: 13, 6: 22, 7: 15, 8: 5, 9: 7, 10: 4, 11: 2, 12: 2, 13: 2, 14: 1, 16: 2} |
| `libmeet_clean` | 3000 | 501.72 | 501.72 | 416.06 | 0.177 | {3: 522, 4: 499, 5: 502, 6: 487, 7: 490, 8: 500} |
| `maptask` | 128 | 14.31 | 14.31 | 9.43 | 0.053 | {2: 128} |
| `msp_dev` | 104 | 8.96 | 8.96 | 7.69 | 0.027 | {1: 5, 2: 42, 3: 29, 4: 17, 5: 7, 6: 3, 11: 1} |
| `msp_eval` | 162 | 13.85 | 13.85 | 11.81 | 0.051 | {1: 14, 2: 133, 3: 12, 5: 3} |
| `multi_tpc` | 23 | 4.71 | 4.71 | 4.25 | 0.512 | {3: 23} |
| `nb_samtale` | 35 | 24.46 | 24.36 | 23.22 | 0.034 | {2: 5, 3: 6, 4: 17, 5: 3, 6: 3, 9: 1} |
| `notsofar1_dev` | 33 | 3.45 | 3.45 | 2.88 | 0.198 | {4: 15, 5: 13, 6: 5} |
| `notsofar1_eval` | 80 | 8.33 | 8.33 | 7.78 | 0.314 | {3: 9, 4: 26, 5: 30, 6: 7, 7: 8} |
| `notsofar1_train` | 108 | 11.14 | 11.14 | 10.38 | 0.335 | {4: 26, 5: 31, 6: 33, 7: 10, 8: 8} |
| `npsc_dev` | 5 | 14.69 | 14.17 | 13.14 | 0.000 | {12: 1, 14: 1, 17: 1, 35: 1, 43: 1} |
| `npsc_eval` | 4 | 13.09 | 12.71 | 12.32 | 0.000 | {9: 1, 30: 1, 41: 1, 50: 1} |
| `npsc_train` | 32 | 112.55 | 109.23 | 100.32 | 0.000 | {3: 1, 8: 1, 11: 1, 12: 1, 15: 1, 16: 2, 17: 1, 20: 1, 24: 1, 25: 1, 26: 1, 27: 1, 30: 1, 31: 1, 35: 1, 36: 2, 37: 1, 40: 3, 43: 1, 44: 1, 48: 1, 49: 2, 50: 2, 52: 1, 54: 1, 55: 1} |
| `openyap` | 865 | 518.04 | 518.04 | 410.83 | 0.090 | {2: 865} |
| `otospeech141` | 538 | 141.56 | 141.56 | 120.77 | 0.082 | {2: 538} |
| `otospeech_task20` | 58 | 20.01 | 20.01 | 17.50 | 0.102 | {2: 58} |
| `otospeech_task_v2` | 47 | 17.38 | 17.38 | 15.59 | 0.100 | {2: 47} |
| `perit` | 45 | 5.10 | 5.10 | 4.78 | 0.042 | {2: 45} |
| `primock57` | 57 | 8.64 | 8.64 | 7.92 | 0.063 | {2: 57} |
| `seamless_dev` | 275 | 18.22 | 18.22 | 14.07 | 0.069 | {1: 3, 2: 272} |
| `seamless_eval` | 194 | 13.45 | 13.45 | 10.98 | 0.063 | {1: 4, 2: 190} |
| `simsamu` | 61 | 3.24 | 3.24 | 2.61 | 0.000 | {2: 60, 3: 1} |
| `spice` | 67 | 27.71 | 27.71 | 26.04 | 0.138 | {2: 67} |
| `spjallromur` | 46 | 18.23 | 18.23 | 15.69 | 0.044 | {2: 46} |
| `turnturk` | 6 | 1.94 | 1.94 | 1.72 | 0.079 | {2: 6} |
| `voxconverse_dev` | 216 | 20.30 | 20.30 | 18.91 | 0.037 | {1: 22, 2: 44, 3: 35, 4: 24, 5: 31, 6: 17, 7: 12, 8: 11, 9: 4, 10: 6, 11: 3, 12: 3, 15: 2, 17: 1, 20: 1} |
| `voxconverse_eval` | 232 | 43.53 | 43.53 | 38.98 | 0.031 | {1: 15, 2: 31, 3: 18, 4: 22, 5: 13, 6: 18, 7: 32, 8: 22, 9: 15, 10: 10, 11: 12, 12: 6, 13: 5, 14: 3, 15: 6, 17: 1, 18: 1, 19: 1, 21: 1} |

Notes on the table:

- **OpenYAP.** 865 conversations give 518 h of mixed audio, while sd_dataset_db
  reports 1,000 h (the source's own figure). It may count both speaker files,
  but this is not verified. One conversation dir lacked audio or a transcript
  and was skipped.
- **Turn granularity.** Kallaama (whole Transcriber turns) and NPSC (sentence
  level) give speech ratios near 1 and no overlap. Their turns include pauses,
  and NPSC never marks overlapping talkers.
- **Dropped recordings.** Recordings without any turn are dropped and listed in
  the stage-1 log:
  - 20 Seamless dev and 19 Seamless eval conversations with empty VAD lists;
  - 3 Kallaama files with no speaker turns.
