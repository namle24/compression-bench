#!/usr/bin/env bash
# Quick end-to-end check (~10-15 min): 1 GB, one codec, one repetition.
set -euo pipefail
cd "$(dirname "$0")"
export SIZES=1 CODECS=snappy REPS=1 RESULTS=$(cd .. && pwd)/results-smoke
./gen_data.sh
./run_experiments.sh
cd ../analysis
python3 parse.py "$RESULTS"
python3 plots.py "$RESULTS"
column -s, -t < "$RESULTS/characterization.csv"
