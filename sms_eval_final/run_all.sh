#!/usr/bin/env bash
# Full evaluation + retrain + Java parity fixture, on the merged 2,200-message set.
# Run from this folder:  bash run_all.sh [path/to/parity_fixture.tsv]
set -euo pipefail
FIXTURE="${1:-../backend/src/test/resources/sms/parity_fixture.tsv}"

# 1. (optional) rebuild the real-format set and the merged files; same seed gives the same messages
#    python3 gen_real_formats.py 1200 7

# 2. evaluate: random, unseen_wording, unseen_sender, real_formats (train fictional -> test real)
python3 evaluate.py sms_dataset_2200.jsonl manifest_2200.csv | tee eval_report.txt

# 3. train the production model on everything
python3 sms_model.py train sms_dataset_2200.jsonl sms_txn_model.joblib

# 4. after your Java export step, regenerate the parity fixture (now includes the real-format quirks)
mkdir -p "$(dirname "$FIXTURE")"
python3 make_parity_fixture.py sms_txn_model.joblib sms_dataset_2200.jsonl "$FIXTURE"
