#!/usr/bin/env bash
set -euo pipefail
H=${HADOOP_HOME:-/opt/hadoop}

case "${1:-}" in
  start)
    if jps | grep -q NameNode; then
      echo "already running"
      exit 0
    fi
    # setsid: keep daemons alive after the SSH session closes
    setsid "$H/sbin/start-dfs.sh" < /dev/null
    setsid "$H/sbin/start-yarn.sh" < /dev/null
    setsid "$H/bin/mapred" --daemon start historyserver < /dev/null
    "$H/bin/hdfs" dfsadmin -safemode wait
    ;;
  stop)
    "$H/bin/mapred" --daemon stop historyserver || true
    "$H/sbin/stop-yarn.sh"
    "$H/sbin/stop-dfs.sh"
    ;;
  status)
    jps
    "$H/bin/hdfs" dfsadmin -report | grep -E '^(Name|Live|Configured Capacity|DFS Remaining)'
    "$H/bin/yarn" node -list
    "$H/bin/hadoop" checknative -a || true
    ;;
  *)
    echo "usage: $0 start|stop|status" >&2
    exit 1
    ;;
esac
