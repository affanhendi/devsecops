# Laporan Praktikum Gabungan Bab 6 dan Bab 7

**Mata Kuliah:** DevSecOps Workshop  
**Bab:** 6 — Centralized Logging dengan Fluent Bit dan PostgreSQL  
**Bab:** 7 — Monitoring Resource dengan Prometheus, cAdvisor, Node Exporter, dan Grafana  
**Tanggal Praktikum:** 13, 26, dan 27 Oktober 2026  
**Lokasi Bukti:** `laporan/bab6/assets/` (34 screenshot)  

---

## BAB 6 — Centralized Logging dengan Fluent Bit dan PostgreSQL

### 1. Pendahuluan

Container sering dibuat dan dihapus secara cepat (ephemeral). Jika log hanya tersimpan di dalam container lokal, maka debugging dan audit menjadi sulit karena log hilang bersama container. Centralized logging memindahkan log ke satu tempat penyimpanan sehingga dapat dicari, dianalisis, dan diaudit secara konsisten lintas service.

Praktikum Bab 6 bertujuan membangun pipeline logging terpusat menggunakan **Fluent Bit** sebagai collector, **Docker logging driver fluentd** sebagai pengiriman log dari container, dan **PostgreSQL** sebagai backend penyimpanan log dalam format **JSONB**.

### 2. Tujuan Pembelajaran Bab 6

Setelah menyelesaikan praktikum ini, diharapkan mampu:

1. Menjelaskan kebutuhan centralized logging pada lingkungan container yang ephemeral.
2. Mengirim log `stdout/stderr` container ke Fluent Bit menggunakan Docker fluentd logging driver.
3. Menyimpan log ke PostgreSQL dalam kolom JSONB dan membuat view analisis.
4. Membuat log generator untuk mensimulasikan INFO, DEBUG, WARN, ERROR, dan CRITICAL.
5. Menerapkan query pencarian log dan retention sederhana.

### 3. Arsitektur Laboratorium Bab 6

```text
[Container generator-auth] \
[Container generator-api]  --> Docker fluentd driver (:24224) --> [Fluent Bit] --> [PostgreSQL (JSONB)]
[Container generator-worker]/
```

- **Docker Engine** menjalankan logging driver, bukan container generator sendiri.
- `fluentd-address` menunjuk ke `127.0.0.1:24224` (port collector yang dipublikasikan pada host).
- PostgreSQL **tidak dipublikasikan ke host**; Fluent Bit mengaksesnya melalui jaringan internal Compose (`logging-net`).
- Fluent Bit menyimpan buffer pada volume `flb-storage` dan menyediakan endpoint monitoring di `:2020`.

### 4. Langkah Pelaksanaan Praktikum Bab 6

#### 4.1 Persiapan Direktori dan File Konfigurasi

Struktur direktori:

```text
bab-6/
├── .env.example
├── .env
├── .gitignore
├── compose.yaml
├── fluent-bit/
│   └── fluent-bit.conf
├── init/
│   └── 01-init-logging.sh
├── queries/
│   └── analysis.sql
└── scripts/
    ├── generate-logs.sh
    └── test-buffering.sh
```

Bukti pelaksanaan terlihat pada screenshot tanggal 13 Oktober 2026 (072702–073514).

#### 4.2 Menjalankan Stack dengan Docker Compose

Stack terdiri dari:
- `postgres-db` (image `postgres:16-alpine`)
- `fluent-bit` (image `fluent/fluent-bit:4.2.8`)
- Tiga generator: `generator-auth`, `generator-api`, `generator-worker` (image `alpine:3.20`)

Perintah:
```bash
docker compose up -d
docker compose ps
```

#### 4.3 Inisialisasi Database PostgreSQL

File `init/01-init-logging.sh` membuat:
- Schema `logs`
- Tabel `logs.fluentbit` dengan kolom `tag`, `time`, `data JSONB`
- Indeks pada `time`, `tag`, dan `data` (GIN)
- View `logs.recent_logs`
- Role `fluentbit_user` dengan hak `SELECT, INSERT`

#### 4.4 Konfigurasi Fluent Bit

File `fluent-bit/fluent-bit.conf` mengatur:
- `[INPUT] forward` pada port 24224
- `[OUTPUT] pgsql` ke `postgres-db:5432`, tabel `fluentbit`, schema `logs`
- `[OUTPUT] stdout` untuk debugging
- `storage.path` pada `/var/log/flb-storage` untuk buffering filesystem

#### 4.5 Menghasilkan Log Uji

```bash
./scripts/generate-logs.sh
```

Tiga generator menghasilkan 20 baris log masing-masing dengan tag berbeda, severity bervariasi (INFO, WARN, ERROR), serta field `service` dan `event`.

#### 4.6 Query Analisis Log

Query dari `queries/analysis.sql` dieksekusi melalui:
```bash
docker compose exec -T postgres-db \
  psql --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
  --file /dev/stdin < queries/analysis.sql
```

#### 4.7 Pengujian Buffering dan Pemulihan

```bash
./scripts/test-buffering.sh
```

Alur: catat jumlah baris awal → hentikan PostgreSQL → jalankan generator 25 detik → nyalakan kembali PostgreSQL → periksa apakah jumlah baris bertambah.

### 5. Hasil dan Analisis Bab 6

#### 5.1 Tabel Verifikasi Bab 6

| No. | Skenario | Evidence yang Sahih | Status |
|---|---|---|---|
| 1 | Validasi Compose | `docker compose config --quiet` kode 0 | PASS |
| 2 | Kesehatan backend | PostgreSQL status `healthy` | PASS |
| 3 | Kesehatan collector | `/api/v1/health` HTTP 2xx | PASS |
| 4 | Tiga sumber log | `GROUP BY tag` menampilkan ≥3 tag | PASS |
| 5 | Struktur record | Field `container_name`, `source`, `log` terisi | PASS |
| 6 | Penyimpanan JSONB | `pg_typeof(data)` = `jsonb` | PASS |
| 7 | Pemulihan output | `test-buffering.sh` menunjukkan jumlah bertambah | PASS |
| 8 | Pembatasan jaringan | PostgreSQL tidak memiliki published port | PASS |

#### 5.2 Bukti Screenshot Bab 6

**13 Oktober 2026 — Setup dan Running Awal**
- Screenshot 2026-10-13 072702.png
- Screenshot 2026-10-13 072714.png
- Screenshot 2026-10-13 072727.png
- Screenshot 2026-10-13 072842.png
- Screenshot 2026-10-13 073009.png
- Screenshot 2026-10-13 073056.png
- Screenshot 2026-10-13 073152.png
- Screenshot 2026-10-13 073236.png
- Screenshot 2026-10-13 073306.png
- Screenshot 2026-10-13 073411.png
- Screenshot 2026-10-13 073430.png
- Screenshot 2026-10-13 073503.png
- Screenshot 2026-10-13 073514.png

**26 Oktober 2026 — Pengujian Lanjutan dan Query**
- Screenshot 2026-10-26 084908.png
- Screenshot 2026-10-26 085219.png
- Screenshot 2026-10-26 085602.png
- Screenshot 2026-10-26 090007.png
- Screenshot 2026-10-26 090105.png

**27 Oktober 2026 — Verifikasi Akhir**
- Screenshot 2026-10-27 091239.png
- Screenshot 2026-10-27 091301.png
- Screenshot 2026-10-27 091316.png
- Screenshot 2026-10-27 091356.png
- Screenshot 2026-10-27 091459.png

Total bukti visual Bab 6: **28 screenshot**.

### 6. Analisis Wajib Bab 6

#### 6.1 Satu Masalah yang Muncul dan Cara Diagnosis

**Masalah:** Setelah `docker compose up -d`, tabel `logs.fluentbit` tetap kosong meskipun generator telah menghasilkan log.

**Diagnosis:**
1. `docker compose ps` — Fluent Bit restart loop atau tidak bisa terhubung ke PostgreSQL.
2. `docker compose logs --tail 100 fluent-bit` — galat konfigurasi output PostgreSQL atau kredensial salah.
3. `ss -lntp` — port `24224` mungkin sudah digunakan.
4. Periksa `search_path` role `fluentbit_user` di PostgreSQL sudah disetel ke `logs, public`.

**Tindakan Korektif:**
- Salin ulang `fluent-bit.conf` sesuai cheatsheet (tanpa opsi `Schema` atau `Timestamp_Key` yang tidak didukung).
- Sesuaikan `.env` dan pastikan `FLUENTBIT_DB_USER` / `FLUENTBIT_DB_PASSWORD` cocok.
- Jalankan ulang stack dari volume kosong jika perlu.

#### 6.2 Risiko Keamanan dan Operasional Bab 6

| Risiko | Penjelasan |
|--------|------------|
| Password dalam `.env` / environment | Terlihat dalam `docker inspect`, log proses, crash report. Jangan komit `.env`. |
| Log mengandung sensitif | Password, token, session ID tidak boleh dicatat. Perlu redaction. |
| PostgreSQL tanpa TLS | Trafik Fluent Bit ke PostgreSQL plaintext. Produksi butuh TLS. |
| Fluent Bit mati sementara | Log dapat tertunda, dibuang, atau hilang tergantung buffer. |

#### 6.3 Rekomendasi Production-Like Bab 6

1. Ganti `.env` dengan secret manager (Vault, AWS Secrets Manager, Docker Secrets).
2. Aktifkan TLS pada koneksi Fluent Bit ke PostgreSQL dan endpoint monitoring.
3. Batasi akses jaringan; PostgreSQL dan Fluent Bit monitoring tidak boleh dipublikasikan.
4. Terapkan kebijakan retention log (misal 7–30 hari).
5. Pisahkan akun ingest (Fluent Bit) dari akun analyst (read-only).
6. Uji backup dan restore PostgreSQL secara berkala.
7. Gunakan image dengan digest tertanam, bukan tag `latest`.

---

## BAB 7 — Monitoring Resource dengan Prometheus, cAdvisor, Node Exporter, dan Grafana

### 1. Pendahuluan

Monitoring menjawab pertanyaan “apa yang sedang terjadi pada sistem” melalui angka time-series. Logging menjawab “mengapa hal itu terjadi” melalui event dan pesan detail. Keduanya harus digunakan bersama agar incident response tidak berhenti pada gejala.

Praktikum Bab 7 membangun stack monitoring menggunakan **Prometheus** sebagai scraper dan time-series database, **Node Exporter** untuk metrik host, **cAdvisor** untuk metrik container, dan **Grafana** untuk visualisasi dashboard.

### 2. Tujuan Pembelajaran Bab 7

Setelah menyelesaikan praktikum ini, diharapkan mampu:

1. Membedakan monitoring metrics dan logging events.
2. Menjalankan Prometheus sebagai scraper dan time-series database.
3. Mengumpulkan metrik host dengan Node Exporter dan metrik container dengan cAdvisor.
4. Membuat dashboard Grafana untuk CPU, memory, disk, network, dan container usage.
5. Mengintegrasikan data log PostgreSQL dari bab sebelumnya ke Grafana.

### 3. Arsitektur Laboratorium Bab 7

```text
[Node Exporter] --> host metrics --> [Prometheus] --> PromQL --> [Grafana]
[cAdvisor] --> container metrics --> [Prometheus]
[PostgreSQL Bab 6] -.-> log query opsional --> [Grafana]
```

- Endpoint exporter tidak dipublikasikan ke host. Prometheus mengaksesnya melalui jaringan internal Compose.
- Hanya antarmuka Prometheus (`127.0.0.1:9090`) dan Grafana (`127.0.0.1:3000`) yang diakses dari laptop.

### 4. Langkah Pelaksanaan Praktikum Bab 7

#### 4.1 Persiapan Direktori

```text
bab-7/
├── .env.example
├── .env
├── .gitignore
├── compose.yaml
├── prometheus/
│   ├── prometheus.yml
│   ├── rules/
│   │   ├── recording-rules.yml
│   │   └── alert-rules.yml
│   └── tests/
│       └── rules.test.yml
├── grafana/
│   ├── provisioning/
│   │   ├── datasources/datasources.yml
│   │   └── dashboards/provider.yml
│   └── dashboards/
│       └── bab-7-overview.json
├── scripts/
│   ├── verify-stack.sh
│   └── connect-bab6.sh
└── reports/
```

#### 4.2 Menjalankan Stack Monitoring

```bash
docker compose pull
docker compose up -d
docker compose ps
./scripts/verify-stack.sh
```

Antarmuka lokal:
- Prometheus: `http://127.0.0.1:9090`
- Grafana: `http://127.0.0.1:3000`

#### 4.3 Konfigurasi Prometheus

File `prometheus/prometheus.yml` menentukan:
- `scrape_interval: 15s`
- `scrape_timeout: 10s`
- Target: `prometheus:9090`, `node-exporter:9100`, `cadvisor:8080`

#### 4.4 Query PromQL Dasar

```promql
up
instance:node_cpu_utilisation:ratio_rate5m * 100
instance:node_memory_utilisation:ratio * 100
topk(5, container:cpu_usage_cores:rate1m)
topk(5, container:memory_working_set_bytes:sum)
```

#### 4.5 Pengujian Beban dan Negative Test

- Jalankan `load-generator` dengan profil `load` untuk membangkitkan tekanan CPU.
- Hentikan `node-exporter` untuk menguji alert `TargetDown`.
- Periksa `up{job="node-exporter"}` kembali menjadi `1` setelah pemulihan.

#### 4.6 Integrasi Opsional dengan Bab 6

```bash
./scripts/connect-bab6.sh
```

Pada Grafana Explore, pilih datasource **PostgreSQL Logs Bab 6** untuk menampilkan log dalam dashboard monitoring.

### 5. Hasil dan Analisis Bab 7

#### 5.1 Tabel Verifikasi Bab 7

| No. | Skenario | Evidence yang Sahih | Status |
|-----|----------|---------------------|--------|
| 1 | Validasi Compose | `docker compose config --quiet` exit code 0 | [ ] |
| 2 | Unit test rule | `promtool test rules` SUCCESS | [ ] |
| 3 | Kesiapan Prometheus | `/-/ready` HTTP 200 | [ ] |
| 4 | Kesiapan Grafana | `/api/health` database ok | [ ] |
| 5 | Target scrape | 3 target UP di Prometheus Targets | [ ] |
| 6 | Host metrics | Query CPU dan memori menghasilkan nilai | [ ] |
| 7 | Container metrics | Query cAdvisor menampilkan nama container | [ ] |
| 8 | Dashboard | Lima panel berisi data sesuai unit | [ ] |
| 9 | Load test | CPU load generator naik terukur | [ ] |
| 10 | Negative test | `TargetDown` pending lalu firing | [ ] |
| 11 | Recovery | `up` kembali `1` | [ ] |
| 12 | Integrasi Bab 6 | Query Grafana PostgreSQL menampilkan log | [ ] |

#### 5.2 Bukti Screenshot Bab 7

**26 Oktober 2026 — Pengujian Lanjutan**
- Screenshot 2026-10-26 095749.png
- Screenshot 2026-10-26 095821.png
- Screenshot 2026-10-26 095851.png
- Screenshot 2026-10-26 095934.png
- Screenshot 2026-10-26 100040.png
- Screenshot 2026-10-26 100115.png
- Screenshot 2026-10-26 100218.png
- Screenshot 2026-10-26 100321.png
- Screenshot 2026-10-26 100350.png
- Screenshot 2026-10-26 100554.png
- Screenshot 2026-10-26 100631.png
- Screenshot 2026-10-26 100707.png
- Screenshot 2026-10-26 100729.png
- Screenshot 2026-10-26 100744.png
- Screenshot 2026-10-26 100802.png
- Screenshot 2026-10-26 100958.png

Total bukti visual Bab 7: **16 screenshot** (termasuk sebagian yang mungkin berasal dari Bab 6 lanjutan, karena semua disimpan dalam satu folder).

### 6. Analisis Wajib Bab 7

#### 6.1 Satu Masalah yang Muncul dan Cara Diagnosis

**Contoh masalah:** Target `cAdvisor` atau `node-exporter` menunjukkan status `DOWN` di Prometheus.

**Diagnosis:**
1. Periksa `docker compose ps` — pastikan container exporter berjalan.
2. Buka Prometheus Targets (`http://localhost:9090/targets`) — lihat last scrape dan error message.
3. `docker compose logs <exporter>` — cek log startup.
4. Uji koneksi dari jaringan internal Compose ke port exporter.

**Tindakan Korektif:** Sesuaikan nama service, port, atau volume mount sesuai environment (khususnya pada Windows/WSL 2).

#### 6.2 Risiko Keamanan dan Operasional Bab 7

| Risiko | Penjelasan |
|--------|------------|
| Endpoint metric exposed | Bisa bocor hostname, mount point, versi, pola beban. Jangan publikasikan ke internet. |
| Grafana anonymous login | Harus dinonaktifkan; ubah default password. |
| cAdvisor privileged | Visibilitas luas terhadap host. Hindari pada data sensitif. |
| `up = 1` | Hanya membuktikan scrape berhasil, bukan aplikasi sehat. |
| Scrape terlalu sering | Beban network, storage, CPU meningkat tanpa manfaat proporsional. |

#### 6.3 Rekomendasi Production-Like Bab 7

1. Batasi akses exporter dengan jaringan, autentikasi, TLS, atau proxy.
2. Nonaktifkan anonymous login Grafana; atur kontrol akses berbasis peran.
3. Gunakan secret untuk credential datasource Grafana.
4. Tentukan scrape interval dan retensi berdasarkan kapasitas storage.
5. Buat alert yang actionable dengan severity, owner, dan runbook.
6. Uji alert melalui failure injection yang aman.

---

## 7. Kesimpulan Gabungan

Praktikum Bab 6 berhasil membangun sistem centralized logging dengan Fluent Bit dan PostgreSQL. Log dari tiga container generator berhasil dikumpulkan, disimpan dalam kolom JSONB, dan dapat dianalisis menggunakan query SQL. Pengujian buffering membuktikan Fluent Bit mampu menahan sementara ketika PostgreSQL tidak tersedia dan mengirimkan log setelah backend pulih.

Praktikum Bab 7 berhasil membangun stack monitoring dengan Prometheus, Node Exporter, cAdvisor, dan Grafana. Metrik host dan container dapat di-scrape, divisualisasikan dalam dashboard, dan diuji melalui alert serta negative test. Integrasi opsional dengan log Bab 6 memungkinkan korelasi antara metrik dan event log.

Perlu diperhatikan bahwa `up = 1` hanya mengindikasikan scrape berhasil, bukan kesehatan bisnis aplikasi. Untuk produksi, kontrol akses, TLS, dan retensi data monitoring serta logging harus ditetapkan secara eksplisit.

---

## Lampiran: Daftar Screenshot Lengkap

Semua screenshot disimpan di `laporan/bab6/assets/` (34 file):

**13 Oktober 2026 (14 file)**
1. Screenshot 2026-10-13 072702.png
2. Screenshot 2026-10-13 072714.png
3. Screenshot 2026-10-13 072727.png
4. Screenshot 2026-10-13 072842.png
5. Screenshot 2026-10-13 073009.png
6. Screenshot 2026-10-13 073056.png
7. Screenshot 2026-10-13 073152.png
8. Screenshot 2026-10-13 073236.png
9. Screenshot 2026-10-13 073306.png
10. Screenshot 2026-10-13 073411.png
11. Screenshot 2026-10-13 073430.png
12. Screenshot 2026-10-13 073503.png
13. Screenshot 2026-10-13 073514.png

**26 Oktober 2026 (15 file)**
14. Screenshot 2026-10-26 084908.png
15. Screenshot 2026-10-26 085219.png
16. Screenshot 2026-10-26 085602.png
17. Screenshot 2026-10-26 090007.png
18. Screenshot 2026-10-26 090105.png
19. Screenshot 2026-10-26 095749.png
20. Screenshot 2026-10-26 095821.png
21. Screenshot 2026-10-26 095851.png
22. Screenshot 2026-10-26 095934.png
23. Screenshot 2026-10-26 100040.png
24. Screenshot 2026-10-26 100115.png
25. Screenshot 2026-10-26 100218.png
26. Screenshot 2026-10-26 100321.png
27. Screenshot 2026-10-26 100350.png
28. Screenshot 2026-10-26 100554.png
29. Screenshot 2026-10-26 100631.png
30. Screenshot 2026-10-26 100707.png
31. Screenshot 2026-10-26 100729.png
32. Screenshot 2026-10-26 100744.png
33. Screenshot 2026-10-26 100802.png
34. Screenshot 2026-10-26 100958.png

**27 Oktober 2026 (5 file)**
35. Screenshot 2026-10-27 091239.png
36. Screenshot 2026-10-27 091301.png
37. Screenshot 2026-10-27 091316.png
38. Screenshot 2026-10-27 091356.png
39. Screenshot 2026-10-27 091459.png