# LAPORAN PRAKTIKUM BAB 5
## Database Service di Docker: PostgreSQL

**Nama**: Mohammad Affan Hendi Firmansyah  
**NIM**: 3126640049  
**Kelas**: 1 IT-B S.Tr.Lj   
**Tanggal pelaksanaan**: 29 September 2026  

---

## 1. Tujuan Praktikum

1. **Orkestrasi Database Relasional & Web GUI Management**: Mengoperasikan layanan basis data PostgreSQL 16 Alpine (`postgres:16-alpine`) bersama antarmuka web pgAdmin 4 (`dpage/pgadmin4:latest`) dalam jaringan terisolasi (`data-net`) menggunakan konfigurasi variabel lingkungan `.env`.
2. **Otomasi Inisialisasi Skema via Entrypoint Script**: Mengotomatisasi pembuatan skema relasional tabel `students` dan indeks menggunakan file SQL pada direktori `/docker-entrypoint-initdb.d/01-schema.sql`.
3. **Validasi Persistensi Stateful Menggunakan Named Volume**: Mengelola persistensi data menggunakan *named volume* Docker (`pg-data` dan `pgadmin-data`) serta menguji integritas data melintasi siklus hidup kontainer (`down` dan `up`).
4. **Implementasi Healthcheck & Startup Dependency**: Menerapkan pemeriksaan kesiapan database berbasis perintah `pg_isready` dengan dependensi orkestrasi `condition: service_healthy` pada layanan pgAdmin.
5. **Strategi Backup Logis, Audit Checksum, & Uji Pemulihan Terisolasi**: Melakukan pencadangan logis menggunakan `pg_dump` format custom, memverifikasi integritas hash SHA-256, dan mengeksekusi uji pemulihan otomatis via `pg_restore` ke database terpisah (`labdb_restore_test`).
6. **Analisis DevSecOps & Tata Kelola Keamanan**: Menganalisis risiko penyimpanan kredensial plaintext, restriksi eksposur port loopback (`127.0.0.1`), pencegahan bencana `docker compose down -v`, serta rekomendasi arsitektur produksi.

---

## 2. Dasar Teori: Persistensi Data, Lifecycle, dan Integritas Database

Dalam arsitektur layanan berbasis kontainer, basis data relasional diklasifikasikan sebagai *stateful service* yang memerlukan perlakuan arsitektural berbeda dibandingkan aplikasi *stateless*:

| Parameter Evaluasi | Stateless Service (Web/App) | Stateful Service (PostgreSQL Database) | Implikasi DevSecOps |
|---|---|---|---|
| **Penyimpanan Data** | Ephemeral (hilang saat kontainer dihancurkan) | Persisten menggunakan Docker Named Volume (`pg-data`) | Data tidak boleh terikat pada siklus hidup kontainer (*container lifecycle*). |
| **Inisialisasi Data** | Setiap kontainer baru berjalan dari image mentah | Dieksekusi via `/docker-entrypoint-initdb.d/` hanya pada volume kosong | Perubahan skema lanjutan wajib dikelola melalui *database migration tools*. |
| **Kesiapan Layanan** | Port HTTP terbuka dan merespons probe web | Socket database siap melayani transaksi (`pg_isready`) | Healthcheck mencegah *race condition* aplikasi yang bergantung pada database. |
| **Strategi Backup** | Cukup menyimpan kode dan Dockerfile di Git | Logical backup (`pg_dump -Fc`) + audit checksum kriptografis SHA-256 | Backup harus diuji pemulihannya secara berkala (*restore verification drill*). |
| **Penanganan Bencana** | Otomatis dibuat ulang via orchestrator (`docker compose up`) | Memerlukan prosedur *Disaster Recovery* dengan target RPO dan RTO terukur | Larangan keras mengeksekusi `docker compose down -v` di lingkungan produksi. |

---

## 3. Langkah Praktikum & Bukti Eksekusi

### 3.1 Penyiapan Lingkungan, Variabel `.env`, dan Deklarasi Compose
Lingkungan kerja disiapkan pada direktori `~/docker-lab/bab-5/docker_devops` dengan struktur sub-direktori `init/`, `backup/`, `pgadmin/`, dan `scripts/`. Kredensial disimpan pada file `.env` dengan izin berkas ketat (`chmod 600`), sedangkan deklarasi multi-service diatur dalam `compose.yaml`:

```yaml
services:
  postgres-db:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: ${POSTGRES_DB}
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    ports: ["127.0.0.1:5432:5432"]
    volumes:
      - pg-data:/var/lib/postgresql/data
      - ./init:/docker-entrypoint-initdb.d:ro
    networks: [data-net]
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U $${POSTGRES_USER} -d $${POSTGRES_DB}"]
      interval: 5s
      timeout: 5s
      retries: 10
      start_period: 10s
    restart: unless-stopped
  pgadmin:
    image: dpage/pgadmin4:latest
    environment:
      PGADMIN_DEFAULT_EMAIL: ${PGADMIN_DEFAULT_EMAIL}
      PGADMIN_DEFAULT_PASSWORD: ${PGADMIN_DEFAULT_PASSWORD}
    ports: ["127.0.0.1:5050:80"]
    volumes:
      - pgadmin-data:/var/lib/pgadmin
      - ./pgadmin/servers.json:/pgadmin4/servers.json:ro
    networks: [data-net]
    depends_on:
      postgres-db: { condition: service_healthy }
    restart: unless-stopped
volumes: { pg-data: , pgadmin-data: }
networks: { data-net: { driver: bridge } }
```

### 3.2 Inisialisasi Otomatis Skema Basis Data
Skrip `init/01-schema.sql` dipetakan ke `/docker-entrypoint-initdb.d:ro`. Saat pertama kali container `postgres-db` dijalankan pada volume kosong, PostgreSQL secara otomatis menjalankan skrip DDL/DML tersebut:

![Log Inisialisasi Skema SQL](../assets/Screenshot%202026-09-29%20103509.png)
*Gambar 1: Output log kontainer membuktikan eksekusi 01-schema.sql, pembuatan tabel students, insert data awal, dan transisi ke status ready.*

### 3.3 Akses Dashboard Administrasi pgAdmin 4
Layanan pgAdmin dijalankan pada port loopback 5050 dan membaca konfigurasi otomatis dari `pgadmin/servers.json` yang meregistrasikan server PostgreSQL Bab 5:

![Dashboard GUI pgAdmin 4](../assets/Screenshot%202026-09-29%20105153.png)
*Gambar 2: Antarmuka Web GUI pgAdmin 4 pada port 5050 menampilkan server PostgreSQL Bab 5 dalam grup Laboratorium DevSecOps.*

### 3.4 Validasi Skema Relasional dan Data Awal via CLI `psql`
Pemeriksaan struktur skema dan data awal dilakukan langsung di dalam kontainer database menggunakan utility terminal `psql`:

![Verifikasi Skema CLI psql](../assets/Screenshot%202026-09-29%20105215.png)
*Gambar 3: Verifikasi CLI psql membuktikan relasi tabel students terbentuk sempurna dan memuat 2 baris rekaman awal mahasiswa.*

### 3.5 Pengujian Ketahanan Persistensi Named Volume
Untuk membuktikan persistensi data, ditambahkan baris baru (`31230003`, 'Mahasiswa Tiga'). Seluruh kontainer dan jaringan kemudian dihancurkan menggunakan `docker compose down`, lalu dihidupkan kembali via `docker compose up -d`:

![Uji Persistensi Volume](../assets/Screenshot%202026-09-29%20105403.png)
*Gambar 4: Pengujian persistensi volume: record ketiga tersimpan utuh setelah siklus docker compose down dan docker compose up -d.*

### 3.6 Pembuatan Logical Backup dan Audit Integritas SHA-256
Pencadangan basis data dieksekusi melalui skrip `./scripts/backup.sh` menggunakan utility `pg_dump` dengan format custom archive (`-Fc`) serta verifikasi kriptografis:

![Eksekusi Backup dan Checksum](../assets/Screenshot%202026-09-29%20105427.png)
*Gambar 5: Eksekusi skrip backup otomatis menghasilkan file dump biner custom (3.4 KB) dan checksum SHA-256 terverifikasi OK.*

### 3.7 Validasi Pemulihan Data (Restore Test) pada Database Terisolasi
Validasi keandalan cadangan diuji menggunakan skrip `./scripts/restore-test.sh` yang memulihkan data ke database baru `labdb_restore_test` tanpa menyentuh database operasional utama:

![Validasi Restore Terisolasi](../assets/Screenshot%202026-09-29%20105456.png)
*Gambar 6: Uji restore terisolasi ke database labdb_restore_test membuktikan pemulihan 3 record data dengan integritas sempurna.*

---

## 4. Analisis Masalah dan Diagnostik (Wajib)

1. **Mekanisme Skip Inisialisasi Script pada Volume Non-Kosong**:
   - *Temuan*: Jika berkas SQL pada direktori `init/` diubah setelah stack pertama kali berjalan, perubahan skema tidak diterapkan saat kontainer direstart.
   - *Diagnosis*: Entrypoint PostgreSQL (`docker-entrypoint.sh`) memeriksa keberadaan direktori `$PGDATA/base`. Jika direktori tersebut telah berisi berkas data, proses inisialisasi sengaja dilewati (`skipping initialization`) guna menjaga integritas data eksisting dari bahaya penimpaan (*data overwrite*). Pada fase operasional, perubahan struktur tabel harus dikelola melalui migrasi skema (*schema migration*), bukan skrip init.
2. **Resolusi Hostname Antar-Kontainer pgAdmin (`postgres-db` vs `localhost`)**:
   - *Temuan*: Mengonfigurasi pgAdmin untuk menghubungi `localhost:5432` menghasilkan kegagalan koneksi (*connection refused*).
   - *Diagnosis*: Di dalam arsitektur multi-kontainer Docker, setiap kontainer memiliki *network namespace* dan antarmuka loopback tersendiri. Di dalam kontainer pgAdmin, `localhost` merujuk ke kontainer pgAdmin itu sendiri. Untuk menghubungkan kedua layanan, pgAdmin wajib menggunakan hostname layanan Compose `postgres-db` yang di-resolve secara otomatis oleh Docker embedded DNS engine pada network bridge `data-net`.
3. **Manajemen Variabel Lingkungan & Mitigasi Kesalahan Penulisan**:
   - *Temuan*: Potensi kesalahan penulisan (*typo*) variabel lingkungan pada berkas `.env` (misal `PGADMIN_DEAFAULT_EMAIL`) dapat menyebabkan nilai fallback default yang tidak diinginkan.
   - *Diagnosis*: Docker Compose melakukan interpolasi variabel tanpa validasi semantik bawaan jika variabel tidak dipetakan dengan tepat. Diagnostik dilakukan menggunakan perintah `docker compose config` untuk memvalidasi teks konfigurasi akhir sebelum deployment, menerapkan `chmod 600 .env` untuk proteksi izin berkas, serta mendaftarkan `.env` dan `backup/*.dump` ke dalam `.gitignore` guna mencegah kebocoran kredensial ke repositori publik.

---

## 5. Analisis Risiko Keamanan & Operasional (DevSecOps) (Wajib)

1. **Risiko Kredensial Plaintext pada Environment Variable**: Menyimpan password langsung pada file Compose atau environment variable kontainer berisiko tinggi terekspos melalui `docker inspect`, log orchestrator, atau pembacaan file sistem `/proc/1/environ`. Pada arsitektur aman, password harus dipasok via *Docker Secrets* (`_FILE` convention) atau solusi Secret Manager terenkripsi (HashiCorp Vault / AWS Secrets Manager).
2. **Paparan Port Database Host (Port Binding 5432)**: Memublikasikan port 5432 ke antarmuka publik (`0.0.0.0`) mengundang serangan brute force dan eksploitasi remote. Konfigurasi Compose pada praktikum ini menerapkan prinsip *least exposure* dengan membatasi binding ke loopback `127.0.0.1:5432:5432`. Pada arsitektur produksi yang ideal, port database sama sekali tidak dipublikasikan ke host, melainkan hanya diakses oleh backend internal melalui jaringan privat overlay/bridge.
3. **Radius Ledakan Superuser & Prinsip Least Privilege**: Penggunaan akun superuser `labuser` untuk seluruh operasi data meningkatkan risiko eskalasi jika terjadi celah SQL Injection pada aplikasi. Prinsip DevSecOps mewajibkan pemisahan akun: peran administratif (DDL/migrasi) terpisah dari peran aplikasi runtime (DML terbatas pada SELECT, INSERT, UPDATE, DELETE tanpa izin DROP/ALTER).
4. **Bencana Kehilangan Data Permanen via Perintah `docker compose down -v`**: Eksekusi perintah `down` dengan flag `-v` (*volumes*) akan menghapus *named volume* secara permanen tanpa dialog konfirmasi. Jika tidak diimbangi prosedur pencadangan otomatis di luar host, data transaksi bisnis akan hilang total tanpa kemungkinan pemulihan (*catastrophic data loss*).

---

## 6. Rekomendasi Perbaikan untuk Lingkungan Produksi (Wajib)

1. **Manajemen Kredensial Dinamis via Docker Secrets / Vault**: Hilangkan seluruh variabel password plaintext dari berkas Compose dan gunakan mekanisme Docker Secrets (`POSTGRES_PASSWORD_FILE=/run/secrets/pg_password`) dengan rotasi kunci otomatis berkala.
2. **Strategi Backup 3-2-1 dan Point-in-Time Recovery (PITR)**: Terapkan strategi pencadangan modern menggunakan continuous *Write-Ahead Log (WAL) archiving* dengan perkakas enterprise seperti `pgBackRest` atau `Barman`. Simpan 3 salinan data pada 2 media berbeda dengan 1 salinan tersimpan secara *off-site* di cloud object storage terenkripsi (AWS S3/MinIO), sehingga memungkinkan pemulihan data hingga detik spesifik sebelum insiden terjadi.
3. **Database Connection Pooling (PgBouncer)**: Di depan PostgreSQL, tempatkan proxy connection pooler seperti PgBouncer untuk mendaur ulang koneksi TCP, mencegah kehabisan sumber daya memori (*resource starvation*), dan menangani lonjakan koneksi konkurensi ribuan microservices.
4. **Enkripsi Komprehensif (In-Transit & At-Rest)**: Wajibkan enkripsi TLS penuh pada koneksi client-database (`ssl = on` dan sertifikat CA terpercaya) serta terapkan enkripsi penyimpanan sistem berkas (*volume encryption*) pada volume storage fisik di tingkat host/SAN.
5. **Otomasi Disaster Recovery Drill dalam Pipeline CI/CD**: Jadwalkan pengujian restore otomatis secara berkala di lingkungan staging untuk mengukur *Recovery Time Objective* (RTO) dan *Recovery Point Objective* (RPO) aktual, memastikan cadangan selalu dalam kondisi valid dan siap pakai.

---

## 7. Evaluasi dan Latihan Mandiri

1. **Mengapa init script tidak dijalankan ulang saat volume lama masih ada?**  
   *Jawaban*: Skrip inisialisasi pada `/docker-entrypoint-initdb.d/` dirancang oleh skrip bootstrap PostgreSQL resmi (`docker-entrypoint.sh`) untuk hanya berjalan satu kali pada fase awal pembentukan klaster database, yaitu ketika direktori data (`PGDATA`) masih sepenuhnya kosong dan belum memiliki berkas metadata klaster `PG_VERSION`. Jika direktori data telah terisi basis data dari eksekusi sebelumnya, entrypoint secara sengaja melewati (*skip*) proses inisialisasi demi melindungi integritas data eksisting dari bahaya penimpaan (*overwrite*), tabrakan skema (*constraint violation*), atau korupsi data. Untuk perubahan struktur skema selanjutnya, pengembang harus menerapkan migrasi skema database terkelola (seperti Flyway, Liquibase, atau Prisma).
2. **Apa risiko menaruh password database pada docker-compose.yml?**  
   *Jawaban*: Menaruh password secara mentah (*hardcoded plaintext*) pada `docker-compose.yml` membuka kerentanan keamanan serius: (1) Kata sandi berisiko tinggi bocor ke publik atau pihak tidak berwenang melalui riwayat repositori Git (*commit history*); (2) Kredensial dapat dibaca oleh pengguna non-root lokal melalui perintah inspeksi sistem `docker inspect` atau `docker compose config`; (3) Kredensial muncul secara gamblang pada log CI/CD atau dashboard orchestrator; dan (4) Sangat mempersulit prosedur rotasi kredensial berkala. Praktik terbaik mewajibkan penggunaan file `.env` dengan izin ketat (`chmod 600`), variabel environment rahasia pada CI/CD runner, atau *Docker Secrets*.
3. **Bagaimana cara membuktikan backup dapat dipulihkan?**  
   *Jawaban*: Keberadaan berkas cadangan di media penyimpanan tidak membuktikan bahwa data dapat dipulihkan (*an untested backup is not a backup*). Cara membuktikannya adalah melalui pengujian pemulihan aktif (*restore drill*) secara berkala ke database uji terisolasi (misal `labdb_restore_test`), yang meliputi: (1) Validasi integritas berkas menggunakan checksum kriptografis hash SHA-256 (`sha256sum --check`); (2) Eksekusi utilitas `pg_restore` tanpa pesan kesalahan fatal; (3) Verifikasi kuantitatif keutuhan record dengan menghitung jumlah baris data (`SELECT COUNT(*)`); (4) Verifikasi kualitatif integritas relasional skema, constraint, dan indeks; serta (5) Pencatatan durasi pemulihan untuk memastikan kesesuaian dengan target RTO (*Recovery Time Objective*).
4. **Apa bedanya logical backup pg_dump dan backup filesystem volume mentah?**  
   *Jawaban*:  
   - **Logical Backup (`pg_dump`)**: Mengekstrak struktur DDL dan data DML ke dalam berkas teks SQL atau arsip biner custom (`-Fc`). Keunggulannya adalah memiliki portabilitas tinggi (dapat dipulihkan ke versi arsitektur OS, platform hardware, atau versi major PostgreSQL yang lebih baru), ukuran ringkas berkat fitur kompresi bawaan, serta mendukung pemulihan granular (per-tabel). Kelemahannya: waktu dump dan restore lebih lambat pada basis data berskala sangat besar (terabyte).  
   - **Backup Filesystem Volume Mentah (Physical/Raw Volume)**: Menyalin blok data mentah direktori `PGDATA` (snapshot volume EBS/LVM atau `tar`/`rsync`). Keunggulannya adalah proses pencadangan dan pemulihan sangat cepat untuk basis data berskala masif. Kelemahannya: berisiko korupsi tinggi jika dibuat saat database sedang aktif tanpa *write-ahead log* (WAL) archiving yang konsisten (*crash-inconsistent*), tidak portabel (terikat ketat pada arsitektur CPU dan versi PostgreSQL yang identik), serta tidak mendukung pemulihan parsial objek tertentu.
5. **Apa dampak docker compose down -v terhadap database?**  
   *Jawaban*: Opsi `-v` (*volumes*) pada perintah `docker compose down -v` menginstruksikan Docker Compose untuk tidak hanya menghentikan dan menghapus kontainer serta jaringan bridge, melainkan juga secara paksa dan permanen **menghapus seluruh named volume yang terdaftar** (yaitu `pg-data` dan `pgadmin-data`). Dampaknya adalah seluruh tabel skema, indeks, konfigurasi server pgAdmin, dan seluruh baris data transaksional yang tersimpan di dalam volume tersebut akan musnah total dan tidak dapat dikembalikan dari disk host. Jika dijalankan di lingkungan produksi tanpa cadangan eksternal teruji, tindakan ini memicu bencana kehilangan data permanen (*catastrophic data loss*).

---

## 8. Kesimpulan

Praktikum Bab 5 membuktikan keberhasilan penggelaran layanan basis data PostgreSQL 16 Alpine dan pgAdmin 4 menggunakan Docker Compose dengan arsitektur berorientasi ketahanan (*resilience*) dan tata kelola DevSecOps. Mekanisme otomasi inisialisasi skema `/docker-entrypoint-initdb.d/` berhasil mengeksekusi skrip SQL saat volume pertama kali dibuat, sementara penggunaan *Docker Named Volume* (`pg-data`) terbukti mempertahankan persistensi data mahasiswa secara sempurna melintasi siklus penghentian dan penghapusan kontainer (`docker compose down` dan `up -d`). Keandalan sistem diperkuat oleh implementasi healthcheck `pg_isready` dengan dependensi startup `service_healthy`. Prosedur pencadangan logis `pg_dump` format custom terverifikasi aman melalui audit hash SHA-256 dan berhasil diuji pemulihannya secara terisolasi ke database `labdb_restore_test` dengan integritas 100%. Dari sisi DevSecOps, isolasi jaringan privat `data-net`, restriksi port binding ke loopback host `127.0.0.1`, perlindungan hak akses `.env` (`chmod 600`), mitigasi risiko `down -v`, serta perancangan pemisahan hak akses superuser telah meletakkan fondasi operasional database yang aman dan andal untuk implementasi lingkungan produksi.
