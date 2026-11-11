#!/usr/bin/env bash
# Generates every dataset once per codec. Same seed => identical records for all codecs.
source "$(dirname "$0")/lib.sh"

for size in $SIZES; do
  for codec in none $CODECS; do
    out=$HDFS_ROOT/data/${size}g/$codec
    dir=$RESULTS/datagen/${size}g_$codec
    if hdfs dfs -test -d "$out"; then
      echo "skip $out"
      continue
    fi
    opts=()
    if [ "$codec" != none ]; then
      read -ra opts <<< "$(storage_opts "$codec")"
    fi
    echo "[$(date +%T)] generating $out"
    measure "$dir" hadoop jar "$JAR" vn.usth.cbd.DataGen "${opts[@]}" "$((size * 1024))" "$out"
    printf '{"size_gb": %s, "codec": "%s", "dataset_bytes": %s, "master": "%s"}\n' \
      "$size" "$codec" "$(hdfs_bytes "$out")" "$MASTER" > "$dir/meta.json"
  done
done
