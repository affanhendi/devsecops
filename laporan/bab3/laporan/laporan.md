# LAPORAN PRAKTIKUM BAB 3
## Docker Network, Volume, Bind Mount, tmpfs, dan Compose

**Nama**: ........................................................  
**NIM**: ..........................................................  
**Kelas**: ........................................................  
**Tanggal pelaksanaan**: 10 September 2026 & 22 September 2026  

---

## 1. Tujuan Praktikum

1. **User-Defined Bridge Network**: Membangun bridge network kustom (`172.20.0.0/16`) dan membuktikan *automatic DNS name resolution* antarkontainer tanpa ketergantungan IP statis.
2. **Karakteristik Mount Penyimpanan**: Menganalisis perbedaan persistensi, portabilitas, performa, dan risiko keamanan antara *Named Volume*, *Bind Mount*, dan *tmpfs*.
3. **Model Deklaratif Docker Compose**: Menyusun berkas `compose.yaml` multi-kontainer 3-tier (Nginx, Flask, PostgreSQL) dengan segmentasi jaringan (*frontend* dan *backend*).
4. **Dependensi & Healthcheck**: Mengonfigurasi dependensi cerdas (`depends_on: condition: service_healthy`) berbasis `pg_isready` guna menjamin kesiapan basis data sebelum aplikasi backend diinisialisasi.
5. **Lifecycle Management & DevSecOps**: Mengelola siklus hidup stack (`up`, `ps`, `logs`, `down`, `down -v`) serta mengevaluasi risiko kredensial plaintext dan proteksi *read-only mount* (`:ro`).

---

## 2. Dasar Teori & Perbandingan Storage Mount

Jaringan kontainer membentuk graf keterjangkauan (*reachability graph*) antarlayanan. Driver *user-defined bridge* menyediakan resolusi DNS otomatis berbasis nama service, isolasi tingkat jaringan, dan manajemen subnet terdedikasi. Dari sisi penyimpanan, Docker memisahkan *lifecycle* data dari kontainer melalui tiga mekanisme mount utama:

| Tipe Mount | Lokasi Penyimpanan | Persistensi Data | Ketergantungan Host | Skenario Penggunaan Utama | Risiko Keamanan & Operasional |
|---|---|---|---|---|---|
| **Named Volume** | `/var/lib/docker/volumes/` | Melampaui lifecycle kontainer | Rendah (Dikelola Engine) | Basis data persisten (PostgreSQL) | Terhapus oleh `docker compose down -v` |
| **Bind Mount** | Direktori/file host arbitrer | Mengikuti siklus berkas host | Tinggi (Tergantung path host) | Source code dev, file konfigurasi (`:ro`) | Kontainer dapat memodifikasi host jika tanpa `:ro` |
| **tmpfs Mount** | Memori RAM host / Swap | Hilang saat kontainer stop | Terikat Linux & RAM host | Data rahasia temporer, cache, token | Mengonsumsi RAM; data tidak persisten |

---

## 3. Langkah Praktikum & Bukti Eksekusi

### 3.1 User-Defined Bridge Network & Resolusi Nama DNS
Dibuat bridge network kustom `lab-net` dengan subnet `172.20.0.0/16`. Dua kontainer Nginx (`server-a` dan `server-b`) dihubungkan ke jaringan tersebut untuk menguji resolusi nama DNS internal.

```bash
docker network create --driver bridge --subnet 172.20.0.0/16 lab-net
docker run -d --name server-a --network lab-net nginx:alpine
docker run -d --name server-b --network lab-net nginx:alpine
docker exec server-a ping -c 3 server-b
docker rm -f server-a server-b
```

![Uji konektivitas dan resolusi DNS bridge network](../assets/Screenshot%202026-09-10%20070422.png)
*Gambar 1: Eksekusi ping membuktikan server-a berhasil meresolusi hostname server-b ke IP 172.20.0.3 tanpa packet loss.*

### 3.2 Manajemen Lifecycle Named Volume & Prosedur Backup
Named volume `data-vol` dibuat untuk menguji persistensi data melampaui masa hidup kontainer `writer`. Data log yang ditulis diverifikasi tetap utuh setelah kontainer dihapus, lalu dicadangkan ke dalam arsip tarball terkompresi menggunakan *temporary utility container*.

```bash
docker volume create data-vol
docker run -d --name writer -v data-vol:/app/data alpine:3.20 sh -c "while true; do date >> /app/data/log.txt; sleep 5; done"
sleep 15; docker rm -f writer
docker run --rm -v data-vol:/data alpine:3.20 cat /data/log.txt
docker run --rm -v data-vol:/source:ro -v $(pwd):/backup alpine:3.20 tar czf /backup/data-vol-backup.tar.gz -C /source .
```

![Persistensi volume dan backup tarball](../assets/Screenshot%202026-09-10%20070508.png)
*Gambar 2: Verifikasi isi log.txt tetap bertahan setelah kontainer dihapus dan berhasil diarsip menjadi data-vol-backup.tar.gz.*

### 3.3 Compose Multi-Container Nginx-Flask-PostgreSQL
Arsitektur multi-kontainer 3-tier didefinisikan ke dalam `compose.yaml` yang memadukan reverse proxy Nginx, aplikasi web Flask, dan basis data PostgreSQL 16 Alpine. Jaringan disederhanakan ke dalam dua zona isolasi: `frontend` (Nginx dan Flask) serta `backend` (Flask dan PostgreSQL). Layanan Flask dikonfigurasi menunggu kesiapan basis data melalui `depends_on: db: condition: service_healthy`.

```yaml
services:
  web:
    image: nginx:alpine
    ports: ["8080:80"]
    volumes:
      - ./html:/usr/share/nginx/html:ro
      - ./nginx.conf:/etc/nginx/conf.d/default.conf:ro
    networks: [frontend]
    depends_on: [app]
  app:
    build: ./app
    environment:
      DB_HOST: db
      DB_NAME: labdb
      DB_USER: labuser
      DB_PASS: labpass123
    networks: [frontend, backend]
    depends_on:
      db: { condition: service_healthy }
  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: labdb
      POSTGRES_USER: labuser
      POSTGRES_PASSWORD: labpass123
    volumes: [pg-data:/var/lib/postgresql/data]
    networks: [backend]
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U labuser -d labdb"]
      interval: 5s
      timeout: 5s
      retries: 5
volumes: { pg-data: }
networks: { frontend: , backend: }
```

### 3.4 Bukti Minimum Eksekusi Layanan
Stack multi-kontainer dijalankan dengan `docker compose up -d --build`. Status operasional, keterjangkauan endpoint, dan log inisialisasi diverifikasi sebagai bukti minimum eksekusi:

![Status operasional docker compose ps dan uji cURL API](../assets/Screenshot%202026-09-10%20070751.png)
*Gambar 3: Output docker compose ps menunjukkan ketiga kontainer aktif dengan db berstatus healthy, serta curl http://localhost:8080 berhasil mengembalikan status Connected to labdb.*

![Verifikasi respons HTTP cURL](../assets/Screenshot%202026-09-22%20081926.png)
*Gambar 4: Respons cURL -v membuktikan status HTTP/1.1 200 OK dari Nginx reverse proxy dengan payload koneksi database yang sukses.*

![Cuplikan log terpadu docker compose logs](../assets/Screenshot%202026-09-22%20081903.png)
*Gambar 5: Log gabungan membuktikan inisialisasi sukses PostgreSQL 16 Alpine, eksekusi pg_isready, dan kesiapan Flask melayani request.*

---

## 4. Analisis Masalah dan Diagnostik (Wajib)

Dalam proses inisialisasi stack multi-kontainer, ditemukan satu masalah operasional pada layanan basis data `db` (`postgres:16-alpine`):
- **Temuan Gejala**: Pada cuplikan log kontainer `db` (Gambar 5), tercatat peringatan sistem: `sh: locale: not found` dan `WARNING: no usable system locales were found`, serta `initdb: warning: enabling "trust" authentication for local connections`.
- **Metode Diagnosis**: Diagnosis dilakukan melalui analisis forensik log kontainer (`docker compose logs db`). Peringatan `locale: not found` terjadi karena Alpine Linux menggunakan pustaka `musl-libc` yang tidak menyertakan utilitas GNU `locale`. Akibatnya, PostgreSQL secara otomatis beralih (*fallback*) ke locale bawaan `POSIX/C.UTF-8`. Sementara itu, peringatan otentikasi *trust* muncul karena parameter lingkungan inisialisasi membolehkan koneksi lokal tanpa kata sandi pada tahap bootstrap.
- **Tindakan Korektif & Validasi**: Masalah ini bersifat non-fatal pada lingkungan praktikum. Uji kesehatan berkala `CMD-SHELL pg_isready -U labuser -d labdb` berhasil mengevaluasi soket lokal PostgreSQL setelah database beralih ke status *ready to accept connections* (PID 1). Status kontainer berhasil mencapai `healthy`, sehingga kontainer aplikasi `app` diizinkan memulai koneksi tanpa mengalami kegagalan *connection refused* atau *502 Bad Gateway*.

---

## 5. Analisis Risiko Keamanan & Operasional (DevSecOps) (Wajib)

1. **Risiko Kredensial Plaintext dalam Compose File**: Konfigurasi `POSTGRES_PASSWORD: labpass123` dan `DB_PASS: labpass123` didefinisikan secara telanjang (*hardcoded plaintext*). Berkas ini rentan terbaca melalui inspeksi kontainer (`docker inspect`), variabel lingkungan proses, log crash, atau repositori version control publik.
2. **Risiko Keamanan Bind Mount Tanpa Opsi Read-Only (`:ro`)**: Bind mount memetakan sistem berkas host langsung ke kontainer. Jika kontainer aplikasi berhasil dikompromikan (*remote code execution*), proses kontainer berhak memodifikasi, merusak, atau menyisipkan skrip berbahaya ke direktori host. Penggunaan `:ro` pada konfigurasi Nginx (`./nginx.conf:...:ro`) merupakan mitigasi wajib untuk menjaga integritas file konfigurasi host.
3. **Risiko Operasional Kehilangan Data Persisten (`down -v`)**: Perintah `docker compose down` hanya menghentikan kontainer dan menghapus jaringan bridge proyek. Namun, eksekusi perintah destruktif berflag volume `docker compose down -v` akan menghapus seluruh named volume proyek (`pg-data`). Tanpa prosedur pencadangan otomatis (seperti tarball backup pada Langkah 3.2), seluruh data bisnis basis data akan hilang permanen (*unrecoverable*).
4. **Prinsip Least Exposure pada Port Publishing**: Port basis data `5432` tidak dipublikasikan ke host (`ports`), melainkan hanya dapat diakses melalui jaringan internal `backend` oleh kontainer `app`. Hal ini membatasi *attack surface* dari pemindaian port eksternal (*port scanning*) pada antarmuka host.

---

## 6. Rekomendasi Perbaikan untuk Lingkungan Produksi (Wajib)

Bila arsitektur laboratorium ini akan diterapkan ke lingkungan *production-like*, beberapa perbaikan berikut wajib diimplementasikan:
1. **Manajemen Rahasia Terenkripsi (*Docker Secrets / Secret Manager*)**: Menghapus seluruh variabel rahasia dari berkas Compose dan menggantinya dengan Docker Secrets (`/run/secrets/db_password`) atau external vault (HashiCorp Vault, AWS Secrets Manager) dengan prinsip *zero-trust* dan rotasi berkala.
2. **Strategi Backup Otomatis & Driver Volume Eksternal**: Mengganti driver volume lokal dengan driver terkelola (*cloud storage plugin* seperti AWS EBS / NFS) yang mendukung *point-in-time snapshot*, serta menjadwalkan *cron job* berkala untuk eksekusi `pg_dump` otomatis dengan enkripsi data saat istirahat (*data-at-rest encryption*).
3. **Penerapan Pengguna Non-Root & Liveness/Readiness Probes**: Menjalankan kontainer aplikasi dan basis data menggunakan pengguna non-root dengan UID/GID eksplisit, serta memisahkan *healthcheck* menjadi *liveness* (apakah proses berjalan) dan *readiness* (apakah basis data telah menyelesaikan migrasi dan siap melayani lalu lintas).

---

## 7. Evaluasi dan Latihan Mandiri

1. **Mengapa user-defined bridge lebih baik daripada default bridge untuk multi-container app?**  
   *Jawaban*: User-defined bridge menyediakan DNS internal otomatis berbasis nama kontainer/layanan, mengisolasi lalu lintas dari kontainer asing di host yang sama, membolehkan konfigurasi subnet/MTU secara fleksibel, dan memungkinkan kontainer dihubungkan/diputuskan secara dinamis tanpa me-restart kontainer.
2. **Apa risiko bind mount terhadap keamanan host?**  
   *Jawaban*: Bind mount memberi kontainer akses langsung ke berkas host. Jika kontainer dieksploitasi atau dijalankan dengan hak root, proses kontainer dapat memodifikasi, menimpa berkas sistem sensitif host, atau memasang pintu belakang (*backdoor*). Risiko ini dicegah dengan opsi read-only (`:ro`) dan pengguna non-root.
3. **Apa perbedaan docker compose down dan docker compose down -v?**  
   *Jawaban*: `docker compose down` menghentikan dan menghapus kontainer beserta jaringan bridge proyek, namun membiarkan *named volume* tetap utuh sehingga data persisten terlindungi. Sebaliknya, `docker compose down -v` menghapus kontainer, jaringan, DAN seluruh *named volume* yang dideklarasikan, sehingga seluruh data persisten di dalamnya musnah.
4. **Kapan depends_on dengan healthcheck lebih tepat daripada depends_on biasa?**  
   *Jawaban*: `depends_on` biasa hanya menunggu proses kontainer dependensi aktif (*started*), bukan siap melayani (*ready*). Pada basis data yang memerlukan waktu inisialisasi dan migrasi, aplikasi dapat mengalami *crash* karena koneksi ditolak. `depends_on` dengan `condition: service_healthy` memastikan aplikasi baru dijalankan setelah probe kesehatan (seperti `pg_isready`) benar-benar sukses mengonfirmasi kesiapan layanan.
5. **Bagaimana strategi backup volume untuk database produksi?**  
   *Jawaban*: Strategi backup produksi mencakup: (1) Menjalankan utilitas pencadangan konsisten aplikasi secara terjadwal (`pg_dump` / `pg_basebackup`) untuk menghindari korupsi data; (2) Memanfaatkan snapshot storage/cloud berkala pada tingkat volume; (3) Mengompresi dan mengenkripsi berkas cadangan (*tar.gz.enc*); (4) Menyimpan salinan ke *offsite/cloud object storage* (S3) dengan kebijakan *immutability* dan retensi data; serta (5) Menguji prosedur *recovery/restore* secara berkala.

---

## 8. Kesimpulan

Praktikum Bab 3 membuktikan bahwa Docker Network, Volume, dan Compose merupakan pilar fundamental dalam orkestrasi kontainer modern. *User-defined bridge* menghadirkan *service discovery* yang andal tanpa IP statis, *named volume* menjamin persistensi data melampaui masa hidup kontainer, dan *Docker Compose* menyatukan seluruh dependensi, healthcheck, serta segmentasi jaringan dalam model deklaratif yang terkelola. Dari perspektif DevSecOps, penerapan prinsip *least exposure*, penggunaan *read-only bind mount*, serta pemisahan kredensial dari berkas konfigurasi menjadi prasyarat mutlak untuk menjamin keamanan dan keandalan sistem pada tingkat produksi.
