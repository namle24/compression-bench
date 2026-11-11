#!/usr/bin/env bash
# Optional: cap the egress bandwidth of every node to make the network a bottleneck.
# Usage: netlimit.sh set 100mbit | clear | show
source "$(dirname "$0")/lib.sh"
DEV='$(ip route show default | awk "{print \$5; exit}")'

case "${1:-}" in
  set)   on_all "sudo tc qdisc replace dev $DEV root tbf rate ${2:?rate} burst 256kb latency 100ms" ;;
  clear) on_all "sudo tc qdisc del dev $DEV root 2>/dev/null || true" ;;
  show)  on_all "hostname; tc qdisc show dev $DEV" ;;
  *) echo "usage: $0 set <rate> | clear | show" >&2; exit 1 ;;
esac
