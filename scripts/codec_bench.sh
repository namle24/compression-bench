#!/usr/bin/env bash
# Intrinsic codec benchmark (single core, in memory). Usage: codec_bench.sh [sampleMB] [reps]
source "$(dirname "$0")/lib.sh"
mkdir -p "$RESULTS"
export HADOOP_CLIENT_OPTS="-Xmx3g"
hadoop jar "$JAR" vn.usth.cbd.CodecBench "${1:-256}" "${2:-5}" > "$RESULTS/codec_bench.csv"
column -s, -t < "$RESULTS/codec_bench.csv"
