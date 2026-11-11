#!/usr/bin/env bash
# Full campaign. Resumable: rerun after an interruption.
#   nohup scripts/run_all.sh > campaign.log 2>&1 &
set -euo pipefail
cd "$(dirname "$0")"
source ./bench.env
[ -f "$RESULTS/codec_bench.csv" ] || ./codec_bench.sh 256 5
./gen_data.sh
./run_experiments.sh
cd ../analysis
python3 parse.py "$RESULTS"
python3 plots.py "$RESULTS"
