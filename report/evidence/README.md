# Evidence

Raw material collected while the experiments ran. The numbers in the report come from
`results/runs.csv`; `results/tables.md` has all of them in readable form
(regenerate with `python3 analysis/tables.py results results-100mbit`).

## screenshots/

Web UIs of the cluster (NameNode :9870, ResourceManager :8088, JobHistory :19888),
taken with headless Chrome. Each folder has the same 13 pages; `job_id.txt` is the job
shown on pages 10-13.

| Folder | When |
|---|---|
| `during-campaign-r3/` | main campaign, repetition 3 in progress |
| `campaign-end/` | after the 468 runs of the main campaign |
| `netlimit-100mbit/` | network-limited runs; pages 20-21 are Sort 4 GB C0 and C2-zstd with the limit (`netlimit_jobs.txt`) |
| `during-16g/` | 16 GB runs in progress |
| `final/` | end of all experiments |

Pages: 01 HDFS overview, 02 DataNodes, 03 `/bench` in the HDFS browser, 04 cluster
metrics, 05 NodeManagers, 06 all applications, 07 running applications, 08 scheduler,
09 JobHistory list, 10 job overview, 11 job counters, 12 map tasks, 13 job configuration.

## cluster/

Snapshots of the cluster state, one folder per date (UTC): Hadoop version,
`hadoop checknative`, `hdfs dfsadmin -report`, HDFS usage of `/bench`, YARN nodes,
list of jobs, the `*-site.xml` files, `bench.env`, hardware of each node
(`node_<host>.txt`) and the tail of the daemon logs (`daemonlog_<host>.txt`).

## logs/

| File | Content |
|---|---|
| `ansible-setup.log` | deployment of the cluster with `ansible/site.yml` |
| `smoke.log` | first test of all apps and codecs at 1 GB |
| `campaign.log` | main campaign: 1-8 GB, 3 apps, C0-C3, 3 repetitions |
| `netlimit.log` | C0/C2 for Sort and BigramCount at 2 and 4 GB, all nodes at 100 Mbit/s |
| `run16.log` | 16 GB datasets and runs (Sort and BigramCount) |
| `followup_scripts.txt` | the two wrapper scripts used for the last two experiments |

## Per-run data

Every run has a folder in `results/raw/` (and `results-100mbit/raw/`) with the job log,
the JobHistory JSON (`job.json`, `counters.json`), timings, and one `stats-<host>.txt`
per node with one `/proc` sample per second
(`ts user sys idle iowait other disk_rd disk_wr net_rx net_tx mem`).
`analysis/monitor_plot.py <run dir>` turns them into a plot such as
`results/figures/monitor_sort_8g_C0_none_r1.png`.

Useful pairs of monitor plots:

- `monitor_sort_8g_C0_none_r1.png` / `monitor_sort_8g_C3_zstd_r1.png`: Sort without and with compression
- `monitor_hashscore_8g_C0_none_r1.png`, `monitor_bigram_8g_C0_none_r1.png`: CPU-bound and balanced profiles
- `monitor_sort_4g_C0_none_r3.png` / `monitor_sort_4g_C0_none_capped.png`: Sort 4 GB with the normal network and with every node at 100 Mbit/s
