# Hướng dẫn chạy trên PC + laptop

Mac chỉ dùng để code. Mọi thứ dưới đây làm trên PC (VMware) và laptop.

## Bước 1: Tạo VM (khoảng 30 phút)

| VM      | Máy    | vCPU | RAM  | Disk  |
|---------|--------|------|------|-------|
| master  | PC     | 2    | 4 GB | 40 GB |
| worker1 | PC     | 4    | 8 GB | 60 GB |
| worker2 | PC     | 4    | 8 GB | 60 GB |
| worker3 | laptop | 4    | 8 GB | 60 GB |

- Cài Ubuntu Server 22.04 (hoặc 24.04) cho một VM. Khi cài, tạo user tên **`hadoop`** và chọn cài OpenSSH server.
- Trên PC, cài xong một VM rồi **Clone** (Full clone) ra 2 VM còn lại. Với mỗi bản clone, vào Network Adapter → Advanced → **Generate MAC**.
- Mọi VM để Network Adapter ở chế độ **Bridged**.
- Worker3 trên laptop: tạo VM bằng VirtualBox/KVM/VMware (cũng Bridged).
  Nếu không thể tạo VM, có thể cài thẳng lên laptop, nhưng Ansible sẽ đổi hostname của laptop thành `worker3`.
- Nếu PC không đủ RAM: giảm RAM của worker xuống 6 GB và sửa `nm_memory_mb` trong `ansible/group_vars/all.yml` (để lại khoảng 1.5 GB cho OS).

Đặt IP tĩnh trên mỗi VM, ví dụ `/etc/netplan/50-cloud-init.yaml` (sửa tên card `ens33` theo `ip a`, và IP/gateway theo mạng nhà bạn):

```yaml
network:
  version: 2
  ethernets:
    ens33:
      dhcp4: no
      addresses: [192.168.1.101/24]
      routes:
        - to: default
          via: 192.168.1.1
      nameservers:
        addresses: [8.8.8.8]
```

Áp dụng bằng `sudo netplan apply`. Kiểm tra bằng cách ping giữa các VM, đặc biệt là từ VM trên PC sang VM trên laptop.

## Bước 2: Copy project sang master

Từ Mac (nếu cùng mạng với master):

```bash
scp compression-bench.tar.gz hadoop@<IP-master>:~
```

Nếu không cùng mạng thì dùng USB, hoặc push lên GitHub (private) rồi `git clone` từ master.

Trên master:

```bash
tar xzf compression-bench.tar.gz && cd compression-bench
nano ansible/inventory.ini        # điền 4 IP
nano ansible/group_vars/all.yml   # nm_memory_mb / nm_vcores khớp với worker
```

## Bước 3: Setup cụm (một lệnh, khoảng 15 phút)

```bash
./setup_master.sh
```

- Script sẽ hỏi mật khẩu của user `hadoop` 4 lần (cho `ssh-copy-id`), rồi hỏi 1 lần mật khẩu sudo (`BECOME password`).
- Kết quả đúng khi:
  - có 3 *Live datanodes* và 3 node trong `yarn node -list`;
  - `hadoop checknative` báo `zlib: true` và `zstd: true`.
  - Nếu zstd là false: sửa `CODECS` trong `scripts/bench.env` thành `snappy lz4 gzip`.

## Bước 4: Chạy thử (khoảng 15 phút)

```bash
scripts/smoke_test.sh
```

Xem bảng in ra cuối cùng (cột `cpu_util`, `disk_mbps`, `net_mbps`) và hình `results-smoke/figures/characterization_timeseries.png`:

- `hashscore` phải có CPU khoảng 90% trở lên, disk và network thấp. Nếu chưa đạt, tăng `HASH_ROUNDS` trong `scripts/bench.env` (ví dụ 400).
- `sort` phải có CPU thấp nhất, disk và network cao nhất.
- `bigram` nằm ở giữa.

## Bước 5: Chạy toàn bộ (để qua đêm)

```bash
nohup scripts/run_all.sh > campaign.log 2>&1 &
tail -f campaign.log
```

- Nếu bị ngắt (mất điện, tắt máy), chỉ cần chạy lại lệnh trên: các run đã xong sẽ được bỏ qua.
- Muốn nhanh hơn: đặt `SIZES="1 2 4"` trong `scripts/bench.env` (còn khoảng 60% thời gian).
- Không dùng PC/laptop cho việc khác trong lúc chạy, vì sẽ làm nhiễu số đo.
- Thí nghiệm thêm (khuyến nghị cho câu hỏi 5 và 7) — mạng chậm:
  ```bash
  scripts/netlimit.sh set 100mbit
  RESULTS=$PWD/results-100mbit CONFIGS=C2 SIZES="2 4" scripts/run_experiments.sh
  scripts/netlimit.sh clear
  cd analysis && python3 parse.py ../results-100mbit && python3 plots.py ../results-100mbit
  ```

## Bước 6: Lấy kết quả về Mac để viết báo cáo

```bash
scp -r hadoop@<IP-master>:~/compression-bench/results ./
```

Hình nằm trong `results/figures/`, số liệu để trích dẫn trong báo cáo nằm trong `results/summary.csv`. Dàn ý báo cáo: `report/outline.md`.

## Lỗi thường gặp

| Triệu chứng | Cách xử lý |
|---|---|
| Tải Hadoop 404 | Trong `group_vars/all.yml`, đổi URL bỏ `-lean` |
| DataNode không lên | `cat /opt/hadoop/logs/*datanode*.log`; kiểm tra `/etc/hosts` không còn dòng `127.0.1.1` |
| Job treo ở ACCEPTED | RAM YARN quá nhỏ: kiểm tra `nm_memory_mb` ≥ `reduce_memory_mb` + `am_memory_mb` |
| Một run FAILED | Xem `results/raw/<run>/job.log`, rồi chạy lại script (run lỗi sẽ được chạy lại) |
| Dừng/khởi động lại cụm | `/opt/bench/cluster.sh stop` / `start` (sau khi reboot VM) |
