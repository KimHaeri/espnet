#!/usr/bin/env bash
# Set bash to 'debug' mode, it will exit on :
# -e 'error', -u 'undefined variable', -o ... 'error in pipeline', -x 'print commands',
set -e
set -u
set -o pipefail

train_set="train"
valid_set="valid"
# chunked eval sets (local/data.sh stage 2)
test_sets="dipco_eval_chunk ami_eval_chunk chime6_eval_chunk notsofar1_eval_chunk npsc_eval_chunk alimeeting_eval_chunk voxconverse_eval_chunk dihard3_eval_chunk seamless_eval_chunk msp_eval_chunk"

train_config="conf/train_diar_eda.yaml"
decode_config="conf/decode_diar_eda.yaml"

# num_spk only sizes the unused linear decoder of an EDA model;
# chunks have 1..max_spk speakers (local/data.sh --max_spk)
./diar.sh \
    --collar 0.0 \
    --fs 8k \
    --train_set "${train_set}" \
    --valid_set "${valid_set}" \
    --test_sets "${test_sets}" \
    --diar_config "${train_config}" \
    --inference_config "${decode_config}" \
    --diar_speech_fold_length 3000 \
    --num_spk 8 \
    "$@"
