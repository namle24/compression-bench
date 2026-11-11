#!/usr/bin/env bash
# Per-node sampler (1 s): cpu jiffies, disk bytes, network bytes, used memory.
# Columns: ts user sys idle iowait other disk_rd disk_wr net_rx net_tx mem_used
PIDFILE=/tmp/bench-monitor.pid

sample() {
  local t cpu disk net mem
  t=$(date +%s.%N)
  cpu=$(awk '/^cpu / {printf "%.0f %.0f %.0f %.0f %.0f", $2+$3, $4, $5, $6, $7+$8+$9}' /proc/stat)
  disk=$(awk '$3 ~ /^(sd[a-z]+|vd[a-z]+|xvd[a-z]+|nvme[0-9]+n[0-9]+)$/ {r += $6; w += $10}
              END {printf "%.0f %.0f", r*512, w*512}' /proc/diskstats)
  net=$(awk 'NR > 2 {sub(/^ +/, ""); split($0, a, /[: ]+/); if (a[1] != "lo") {rx += a[2]; tx += a[10]}}
             END {printf "%.0f %.0f", rx, tx}' /proc/net/dev)
  mem=$(awk '/^MemTotal/ {t = $2} /^MemAvailable/ {a = $2} END {printf "%.0f", (t - a) * 1024}' /proc/meminfo)
  echo "$t $cpu $disk $net $mem"
}

case "${1:-}" in
  start)
    "$0" stop
    nohup "$0" loop "$2" >/dev/null 2>&1 </dev/null &
    echo $! > "$PIDFILE"
    ;;
  loop)
    : > "$2"
    while true; do
      sample >> "$2"
      sleep 1
    done
    ;;
  stop)
    if [ -f "$PIDFILE" ]; then
      kill "$(cat "$PIDFILE")" 2>/dev/null || true
      rm -f "$PIDFILE"
    fi
    ;;
  sample)
    sample
    ;;
  *)
    echo "usage: $0 start <file> | stop | sample" >&2
    exit 1
    ;;
esac
