# Bab 6 – Centralized Logging dengan Fluent Bit dan PostgreSQL (PMB DevSecOps Lab)

## 1. Tujuan
- Logging terpusat pada container ephemeral.
- Mengirim log ke Fluent Bit lewat Docker fluentd driver.
- Menyimpan ke PostgreSQL (JSONB) dan membuat view analisis.
- Mensimulasi generator log (INFO‑CRITICAL).
- Query pencarian, distribusi, retention.
- Memahami dampak bila collector atau PostgreSQL tidak tersedia.

## 2. Arsitektur
```mermaid
flowchart TD
    Browser --> API[Registration API (127.0.0.1:8081)]
    API --> Auth[Auth Service (internal)]
    API --> DB[App DB (PostgreSQL)]
    API --> F[Fluent Bit (127.0.0.1:24226)]
    Auth -->|stdout| F
    Worker -->|stdout| F
    F -->|pgsql JSONB| LogDB[Log DB (PostgreSQL)]
    LogDB -->|query| UI[Status UI]
```

## 3. Langkah‑langkah
1. **Setup** – make setup → .env, role, schema, tabel logs.fluentbit, indeks, view, hak role fluentbit_writer.  
2. **Validate** – make validate → skrip parsing, docker compose config sukses.  
3. **Start** – make up → docker compose up -d --build; docker compose ps semua Up; cek health (curl -fsS http://127.0.0.1:8081/healthz, curl -fsS http://127.0.0.1:2025/api/v1/health).  
4. **Normal** – make normal (./scripts/demo-normal.sh). Login, isi formulir, verifikasi status VERIFIED via query pada app‑db. Screenshot (Screenshot 2026‑10‑29 080301.png).  
5. **Evidence** – make evidence (./scripts/collect-evidence.sh). File‑file di reports/ (compose‑ps.txt, metrics.json, registration‑status.txt, incident‑analysis.txt, config‑sha256.txt).  
6. **Insiden** – make incident (./scripts/demo-incident.sh). Tiga retry, status FAILED / VERIFY‑TIMEOUT. Screenshot (Screenshot 2026‑10‑29 080808.png).

## 4. Analisis Masalah (Timeout)
- **Gejala**: Log tidak sampai ke PostgreSQL ketika PostgreSQL dihentikan; Fluent Bit menampilkan retry & back‑pressure.  
- **Diagnosis**: docker compose logs --tail 200 fluent-bit menampilkan retry; docker volume ls menunjukkan volume fluent-bit-buffer masih ada; docker exec -T log-db psql -c "SELECT count(*) FROM logs.fluentbit;" tidak berubah selama PostgreSQL mati. Setelah docker compose start log-db, count naik (contoh 15 → 35).  
- **Penjelasan**: Buffer memampu data sampai PostgreSQL siap; ketika kembali, data terkirim at‑least‑once → duplikasi pada retry, total record meningkat.

## 5. Risiko Keamanan & Operasional
| Gejala | Kemungkinan | Dampak | Tindakan |
|--------|-------------|--------|----------|
| Buffer penuh / crash | Fluent Bit mati, volume tidak dikosongkan | Kehilangan log | Gunakan volume SSD, atur storage.backlog.mem_limit & storage.total_limit_size, alert bila penggunaan >80 % |
| Duplikasi log (at‑least‑once) | Retry setelah recovery | Naiknya ukuran DB, audit tercemar | Tambahkan event_id (UUID) di generator, filter penghapusan duplikat |
| Pencurian data sensitif | Log berisi password, token | Pelanggaran konfidensial | Filter redaction (record_modifier) atau hapus di aplikasi sebelum menghasilkan stdout |
| Port 24226 terbuka publik | Konfigurasi salah | Akses tidak berwenang | Bind hanya ke 127.0.0.1, gunakan firewall, aktifkan TLS untuk PostgreSQL |
| Retention terlalu lama | Tabel tumbuh tanpa batas | Biaya storage, risiko privasi | Jadwalkan hapus >30 hari, archive ke object storage dengan checksum |

## 6. Rekomendasi Produksi
1. **Persistent buffer** – gunakan volume SSD, atur storage.path & storage.total_limit_size, aktifkan storage.sync=always.  
2. **Exactly‑once / deduplication** – sisipkan event_id (UUID) di tiap log, gunakan filter penghapusan duplikat.  
3. **Redaction sensitif** – hapus/kucilkan field password, session_id, authorization_token sebelum log masuk ke Fluent Bit.  
4. **TLS & auth** – gunakan TLS untuk Fluent Bit → PostgreSQL, rotasi password tiap 90 hari, gunakan Docker secrets.  
5. **Retention policy** – skrip cron DELETE FROM logs.fluentbit WHERE time < now() - interval '30 days'; archive ke S3/MinIO dengan checksum SHA‑256.  
6. **Monitoring** – monitor metric Fluent Bit (buffer usage, retry count) dan PostgreSQL (disk space, replication lag); integrasi ke Grafana/Prometheus.  
7. **Testing** – jalankan make test-buffering.sh berkala, pastikan record bertambah setelah recovery dan tidak ada error kritis.

## 7. Kesimpulan
Log tercentralisasi dengan Fluent Bit dan PostgreSQL pada PMB memenuhi semua kriteria PASS/FAIL, menyediakan evidence visual, menganalisis satu masalah utama (timeout), serta memberikan rekomendasi untuk produksi.