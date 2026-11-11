# Experimental Evaluation of Data Compression in Hadoop MapReduce

InfraCloud project (USTH, Cloud and Big Data). We measure the cost and benefit of
Snappy, LZ4, Gzip and Zstandard at the storage level (HDFS) and at the
communication level (MapReduce shuffle) on three workloads.

**Why Hadoop MapReduce rather than Spark:** all four codecs are supported at both
levels (`mapreduce.output.fileoutputformat.compress.codec` and
`mapreduce.map.output.compress.codec`). Spark's `spark.io.compression.codec`
does not support Gzip for shuffle data.

## Layout

```
ansible/            cluster deployment (Hadoop 3.4.1, HDFS + YARN + JobHistory)
apps/src/           MapReduce applications, data generator, codec micro-benchmark
scripts/            experiment drivers and the per-node monitor
analysis/           parse.py (raw -> CSV), plots.py (CSV -> figures)
results/            raw measurements, CSV tables and figures (created by the scripts)
report/outline.md   report structure and which figure answers which question
```

## 1. Infrastructure

Reference topology (bridged networking, all VMs on the same LAN, static IPs):

| VM      | Host   | Role                                           | Suggested size        |
|---------|--------|------------------------------------------------|-----------------------|
| master  | PC     | NameNode, ResourceManager, JobHistory, driver  | 2 vCPU, 4 GB, 40 GB   |
| worker1 | PC     | DataNode, NodeManager                          | 4 vCPU, 8 GB, 60 GB   |
| worker2 | PC     | DataNode, NodeManager                          | 4 vCPU, 8 GB, 60 GB   |
| worker3 | laptop | DataNode, NodeManager                          | 4 vCPU, 8 GB, 60 GB   |

- Ubuntu Server 22.04 or 24.04 on every VM, same user (`hadoop`) with sudo.
- VMware: set the network adapter to *Bridged*, and regenerate the MAC address
  of cloned VMs. Use a wired link between the PC and the laptop if possible.
- Traffic between VMs on the same PC never reaches the physical NIC, so its
  bandwidth is much higher than PC <-> laptop traffic. Keep this in mind when
  interpreting shuffle results, or use `scripts/netlimit.sh` (section 5).
- If the laptop cannot host a VM, put all workers on the PC and use
  `netlimit.sh` to emulate a real network.

Adapt `ansible/inventory.ini` (IPs) and `ansible/group_vars/all.yml`
(YARN memory/vcores must match the worker VMs).

## 2. Deployment

On the master VM:

```bash
sudo apt install -y ansible git
git clone <this repo> ~/compression-bench && cd ~/compression-bench/ansible
ssh-keygen -t ed25519           # if no key yet
for h in master worker1 worker2 worker3; do ssh-copy-id hadoop@<ip-of-$h>; done
ansible all -m ping
ansible-playbook site.yml -K
```

The playbook installs Java 11 and Hadoop, writes the configuration, sets up
passwordless SSH from the master, formats HDFS and starts all daemons.
Then, in a new login shell:

```bash
/opt/bench/cluster.sh status     # 3 live DataNodes, 3 NodeManagers
hadoop checknative -a            # zlib, zstd must be "true"
cd ~/compression-bench/apps && ./build.sh
```

Web UIs: HDFS `http://master:9870`, YARN `http://master:8088`,
JobHistory `http://master:19888`.

## 3. Applications

All applications read the same SequenceFile dataset and use identical code in
every configuration; only `-D` options change.

| App          | Profile   | Logic                                                         | Shuffle         |
|--------------|-----------|---------------------------------------------------------------|-----------------|
| `SortJob`    | I/O-bound | identity map, range partitioner, identity reduce (total sort) | = input size    |
| `HashScore`  | CPU-bound | `hashscore.rounds` iterations of SHA-256 per record, sum/city | a few KB        |
| `BigramCount`| balanced  | bigram count on the comment field, with combiner              | large, reduced  |

The dataset (`DataGen`) contains synthetic sales records
`id|date|city|product|price|qty|comment`, with a Zipf vocabulary for comments
(about 2.3x with gzip). The profiles must be confirmed by measurements
(`characterization_*` outputs). If HashScore is not clearly CPU-bound on your
VMs, increase `HASH_ROUNDS`. `-Dbigram.combiner=false` makes BigramCount
shuffle-heavier.

## 4. Methodology choices

- **Splittable storage compression.** Plain `.gz`, `.snappy`, `.lz4` and `.zst`
  files are not splittable. The input is stored as block-compressed
  SequenceFiles, which can be split with any codec.
- **Same parallelism for every codec.** `DataGen` writes one file of about 100 MB
  per task, which is less than the 128 MB block size. Every codec therefore gives
  the same number of map tasks, so the comparison does not mix compression
  effects with parallelism effects.
- **Same data for every codec.** The generator is deterministic (fixed seed).
- **Cold cache.** Page caches are dropped on every node before each run.
- **Clean shuffle measurement.** `reduce.slowstart.completedmaps=1.0`, so
  the shuffle does not overlap the map phase. Speculative execution is disabled.
- **Variability.** Each point is repeated `REPS` times (default 3). Repetitions
  are the outer loop, so slow drifts affect all configurations equally. Figures
  show mean ± standard deviation.
- **Metrics.**
  - Execution time, average shuffle time per reducer, task CPU time, and
    shuffled bytes come from the JobHistory REST API.
  - CPU utilization, iowait, disk bytes and network bytes come from a 1 s
    `/proc` sampler on every node (`scripts/monitor.sh`).

## 5. Running the campaign

```bash
cd ~/compression-bench/scripts
./codec_bench.sh 256 5        # intrinsic ratio / speed / CPU per codec (section 4 of the subject)
./gen_data.sh                 # datasets for every size x codec (+ write overhead)
./run_experiments.sh          # full matrix, resumable
```

Everything is parameterized in `scripts/bench.env` and can be overridden:

```bash
SIZES="1" REPS=1 ./run_experiments.sh                  # smoke test (~40 min)
APPS="sort" CODECS="snappy zstd" ./run_experiments.sh  # subset
```

Default matrix: 3 apps × 4 sizes × (C0 + 4 codecs × C1/C2/C3) × 3 reps = 468
runs. Count about 1–3 min per run on the reference cluster, so plan 1–2 days
(it can run overnight). Start with `SIZES="1 2 4"` if time is short.
HDFS space: about 2.5× the sum of `SIZES` (one copy per codec) × replication.

Optional network factor (communication compression under a slow network):

```bash
./netlimit.sh set 100mbit
RESULTS=$PWD/../results-100mbit CONFIGS="C2" ./run_experiments.sh
./netlimit.sh clear
```

## 6. Analysis

```bash
cd ~/compression-bench/analysis
python3 parse.py ../results     # runs.csv, datagen.csv, summary.csv
python3 plots.py ../results     # figures/*.png, characterization.csv, codec_bench_summary.csv
```

| Figure                          | Required curve                                   |
|---------------------------------|--------------------------------------------------|
| `exec_vs_size_<app>`            | execution time vs size, per codec                |
| `cpu_vs_size_<app>`             | CPU consumption vs size (compression overhead)   |
| `disk_vs_size_<app>`            | disk I/O volume vs size (storage compression)    |
| `net_vs_size_<app>`             | network traffic vs size (communication)          |
| `shuffle_bytes/time_vs_size_*`  | shuffle volume and shuffle time                  |
| `compression_ratio`             | ratio vs algorithm, write overhead, codec trade-off |
| `exec_vs_config`                | execution time vs C0/C1/C2/C3                    |
| `exec_vs_workload`              | execution time vs workload type (relative to C0) |
| `characterization_timeseries`   | CPU / disk / network profile of each application |
