#!/usr/bin/env python3
"""C0 vs C2 with the normal network and with every node capped by netlimit.sh.

Usage: netlimit_plot.py <results> <results-capped> [label]
"""
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

CODECS = ["none", "snappy", "lz4", "gzip", "zstd"]
APPS = {"sort": "Sort (I/O-bound)", "bigram": "BigramCount (balanced)"}


def c2(path):
    r = pd.read_csv(Path(path) / "runs.csv")
    return r[r.config.isin(["C0", "C2"]) & r.app.isin(list(APPS))]


def main():
    base, capped = c2(sys.argv[1]), c2(sys.argv[2])
    label = sys.argv[3] if len(sys.argv) > 3 else "100 Mbit/s"
    sizes = sorted(capped.size_gb.unique())
    capped_sizes = capped.size_gb.unique()
    base = base[base.size_gb.isin(capped_sizes)]

    rows = []
    for name, df in [("full", base), ("capped", capped)]:
        g = df.groupby(["app", "size_gb", "codec"]).agg(
            exec_m=("exec_s", "mean"), exec_s=("exec_s", "std"),
            shuffle_s=("shuffle_s", "mean"), net_mbps=("net_mbps", "mean"),
            cpu_s=("CPU_MILLISECONDS", lambda x: x.mean() / 1000))
        g["network"] = name
        rows.append(g.reset_index())
    t = pd.concat(rows)
    c0 = t[t.codec == "none"].set_index(["network", "app", "size_gb"]).exec_m
    t["vs_c0"] = [100 * (m / c0[(n, a, s)] - 1) for n, a, s, m in zip(t.network, t.app, t.size_gb, t.exec_m)]
    out = Path(sys.argv[2])
    t.round(3).to_csv(out / "netlimit_summary.csv", index=False)

    fig, axes = plt.subplots(len(APPS), len(sizes), figsize=(6 * len(sizes), 4 * len(APPS)), squeeze=False)
    x = np.arange(len(CODECS))
    for i, app in enumerate(APPS):
        for j, size in enumerate(sizes):
            ax = axes[i][j]
            for k, (net, lab, col) in enumerate([("full", "full speed", "#7f7f7f"), ("capped", label, "#d62728")]):
                s = t[(t.network == net) & (t.app == app) & (t.size_gb == size)].set_index("codec").reindex(CODECS)
                ax.bar(x + (k - 0.5) * 0.38, s.exec_m, 0.38, yerr=s.exec_s.fillna(0), capsize=3, label=lab, color=col)
            ax.set_xticks(x)
            ax.set_xticklabels(["none (C0)"] + [f"{c} (C2)" for c in CODECS[1:]])
            ax.set_title(f"{APPS[app]}, {size} GB")
            ax.set_ylabel("Execution time (s)")
            ax.grid(axis="y", alpha=0.3)
    axes[0][0].legend()
    fig.tight_layout()
    fig.savefig(Path(sys.argv[1]) / "figures" / "netlimit_c2.png", dpi=150)
    print(t.pivot_table(index=["app", "size_gb", "codec"], columns="network",
                        values=["exec_m", "vs_c0", "shuffle_s"]).round(1).to_string())


if __name__ == "__main__":
    main()
