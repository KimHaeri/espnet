#!/usr/bin/env bash
# Multi-corpus diarization data preparation.
#
# Stage 1: per data set, describe the recordings (local/prep_*.py ->
#          data/<set>/recordings.jsonl) and write 8 kHz mono audio plus a
#          recording-level data dir (local/materialize.py -> data/<set>).
# Stage 2: cut the training sets and a sample of the dev sets into chunks
#          (local/make_chunks.py) -> data/train, data/valid; each eval set is
#          chunked into data/<set>_chunk as well.
#
# Corpus roots come from db.sh. See local/CORPORA.md for what is done to
# each corpus.
set -euo pipefail

log() {
    local fname=${BASH_SOURCE[1]##*/}
    echo -e "$(date '+%Y-%m-%dT%H:%M:%S') (${fname}:${BASH_LINENO[0]}:${FUNCNAME[1]}) $*"
}

stage=1
stop_stage=2
nj=16
audio_dir=data_audio      # 8 kHz recording-level audio
train_sets="ami_train icsi chime6_train notsofar1_train kallaama npsc_train openyap otospeech141 otospeech_task20 otospeech_task_v2 spice spjallromur egocom multi_tpc indic libmeet_clean harpervalley nb_samtale datahive perit simsamu primock57 maptask turnturk"
dev_sets="dipco_dev ami_dev chime6_dev notsofar1_dev npsc_dev alimeeting_dev voxconverse_dev dihard3_dev seamless_dev msp_dev"
eval_sets="dipco_eval ami_eval chime6_eval notsofar1_eval npsc_eval alimeeting_eval voxconverse_eval dihard3_eval seamless_eval msp_eval"
sets=             # stage 1: prepare only these sets (default: all)
chunk_sec=30
min_chunk_sec=10
max_spk=8
valid_hours_per_set=1.0

. ./db.sh
. ./path.sh
. utils/parse_options.sh

: "${AMI:=downloads/ami}" "${ICSI:=downloads/icsi}" "${CHIME6:=downloads/chime6}"
: "${DIPCO:=downloads/dipco}" "${NOTSOFAR1:=downloads/notsofar1}"
: "${KALLAAMA:=downloads/kallaama}" "${NPSC:=downloads/norwegian_parliamentary}"
: "${OPENYAP:=downloads/OpenYAP-1K}" "${SPICE:=downloads/spice}"
: "${OTOSPEECH141:=downloads/otoSpeech-full-duplex-processed-141h}"
: "${OTOSPEECH_TASK20:=downloads/otoSpeech-full-duplex-task-oriented-20h}"
: "${OTOSPEECH_TASK_V2:=downloads/otoSpeech-full-duplex-task-oriented-v2}"
: "${SPJALLROMUR:=downloads/spjallromur}" "${EGOCOM:=downloads/egocom}"
: "${MULTI_TPC:=downloads/multi_tpc}" "${INDIC_MULTISPK:=downloads/Indic-High-Fidelity-MultiSpeaker-ASR}"
: "${LIBRI_MEETINGS:=downloads/librispeech_meetings_2k}"
: "${HARPERVALLEY_FULL:=downloads/harper_valley/gridspace-stanford-harper-valley}"
: "${NB_SAMTALE:=downloads/nb_samtale/original/nb_samtale}"
: "${DATAHIVE:=downloads/datahive_conversations_sample}"
: "${PERIT:=downloads/perit_duplex_support_en/perit-duplex-support-en}"
: "${SIMSAMU:=downloads/simsamu/simsamu}" "${PRIMOCK57:=downloads/primock57/github}"
: "${MAPTASK:=downloads/maptask}" "${TURNTURK:=downloads/real_turnturk/Real-TurnTurk}"
: "${DIARIZEN:=downloads/DiariZen_Compound_dataset}"
: "${SEAMLESS_INTERACTION:=downloads/seamless_interaction}"
: "${MSP_CONVERSATION:=downloads/msp_conversation}"

# describe <set> <recordings.jsonl>: run the prep script of one data set
describe() {
    local set=$1 out=$2 L=local
    case "${set}" in
        ami_train|ami_dev|ami_eval) python3 $L/prep_ami.py "${AMI}" "${set#ami_}" "${out}" ;;
        icsi) python3 $L/prep_icsi.py "${ICSI}" "${out}" ;;
        chime6_*) python3 $L/prep_dinner.py chime6 "${CHIME6}" "${set#chime6_}" "${out}" ;;
        dipco_*) python3 $L/prep_dinner.py dipco "${DIPCO}" "${set#dipco_}" "${out}" ;;
        notsofar1_*) python3 $L/prep_notsofar.py "${NOTSOFAR1}" "${set#notsofar1_}" "${out}" ;;
        kallaama) python3 $L/prep_kallaama.py "${KALLAAMA}/clean_dataset_ready4release" "${out}" ;;
        # NPSC calls its development set "eval" and its test set "test"
        npsc_train) python3 $L/prep_npsc.py "${NPSC}" train "${out}" ;;
        npsc_dev) python3 $L/prep_npsc.py "${NPSC}" eval "${out}" ;;
        npsc_eval) python3 $L/prep_npsc.py "${NPSC}" test "${out}" ;;
        openyap) python3 $L/prep_openyap.py "${OPENYAP}" "${out}" ;;
        otospeech141) python3 $L/prep_otospeech.py "${OTOSPEECH141}" oto141 "${out}" ;;
        otospeech_task20) python3 $L/prep_otospeech.py "${OTOSPEECH_TASK20}" ototask20 "${out}" ;;
        otospeech_task_v2) python3 $L/prep_otospeech.py "${OTOSPEECH_TASK_V2}" ototaskv2 "${out}" ;;
        spice) python3 $L/prep_spice.py "${SPICE}" "${out}" ;;
        spjallromur) python3 $L/prep_spjallromur.py "${SPJALLROMUR}" "${out}" ;;
        egocom) python3 $L/prep_egocom.py "${EGOCOM}" "${out}" ;;
        multi_tpc) python3 $L/prep_multi_tpc.py "${MULTI_TPC}/Data" "${out}" ;;
        indic) python3 $L/prep_indic.py "${INDIC_MULTISPK}" "${out}" ;;
        libmeet_clean) python3 $L/prep_libri_meetings.py "${LIBRI_MEETINGS}" "${out}" ;;
        harpervalley) python3 $L/prep_harpervalley.py "${HARPERVALLEY_FULL}" "${out}" ;;
        # full recordings rebuilt from the released segments
        nb_samtale) python3 $L/prep_nb_samtale.py "${NB_SAMTALE}" "${audio_dir}/nb_samtale_rebuilt" "${out}" ;;
        datahive) python3 $L/prep_datahive.py "${DATAHIVE}" "${out}" ;;
        perit) python3 $L/prep_perit.py "${PERIT}" "${out}" ;;
        simsamu) python3 $L/prep_simsamu.py "${SIMSAMU}" "${out}" ;;
        primock57) python3 $L/prep_primock57.py "${PRIMOCK57}" "${out}" ;;
        maptask) python3 $L/prep_maptask.py "${MAPTASK}" "${out}" ;;
        turnturk) python3 $L/prep_turnturk.py "${TURNTURK}" "${out}" ;;
        # official dev sets rebuilt from DiariZen's train + dev
        alimeeting_dev) python3 $L/prep_diarizen.py "${DIARIZEN}" AliMeeting dev alimeeting "${out}" ;;
        alimeeting_eval) python3 $L/prep_diarizen.py "${DIARIZEN}" AliMeeting test alimeeting "${out}" ;;
        voxconverse_dev) python3 $L/prep_diarizen.py "${DIARIZEN}" VoxConverse train,dev voxconverse "${out}" ;;
        voxconverse_eval) python3 $L/prep_diarizen.py "${DIARIZEN}" VoxConverse test voxconverse "${out}" ;;
        dihard3_dev) python3 $L/prep_diarizen.py "${DIARIZEN}" DIHARD3 train,dev dihard3 "${out}" --prefix DH_DEV ;;
        dihard3_eval) python3 $L/prep_diarizen.py "${DIARIZEN}" DIHARD3 test dihard3 "${out}" ;;
        seamless_dev) python3 $L/prep_seamless.py "${SEAMLESS_INTERACTION}" dev "${out}" ;;
        seamless_eval) python3 $L/prep_seamless.py "${SEAMLESS_INTERACTION}" test "${out}" ;;
        msp_dev) python3 $L/prep_msp_conversation.py "${MSP_CONVERSATION}" Development "${out}" ;;
        msp_eval) python3 $L/prep_msp_conversation.py "${MSP_CONVERSATION}" Test "${out}" ;;
        *) log "unknown data set: ${set}"; return 1 ;;
    esac
}

# Commands are chained with && because errexit is ignored in a function
# called as "prepare_set ... || ...".
prepare_set() {
    local set=$1
    mkdir -p "data/${set}" \
    && describe "${set}" "data/${set}/recordings.jsonl" \
    && python3 local/materialize.py "data/${set}/recordings.jsonl" "data/${set}" \
        --audio_dir "${audio_dir}/${set}" --nj "${nj}" \
    && utils/utt2spk_to_spk2utt.pl "data/${set}/utt2spk" > "data/${set}/spk2utt" \
    && utils/validate_data_dir.sh --no-feats --no-text "data/${set}" \
    && python3 local/data_stats.py "data/${set}" > "data/${set}/stats.txt" \
    && touch "data/${set}/.done"
}

if [ ${stage} -le 1 ] && [ ${stop_stage} -ge 1 ]; then
    failed=
    for set in ${sets:-${train_sets} ${dev_sets} ${eval_sets}}; do
        if [ -f "data/${set}/.done" ]; then
            log "skip ${set}: already prepared"
            continue
        fi
        log "Stage 1: ${set}"
        # one failing corpus does not stop the others; rerun to retry it
        prepare_set "${set}" || { log "FAILED: ${set}"; failed+=" ${set}"; }
    done
    if [ -n "${failed}" ]; then
        log "Stage 1 failed for:${failed}"
        exit 1
    fi
fi

if [ ${stage} -le 2 ] && [ ${stop_stage} -ge 2 ]; then
    log "Stage 2: chunk ${chunk_sec}s"
    _dirs() { for s in "$@"; do [ -f "data/${s}/.done" ] && echo "data/${s}"; done; }
    _opts="--chunk_sec ${chunk_sec} --min_chunk_sec ${min_chunk_sec} --max_spk ${max_spk}"
    # shellcheck disable=SC2046,SC2086
    python3 local/make_chunks.py $(_dirs ${train_sets}) data/train ${_opts}
    # shellcheck disable=SC2046,SC2086
    python3 local/make_chunks.py $(_dirs ${dev_sets}) data/valid ${_opts} \
        --max_hours_per_dir "${valid_hours_per_set}"
    for s in ${dev_sets} ${eval_sets}; do
        [ -f "data/${s}/.done" ] || continue
        # shellcheck disable=SC2086
        python3 local/make_chunks.py "data/${s}" "data/${s}_chunk" ${_opts}
    done
    for d in data/train data/valid; do
        utils/validate_data_dir.sh --no-feats --no-text "${d}"
    done
fi
log "Successfully finished. [elapsed=${SECONDS}s]"
