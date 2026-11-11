#!/usr/bin/env bash
# Runs the experiment matrix. Repetitions are the outer loop so that a partial
# campaign already covers every configuration. Finished runs are skipped.
source "$(dirname "$0")/lib.sh"

app_class() {
  case "$1" in
    sort)      echo vn.usth.cbd.SortJob ;;
    hashscore) echo vn.usth.cbd.HashScore ;;
    bigram)    echo vn.usth.cbd.BigramCount ;;
    *) echo "unknown app: $1" >&2; return 1 ;;
  esac
}

run() {
  local app=$1 size=$2 cfg=$3 codec=$4 rep=$5
  local id=${app}_${size}g_${cfg}_${codec}_r${rep}
  local dir=$RESULTS/raw/$id
  local input=$HDFS_ROOT/data/${size}g/none
  local out=$HDFS_ROOT/out
  local opts=(-Dmapreduce.job.reduces="$REDUCERS" -Dhashscore.rounds="$HASH_ROUNDS") extra=()

  if [ -f "$dir/meta.json" ]; then
    return 0
  fi
  case $cfg in
    C1|C3)
      input=$HDFS_ROOT/data/${size}g/$codec
      read -ra extra <<< "$(storage_opts "$codec")"
      opts+=("${extra[@]}")
      ;;
  esac
  case $cfg in
    C2|C3)
      read -ra extra <<< "$(shuffle_opts "$codec")"
      opts+=("${extra[@]}")
      ;;
  esac

  hdfs dfs -rm -r -f -skipTrash "$out" >/dev/null 2>&1 || true
  echo "[$(date +%T)] $id"
  if ! measure "$dir" hadoop jar "$JAR" "$(app_class "$app")" "${opts[@]}" "$input" "$out"; then
    echo "  FAILED, see $dir/job.log" >&2
    return 0
  fi
  printf '{"app": "%s", "size_gb": %s, "config": "%s", "codec": "%s", "rep": %s, "master": "%s", "output_bytes": %s}\n' \
    "$app" "$size" "$cfg" "$codec" "$rep" "$MASTER" "$(hdfs_bytes "$out")" > "$dir/meta.json"
}

collect_env
for rep in $(seq "$REPS"); do
  for size in $SIZES; do
    for app in $APPS; do
      run "$app" "$size" C0 none "$rep"
      for codec in $CODECS; do
        for cfg in $CONFIGS; do
          run "$app" "$size" "$cfg" "$codec" "$rep"
        done
      done
    done
  done
done
echo "done: $(ls "$RESULTS/raw" | wc -l) runs in $RESULTS/raw"
