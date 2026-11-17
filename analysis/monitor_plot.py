#!/usr/bin/env python3
"""Per-node CPU, memory, disk and network over time for one run.

Usage: monitor_plot.py <run_dir> [out.png]
"""
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

COLS = ["ts", "user", "sys", "idle", "iowait", "other",
        "disk_rd", "disk_wr", "net_rx", "net_tx", "mem"]


def load(path):
    a = np.loadtxt(path, ndmin=2)
    d = dict(zip(COLS, a.T))
    dt = np.diff(d["ts"])
    jiff = np.diff(d["user"] + d["sys"] + d["idle"] + d["iowait"] + d["other"])
    busy = np.diff(d["user"] + d["sys"] + d["other"])
    return {
        "t": d["ts"][1:],
        "cpu": 100 * busy / np.maximum(jiff, 1),
        "iowait": 100 * np.diff(d["iowait"]) / np.maximum(jiff, 1),
        "mem": d["mem"][1:] / 2**30,
        "disk": (np.diff(d["disk_rd"]) + np.diff(d["disk_wr"])) / dt / 2**20,
        "net": (np.diff(d["net_rx"]) + np.diff(d["net_tx"])) / dt / 2**20,
    }


def main():
    run = Path(sys.argv[1])
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else run / "monitor.png"
    nodes = {p.stem.split("-", 1)[1]: load(p) for p in sorted(run.glob("stats-*.txt"))}
    t0 = min(n["t"][0] for n in nodes.values())

    panels = [("cpu", "CPU busy (%)"), ("mem", "Memory used (GiB)"),
              ("disk", "Disk read+write (MiB/s)"), ("net", "Network rx+tx (MiB/s)")]
    fig, axes = plt.subplots(len(panels), 1, figsize=(10, 9), sharex=True)
    for ax, (key, label) in zip(axes, panels):
        for name, n in nodes.items():
            ax.plot(n["t"] - t0, n[key], lw=0.9, label=name)
        ax.set_ylabel(label)
        ax.grid(alpha=0.3)
    axes[0].set_ylim(0, 100)
    axes[0].legend(ncol=len(nodes), loc="upper right", fontsize=8)
    axes[-1].set_xlabel("Time since job submission (s)")
    fig.suptitle(run.name)
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    print(out)


if __name__ == "__main__":
    main()
