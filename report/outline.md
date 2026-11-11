# Report outline

1. **Introduction**: storage vs communication compression, objectives.
2. **Infrastructure**: topology (PC/laptop VMs, bridged network), Hadoop config
   (`results/env/`), monitoring, reproducibility (Ansible, scripts).
3. **Methodology**: SequenceFile block compression, one file per task, cold
   cache, slowstart=1.0, repetitions, metric sources (see README section 4).
4. **Workloads and their characterization**: `characterization_timeseries.png`,
   `characterization.csv` (CPU utilization, iowait, disk MB/s, network MB/s).
5. **Intrinsic codec characteristics**: `codec_bench_summary.csv`,
   `compression_ratio.png`.
6. **Storage-level compression (C1)**: `exec/cpu/disk_vs_size_*`, left panels.
7. **Communication-level compression (C2)**: `net/shuffle_*_vs_size_*`, right panels.
8. **Combined compression (C3)**: `exec_vs_config.png`.
9. **Impact of dataset size**: trends across all `*_vs_size_*` figures.
10. **Discussion**: answer each question with numbers taken from `summary.csv`:
    1. Best ratio / CPU trade-off → codec bench + `cpu_vs_size` + `exec_vs_size`
    2. Is I/O-bound always improved? → Sort, C1/C2/C3
    3. Effect on CPU-bound apps → HashScore
    4. Evolution with size → slopes of `exec_vs_size`
    5. Storage vs network → C1 vs C2 in `exec_vs_workload`
    6. Can C3 be worse than C1/C2? → `exec_vs_config`
    7. When to disable compression → synthesis
11. **Unexpected results and limitations**: virtual network on a single PC,
    heterogeneous laptop worker, small cluster, synthetic data.
