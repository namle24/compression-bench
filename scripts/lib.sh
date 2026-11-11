#!/usr/bin/env bash
set -euo pipefail
HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
source "$HERE/bench.env"
SSH="ssh -o BatchMode=yes -o StrictHostKeyChecking=no"

codec_class() {
  case "$1" in
    snappy) echo org.apache.hadoop.io.compress.SnappyCodec ;;
    lz4)    echo org.apache.hadoop.io.compress.Lz4Codec ;;
    gzip)   echo org.apache.hadoop.io.compress.GzipCodec ;;
    zstd)   echo org.apache.hadoop.io.compress.ZStandardCodec ;;
    bzip2)  echo org.apache.hadoop.io.compress.BZip2Codec ;;
    *) echo "unknown codec: $1" >&2; return 1 ;;
  esac
}

storage_opts() {
  echo "-Dmapreduce.output.fileoutputformat.compress=true" \
       "-Dmapreduce.output.fileoutputformat.compress.codec=$(codec_class "$1")" \
       "-Dmapreduce.output.fileoutputformat.compress.type=BLOCK"
}

shuffle_opts() {
  echo "-Dmapreduce.map.output.compress=true" \
       "-Dmapreduce.map.output.compress.codec=$(codec_class "$1")"
}

on_all() {
  local n
  for n in $NODES; do
    $SSH "$n" "$@" &
  done
  wait
}

drop_caches() {
  on_all "sync; echo 3 | sudo tee /proc/sys/vm/drop_caches >/dev/null"
}

hdfs_bytes() {
  hdfs dfs -du -s "$1" 2>/dev/null | awk '{print $1}'
}

fetch_job() {
  local job=$1 dir=$2
  for _ in $(seq 30); do
    if curl -sf "$JHS/ws/v1/history/mapreduce/jobs/$job" -o "$dir/job.json"; then
      curl -sf "$JHS/ws/v1/history/mapreduce/jobs/$job/counters" -o "$dir/counters.json"
      return 0
    fi
    sleep 2
  done
  echo "job history not found: $job" >&2
  return 1
}

# measure <run_dir> <command...>: run a job on a cold cache while every node is monitored.
measure() {
  local dir=$1 n job t0 t1 rc=0
  shift
  mkdir -p "$dir"
  drop_caches
  on_all "/opt/bench/monitor.sh start /tmp/bench.stats"
  sleep 2
  t0=$(date +%s.%N)
  "$@" > "$dir/job.log" 2>&1 || rc=$?
  t1=$(date +%s.%N)
  sleep 2
  on_all "/opt/bench/monitor.sh stop"
  for n in $NODES; do
    $SSH "$n" cat /tmp/bench.stats > "$dir/stats-$n.txt"
  done
  job=$(grep -oE 'job_[0-9]+_[0-9]+' "$dir/job.log" | head -1 || true)
  printf '{"t0": %s, "t1": %s, "rc": %d, "job": "%s"}\n' "$t0" "$t1" "$rc" "$job" > "$dir/timing.json"
  if [ -n "$job" ]; then
    fetch_job "$job" "$dir" || true
  fi
  return "$rc"
}

collect_env() {
  local d=$RESULTS/env n
  mkdir -p "$d"
  cp "$HADOOP_HOME"/etc/hadoop/*-site.xml "$d/"
  cp "$HERE/bench.env" "$d/"
  hadoop version > "$d/hadoop-version.txt"
  hadoop checknative -a > "$d/checknative.txt" 2>&1 || true
  for n in $NODES; do
    $SSH "$n" "uname -a; nproc; free -m; lscpu | head -n 20; df -h /data" > "$d/node-$n.txt" 2>&1 || true
  done
}
