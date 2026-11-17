#!/usr/bin/env python3
"""Readable tables of all results: results/tables.md

Usage: tables.py [results] [results-capped]
"""
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else "results")
CAPPED = Path(sys.argv[2]) if len(sys.argv) > 2 else None
GiB = 2**30
ORDER = ["none", "snappy", "lz4", "gzip", "zstd"]


def md(df):
    cols = [str(c) for c in df.columns]
    out = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for _, r in df.iterrows():
        out.append("| " + " | ".join(str(v) for v in r.values) + " |")
    return "\n".join(out)


def per_run_table(runs):
    g = runs.groupby(["app", "size_gb", "config", "codec"])
    t = g.agg(n=("exec_s", "size"), exec_s=("exec_s", "mean"), std=("exec_s", "std"),
              cpu_s=("CPU_MILLISECONDS", "mean"), shuffle_gib=("REDUCE_SHUFFLE_BYTES", "mean"),
              net_gib=("net_tx", "mean"), disk_gib=("disk_bytes", "mean"),
              shuffle_t=("shuffle_s", "mean"), cpu_util=("cpu_util", "mean")).reset_index()
    c0 = t[t.config == "C0"].set_index(["app", "size_gb"]).exec_s
    t["vs_C0"] = [f"{100 * (e / c0[(a, s)] - 1):+.1f}%" for a, s, e in zip(t.app, t.size_gb, t.exec_s)]
    t["cv"] = (100 * t["std"] / t.exec_s).round(1)
    t["cpu_s"] = (t.cpu_s / 1000).round(0).astype(int)
    for c in ["shuffle_gib", "net_gib", "disk_gib"]:
        t[c] = (t[c] / GiB).round(2)
    for c in ["exec_s", "std", "shuffle_t"]:
        t[c] = t[c].round(1)
    t["cpu_util"] = (100 * t.cpu_util).round(1) if t.cpu_util.max() <= 1 else t.cpu_util.round(1)
    t["codec"] = pd.Categorical(t.codec, ORDER)
    return t.sort_values(["app", "size_gb", "config", "codec"])


def main():
    runs = pd.read_csv(ROOT / "runs.csv")
    runs = runs[runs.state == "SUCCEEDED"] if "state" in runs else runs
    t = per_run_table(runs)
    cols = ["config", "codec", "n", "exec_s", "std", "cv", "vs_C0", "cpu_s", "cpu_util",
            "shuffle_gib", "shuffle_t", "net_gib", "disk_gib"]

    out = ["# Results tables", "",
           f"Generated from `{ROOT.name}/runs.csv` ({len(runs)} successful runs).",
           "exec_s and std: mean and standard deviation of the job time (s); cv: std/mean (%);",
           "vs_C0: change against C0 of the same app and size; cpu_s: task CPU time from the counters;",
           "cpu_util: mean CPU use of the workers (%); shuffle_gib: REDUCE_SHUFFLE_BYTES;",
           "shuffle_t: mean shuffle time per reducer (s); net_gib: bytes sent by all nodes; disk_gib: bytes read and written by all nodes.", ""]

    piv = t.pivot_table(index=["app", "size_gb"], columns=["config", "codec"], values="vs_C0", aggfunc="first", observed=True)
    piv.columns = [f"{c}-{k}" for c, k in piv.columns]
    piv = piv.drop(columns=[c for c in piv.columns if c.startswith("C0")]).reset_index()
    out += ["## Change of execution time against C0", "", md(piv), ""]

    for (app, size), df in t.groupby(["app", "size_gb"]):
        out += [f"## {app}, {size} GB", "", md(df[cols]), ""]

    char = ROOT / "characterization.csv"
    if char.exists():
        out += ["## Workload characterization (C0, largest size with all apps)", "", "```", char.read_text().strip(), "```", ""]
    bench = ROOT / "codec_bench_summary.csv"
    if bench.exists():
        out += ["## Codec micro-benchmark", "", "```", bench.read_text().strip(), "```", ""]
    gen = ROOT / "datagen.csv"
    if gen.exists():
        g = pd.read_csv(gen)
        out += ["## Datasets on HDFS", "", md(g), ""]
    if CAPPED and (CAPPED / "netlimit_summary.csv").exists():
        n = pd.read_csv(CAPPED / "netlimit_summary.csv")
        n["vs_c0"] = n.vs_c0.map(lambda v: f"{v:+.1f}%")
        out += ["## C2 with every node limited to 100 Mbit/s", "", md(n), ""]

    (ROOT / "tables.md").write_text("\n".join(out))
    print(f"wrote {ROOT / 'tables.md'}")


if __name__ == "__main__":
    main()
