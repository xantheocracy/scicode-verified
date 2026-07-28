#!/bin/bash
# Run the SciCode inspect_ai eval against the CLEANED dataset (cleaned problems + patched targets).
# This is the original run_gpt5_eval.sh re-pointed at eval_clean/ via --data-dir and --h5py-file.
#
# Usage:
#   # set your provider creds first (e.g. OPENROUTER_API_KEY=... for gpt-5 via openrouter)
#   bash eval_clean/run_cleaned_eval.sh                 # run on CLEANED data
#   EVAL_VARIANT=original bash eval_clean/run_cleaned_eval.sh   # run on ORIGINAL data (for comparison)
#
# Override anything via env vars: PYTHON, SERVICE, MODEL_NAME, REASONING, MAX_TOKENS, SPLIT, OUTPUT_DIR.
set -e

ROOT="$(cd "$(dirname "$0")/.." && pwd)"          # repository root
INSPECT_DIR="$ROOT/SciCode/eval/inspect_ai"

# --- pick which dataset/targets to score against ---
if [ "${EVAL_VARIANT:-cleaned}" = "original" ]; then
  DATA_DIR="$ROOT/eval_clean/data_original"
  H5="$ROOT/SciCode/eval/data/test_data.h5"
  TAG="original"
else
  DATA_DIR="$ROOT/scicode_verified"               # verified cleaned dataset (problems_test.jsonl + h5)
  H5="$ROOT/scicode_verified/test_data_cleaned.h5"
  TAG="cleaned"
fi

PYTHON="${PYTHON:-python3}"                        # use the env that has inspect_ai + scicode installed
SERVICE="${SERVICE:-openrouter}"
MODEL_NAME="${MODEL_NAME:-gpt-5}"
REASONING="${REASONING:-high}"
MAX_TOKENS="${MAX_TOKENS:-20480}"
SPLIT="${SPLIT:-test}"
OUTPUT_DIR="${OUTPUT_DIR:-$ROOT/eval_clean/results_${TAG}}"

echo "=== SciCode eval [$TAG] ==="
echo "  data-dir : $DATA_DIR"
echo "  h5py     : $H5"
echo "  model    : $SERVICE/$MODEL_NAME (reasoning=$REASONING, max_tokens=$MAX_TOKENS)"
echo "  output   : $OUTPUT_DIR"

cd "$INSPECT_DIR"
"$PYTHON" run_eval.py \
    --service "$SERVICE" \
    --model-name "$MODEL_NAME" \
    --load-api-key \
    --reasoning-mode "$REASONING" \
    --max-tokens "$MAX_TOKENS" \
    --split "$SPLIT" \
    --data-dir "$DATA_DIR" \
    --h5py-file "$H5" \
    --output-dir "$OUTPUT_DIR" \
    "$@"
echo "=== done [$TAG] -> $OUTPUT_DIR ==="
