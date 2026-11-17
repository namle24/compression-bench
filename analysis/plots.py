#!/usr/bin/env python3
"""Performance curves required by the project (section 6) plus workload characterization."""
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from parse import HZ, STAT_COLS

ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else "results")
FIG = ROOT / "figures"
CODECS = ["snappy", "lz4", "gzip", "zstd"]
APPS = {"sort": "Sort (I/O-bound)",
        "hashscore": "HashScore (CPU-bound)",
        "bigram": "BigramCount (balanced)"}
COLORS = {"none": "black", "snappy": "tab:blue", "lz4": "tab:orange",
          "gzip": "tab:green", "zstd": "tab:red"}
CONFIGS = ["C0", "C1", "C2", "C3"]
GB = 2**30


def save(fig, name):
    fig.tight_layout()
    fig.savefig(FIG / f"{name}.png", dpi=150)
    plt.close(fig)


def stat(df, by, col):
    g = df.groupby(by)[col]
    return g.mean(), g.std().fillna(0)


def select(df, app, cfg, codec):
    return df[(df.app == app) & (df.config == cfg) & (df.codec == codec)]


def vs_size(runs, col, ylabel, scale, name):
    for app, title in APPS.items():
        fig, axes = plt.subplots(1, 2, figsize=(11, 4), sharey=True)
        for ax, (cfg, level) in zip(axes, [("C1", "storage"), ("C2", "shuffle")]):
            for codec in ["none"] + CODECS:
                sel = select(runs, app, "C0" if codec == "none" else cfg, codec)
                if sel.empty:
                    continue
                m, s = stat(sel, "size_gb", col)
                ax.errorbar(m.index, m / scale, yerr=s / scale, marker="o", capsize=3,
                            color=COLORS[codec], label="none (C0)" if codec == "none" else codec)
            ax.set_title(f"{title}: {level} compression")
            ax.set_xlabel("Dataset size (GB)")
            ax.grid(alpha=0.3)
        axes[0].set_ylabel(ylabel)
        axes[1].legend()
        save(fig, f"{name}_{app}")


def bars(ax, groups, series, values, errors, colors=None):
    width = 0.8 / len(series)
    x = np.arange(len(groups))
    for i, s in enumerate(series):
        ax.bar(x + (i - (len(series) - 1) / 2) * width, values[i], width, yerr=errors[i],
               capsize=2, label=s, color=colors[i] if colors else None)
    ax.set_xticks(x)
    ax.set_xticklabels(groups)
    ax.grid(axis="y", alpha=0.3)


def config_bars(runs, size):
    fig, axes = plt.subplots(1, len(APPS), figsize=(15, 4))
    for ax, (app, title) in zip(axes, APPS.items()):
        df = runs[(runs.app == app) & (runs.size_gb == size)]
        c0 = df[df.config == "C0"].exec_s
        vals, errs = [], []
        for cfg in CONFIGS:
            if cfg == "C0":
                vals.append([c0.mean()] * len(CODECS))
                errs.append([c0.std()] * len(CODECS))
                continue
            m, s = stat(df[df.config == cfg], "codec", "exec_s")
            vals.append([m.get(c, np.nan) for c in CODECS])
            errs.append([s.get(c, 0) for c in CODECS])
        bars(ax, CODECS, CONFIGS, vals, errs)
        ax.set_title(f"{title}, {size} GB")
        ax.set_ylabel("Execution time (s)")
    axes[-1].legend(title="config")
    save(fig, "exec_vs_config")


def workload_bars(runs, size):
    df = runs[runs.size_gb == size]
    base = df[df.config == "C0"].groupby("app").exec_s.mean()
    fig, axes = plt.subplots(1, 3, figsize=(15, 4), sharey=True)
    for ax, cfg in zip(axes, ["C1", "C2", "C3"]):
        vals, errs = [], []
        for codec in CODECS:
            sel = df[(df.config == cfg) & (df.codec == codec)]
            rel = sel.exec_s / sel.app.map(base)
            m, s = rel.groupby(sel.app).mean(), rel.groupby(sel.app).std().fillna(0)
            vals.append([m.get(a, np.nan) for a in APPS])
            errs.append([s.get(a, 0) for a in APPS])
        bars(ax, [APPS[a].replace(" (", "\n(") for a in APPS], CODECS, vals, errs,
             [COLORS[c] for c in CODECS])
        ax.axhline(1.0, color="black", lw=1, ls="--")
        ax.set_title(f"{cfg} relative to C0 ({size} GB)")
    axes[0].set_ylabel("Execution time / C0")
    axes[-1].legend()
    save(fig, "exec_vs_workload")


def ratio_plots(gen, bench):
    fig, axes = plt.subplots(1, 3, figsize=(15, 4))
    if gen is not None:
        g = gen[gen.codec != "none"]
        m, s = stat(g, "codec", "ratio")
        axes[0].bar(CODECS, [m.get(c, np.nan) for c in CODECS], yerr=[s.get(c, 0) for c in CODECS],
                    color=[COLORS[c] for c in CODECS], capsize=3)
        axes[0].set_title("HDFS dataset compression ratio")
        axes[0].set_ylabel("Uncompressed / compressed size")

        size = gen.size_gb.max()
        t = gen[gen.size_gb == size].set_index("codec").exec_s
        order = ["none"] + CODECS
        axes[1].bar(order, [t.get(c, np.nan) for c in order], color=[COLORS[c] for c in order])
        axes[1].set_title(f"Dataset write time, {size} GB")
        axes[1].set_ylabel("DataGen execution time (s)")
    if bench is not None:
        b = bench.groupby("codec").agg(ratio=("ratio", "mean"),
                                       comp=("comp_mbps", "mean"),
                                       decomp=("decomp_mbps", "mean"))
        ax = axes[2]
        ax.scatter(b.comp, b.ratio, marker="o", label="compression")
        ax.scatter(b.decomp, b.ratio, marker="^", label="decompression")
        for name, r in b.iterrows():
            ax.annotate(name, (r.comp, r.ratio), textcoords="offset points", xytext=(4, 4))
        ax.set_xscale("log")
        ax.set_xlabel("Single-core throughput (MB/s, log)")
        ax.set_ylabel("Compression ratio")
        ax.set_title("Intrinsic codec trade-off")
        ax.legend()
    for ax in axes:
        ax.grid(alpha=0.3)
    save(fig, "compression_ratio")


def bench_table(bench):
    mb = bench.orig_bytes / 2**20
    bench["comp_mbps"] = mb / bench.comp_s
    bench["decomp_mbps"] = mb / bench.decomp_s
    bench["cpu_s_per_gb"] = (bench.comp_cpu_s + bench.decomp_cpu_s) / (mb / 1024)
    cols = ["ratio", "comp_mbps", "decomp_mbps", "comp_cpu_s", "decomp_cpu_s", "cpu_s_per_gb"]
    bench.groupby("codec", sort=False)[cols].agg(["mean", "std"]).round(3).to_csv(
        ROOT / "codec_bench_summary.csv")
    return bench


def timeseries(run_dir, master):
    frames = []
    for p in Path(run_dir).glob("stats-*.txt"):
        if p.stem == f"stats-{master}":
            continue
        df = pd.read_csv(p, sep=" ", names=STAT_COLS)
        d = df.diff().iloc[1:]
        dt = d.ts.values
        total = d.user + d.sys + d.other + d.idle + d.iowait
        frames.append(pd.DataFrame({
            "t": (df.ts.iloc[1:] - df.ts.iloc[0]).round().values,
            "cpu": 100 * ((d.user + d.sys + d.other) / total).values,
            "iowait": 100 * (d.iowait / total).values,
            "disk": ((d.disk_rd + d.disk_wr) / dt / 2**20).values,
            "net": (d.net_tx / dt / 2**20).values,
        }))
    df = pd.concat(frames)
    agg = df.groupby("t").agg(cpu=("cpu", "mean"), iowait=("iowait", "mean"),
                              disk=("disk", "sum"), net=("net", "sum"))
    return agg


def characterization(runs, size):
    fig, axes = plt.subplots(len(APPS), 3, figsize=(15, 9), sharex="row")
    for row, (app, title) in zip(axes, APPS.items()):
        sel = select(runs, app, "C0", "none")
        sel = sel[sel.size_gb == size]
        if sel.empty:
            continue
        r = sel.iloc[0]
        ts = timeseries(r.dir, r.master)
        row[0].plot(ts.index, ts.cpu, label="busy")
        row[0].plot(ts.index, ts.iowait, label="iowait")
        row[0].set_ylim(0, 100)
        row[0].set_ylabel(f"{title}\nCPU per worker (%)")
        row[0].legend()
        row[1].plot(ts.index, ts.disk, color="tab:brown")
        row[1].set_ylabel("Disk I/O, all workers (MB/s)")
        row[2].plot(ts.index, ts.net, color="tab:purple")
        row[2].set_ylabel("Network TX, all workers (MB/s)")
        for ax in row:
            ax.grid(alpha=0.3)
    for ax in axes[-1]:
        ax.set_xlabel("Time (s)")
    save(fig, "characterization_timeseries")

    df = runs[(runs.config == "C0") & (runs.size_gb == size)]
    cols = ["exec_s", "cpu_util", "iowait_util", "disk_mbps", "net_mbps"]
    df.groupby("app")[cols].agg(["mean", "std"]).round(3).to_csv(ROOT / "characterization.csv")


def main():
    FIG.mkdir(parents=True, exist_ok=True)
    runs = pd.read_csv(ROOT / "runs.csv")
    if "state" in runs:
        runs = runs[runs.state == "SUCCEEDED"]
    gen = pd.read_csv(ROOT / "datagen.csv") if (ROOT / "datagen.csv").exists() else None
    bench = pd.read_csv(ROOT / "codec_bench.csv") if (ROOT / "codec_bench.csv").exists() else None
    if bench is not None:
        bench = bench_table(bench)

    size = runs.groupby("size_gb").app.nunique().loc[lambda n: n == runs.app.nunique()].index.max()
    vs_size(runs, "exec_s", "Execution time (s)", 1, "exec_vs_size")
    vs_size(runs, "CPU_MILLISECONDS", "Task CPU time (s)", 1000, "cpu_vs_size")
    vs_size(runs, "disk_bytes", "Disk I/O volume, all nodes (GB)", GB, "disk_vs_size")
    vs_size(runs, "net_tx", "Network traffic, all nodes (GB)", GB, "net_vs_size")
    vs_size(runs, "REDUCE_SHUFFLE_BYTES", "Shuffled bytes (GB)", GB, "shuffle_bytes_vs_size")
    vs_size(runs, "shuffle_s", "Avg shuffle time per reducer (s)", 1, "shuffle_time_vs_size")
    config_bars(runs, size)
    workload_bars(runs, size)
    ratio_plots(gen, bench)
    characterization(runs, size)
    print(f"figures written to {FIG}")


if __name__ == "__main__":
    main()
