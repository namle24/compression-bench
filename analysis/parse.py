#!/usr/bin/env python3
"""Aggregate raw run directories into runs.csv and datagen.csv."""
import json
import sys
from pathlib import Path

import pandas as pd

HZ = 100
STAT_COLS = ["ts", "user", "sys", "idle", "iowait", "other",
             "disk_rd", "disk_wr", "net_rx", "net_tx", "mem"]
COUNTERS = ["CPU_MILLISECONDS", "GC_TIME_MILLIS", "MAP_OUTPUT_BYTES",
            "MAP_OUTPUT_MATERIALIZED_BYTES", "REDUCE_SHUFFLE_BYTES",
            "FILE_BYTES_READ", "FILE_BYTES_WRITTEN", "HDFS_BYTES_READ",
            "HDFS_BYTES_WRITTEN", "SPILLED_RECORDS"]


def read_stats(path, t0, t1):
    df = pd.read_csv(path, sep=" ", names=STAT_COLS)
    return df[(df.ts >= t0 - 1.5) & (df.ts <= t1 + 1.5)]


def node_totals(df):
    d = df.iloc[-1] - df.iloc[0]
    busy = (d.user + d.sys + d.other) / HZ
    total = busy + (d.idle + d.iowait) / HZ
    return {
        "cpu_s": busy,
        "cpu_util": busy / total if total else 0.0,
        "iowait_util": d.iowait / HZ / total if total else 0.0,
        "disk_rd": d.disk_rd,
        "disk_wr": d.disk_wr,
        "net_tx": d.net_tx,
        "mem_peak": df.mem.max(),
    }


def read_counters(path):
    if not path.exists():
        return {}
    groups = json.loads(path.read_text())["jobCounters"].get("counterGroup", [])
    out = {}
    for g in groups:
        for c in g["counter"]:
            if c["name"] in COUNTERS:
                out[c["name"]] = c["totalCounterValue"]
            if c["name"] == "CPU_MILLISECONDS":
                out["MAP_CPU_MILLISECONDS"] = c["mapCounterValue"]
                out["REDUCE_CPU_MILLISECONDS"] = c["reduceCounterValue"]
    return out


def read_job(path):
    if not path.exists():
        return {}
    j = json.loads(path.read_text())["job"]
    return {
        "state": j["state"],
        "exec_s": (j["finishTime"] - j["startTime"]) / 1000,
        "maps": j["totalMaps"],
        "reduces": j["totalReduces"],
        "map_s": j.get("avgMapTime", 0) / 1000,
        "shuffle_s": j.get("avgShuffleTime", 0) / 1000,
        "merge_s": j.get("avgMergeTime", 0) / 1000,
        "reduce_s": j.get("avgReduceTime", 0) / 1000,
    }


def parse_run(d):
    meta = json.loads((d / "meta.json").read_text())
    timing = json.loads((d / "timing.json").read_text())
    row = {**meta, "dir": str(d), "wall_s": timing["t1"] - timing["t0"]}
    row.update(read_job(d / "job.json"))
    row.update(read_counters(d / "counters.json"))

    nodes = {p.stem[len("stats-"):]: node_totals(read_stats(p, timing["t0"], timing["t1"]))
             for p in d.glob("stats-*.txt")}
    workers = [v for k, v in nodes.items() if k != meta["master"]]
    for key in ("cpu_s", "disk_rd", "disk_wr", "net_tx"):
        row[key] = sum(v[key] for v in nodes.values())
    for key in ("cpu_util", "iowait_util"):
        row[key] = sum(v[key] for v in workers) / max(len(workers), 1)
    row["mem_peak"] = max(v["mem_peak"] for v in workers) if workers else 0
    row["disk_bytes"] = row["disk_rd"] + row["disk_wr"]
    row["disk_mbps"] = row["disk_bytes"] / 2**20 / row["wall_s"]
    row["net_mbps"] = row["net_tx"] / 2**20 / row["wall_s"]
    return row


def collect(base):
    rows = [parse_run(d) for d in sorted(base.glob("*")) if (d / "meta.json").exists()]
    return pd.DataFrame(rows)


def main():
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "results")
    runs = collect(root / "raw")
    runs.to_csv(root / "runs.csv", index=False)
    print(f"runs.csv: {len(runs)} runs")

    gen = collect(root / "datagen")
    if not gen.empty:
        base = gen[gen.codec == "none"].set_index("size_gb").dataset_bytes
        gen["ratio"] = gen.size_gb.map(base) / gen.dataset_bytes
        gen.to_csv(root / "datagen.csv", index=False)
        print(f"datagen.csv: {len(gen)} datasets")

    if not runs.empty:
        keys = ["app", "size_gb", "config", "codec"]
        cols = ["exec_s", "shuffle_s", "CPU_MILLISECONDS", "cpu_util", "iowait_util",
                "disk_bytes", "net_tx", "REDUCE_SHUFFLE_BYTES"]
        summary = runs.groupby(keys)[cols].agg(["mean", "std", "count"])
        summary.to_csv(root / "summary.csv")


if __name__ == "__main__":
    main()
