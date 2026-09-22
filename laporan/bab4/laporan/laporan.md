# LAPORAN PRAKTIKUM BAB 4
## Web Service Container: Apache, Nginx, Reverse Proxy, dan TLS

**Nama**: ........................................................  
**NIM**: ..........................................................  
**Kelas**: ........................................................  
**Tanggal pelaksanaan**: 22 September 2026  

---

## 1. Tujuan Praktikum

1. **Deployment Web Server Apache & Nginx**: Mengoperasikan Apache (`httpd:2.4-alpine`) dan Nginx (`nginx:alpine`) dalam kontainer dengan konfigurasi kustom dan bind mount sistem berkas.
2. **Implementasi Reverse Proxy & Ingress Gateway**: Mengonfigurasi Nginx sebagai gerbang tunggal yang memisahkan akses publik dari backend internal (`/` ke Apache dan `/api/` ke Flask).
3. **Simulasi TLS/HTTPS & Redirection 301**: Menerapkan sertifikat TLS *self-signed*, menegosiasikan enkripsi modern TLS 1.3 pada port 8443, dan memvalidasi pengalihan otomatis HTTP (port 8080) ke HTTPS (port 8443).
4. **Isolasi Jaringan & Penerusan Header**: Membatasi paparan port (*least exposure*) dengan mengisolasi backend pada jaringan privat (`web-net`) serta meneruskan header identitas (`X-Forwarded-For`, `X-Forwarded-Proto`, `Host`).
5. **Analisis Keamanan DevSecOps**: Mengevaluasi proteksi *read-only mount* (`:ro`), risiko private key pada bind mount, serta mitigasi *header spoofing*.

---

## 2. Dasar Teori: Komparasi Apache httpd dan Nginx

Dalam arsitektur *containerized web services*, Apache dan Nginx memiliki karakteristik yang saling melengkapi:

| Parameter Evaluasi | Apache HTTP Server (`httpd`) | Nginx Reverse Proxy | Analisis Peran Arsitektur |
|---|---|---|---|
| **Model Arsitektur** | Process/thread-per-request (MPM Event/Worker) | Event-driven, non-blocking asynchronous | Nginx unggul menangani ribuan koneksi konkuren; Apache unggul pada kompatibilitas modul. |
| **Direktori Konfigurasi**| `/usr/local/apache2/conf` | `/etc/nginx` | Nginx menggunakan blok `server` & `location`; Apache berbasis direktif XML-like. |
| **Document Root** | `/usr/local/apache2/htdocs` | `/usr/share/nginx/html` | Apache berperan sebagai *origin server* statis; Nginx sebagai *ingress*. |
| **Fitur Reverse Proxy** | Modul `mod_proxy` | Direktif bawaan `proxy_pass` | Nginx dirancang natively sebagai reverse proxy dengan overhead memori minimal. |
| **Peran pada Praktikum** | Penyaji konten web internal (`/`) | TLS Ingress & Routing Gateway (`/` dan `/api/`) | Pola kombinasi memisahkan terminasi TLS dari eksekusi backend. |

---

## 3. Langkah Praktikum & Bukti Eksekusi

### 3.1 Arsitektur Multi-Service Compose
Arsitektur dideklarasikan dalam berkas `compose.yaml` yang menghubungkan layanan `proxy`, `apache-web`, dan `flask-app` ke dalam jaringan bridge `web-net`. Hanya kontainer `proxy` yang memublikasikan port ke host (`8080` dan `8443`):

```yaml
services:
  proxy:
    image: nginx:alpine
    ports: ["8080:80", "8443:443"]
    volumes:
      - ./nginx/conf:/etc/nginx/conf.d:ro
      - ./certs:/etc/nginx/certs:ro
      - ./logs/nginx:/var/log/nginx
    networks: [web-net]
    depends_on:
      apache-web: { condition: service_started }
      flask-app: { condition: service_healthy }
  apache-web:
    image: httpd:2.4-alpine
    volumes: [./apache/sites:/usr/local/apache2/htdocs:ro]
    networks: [web-net]
  flask-app:
    build: ./app
    networks: [web-net]
networks: { web-net: }
```

### 3.2 Status Operasional Layanan dan Batas Paparan Port
Stack dijalankan dengan `docker compose up -d --build`. Status operasional kontainer diperiksa melalui `docker compose ps`:

![Status operasional docker compose ps](../assets/Screenshot%202026-09-22%20084013.png)
*Gambar 1: Output docker compose ps membuktikan ketiga kontainer berstatus Up (flask-app berstatus healthy), dengan port 8080 dan 8443 hanya dipublikasikan oleh proxy.*

### 3.3 Cuplikan Log Terpadu Sistem
Log gabungan dari ketiga kontainer diperiksa via `docker compose logs` untuk memvalidasi inisialisasi worker process dan proteksi sistem berkas:

![Cuplikan log terpadu docker compose logs](../assets/Screenshot%202026-09-22%20085119.png)
*Gambar 2: Log gabungan membuktikan Apache MPM event aktif, Gunicorn menjalankan 2 worker process, dan skrip Nginx mendeteksi read-only filesystem pada default.conf.*

### 3.4 Pengujian Pengalihan HTTP 301 ke HTTPS
Akses HTTP biasa pada port 8080 diuji dengan `curl -I http://localhost:8080`:

![Pengujian redirection HTTP 301](../assets/Screenshot%202026-09-22%20085134.png)
*Gambar 3: Respons HTTP/1.1 301 Moved Permanently dengan Location: https://localhost:8443/ membuktikan aturan redirect Nginx bekerja sempurna.*

### 3.5 Pengujian Akses HTTPS Apache via Nginx Reverse Proxy
Pengujian jalur root `/` dilakukan melalui HTTPS terenkripsi (`curl -k -i https://localhost:8443`):

![Akses Apache via HTTPS Nginx](../assets/Screenshot%202026-09-22%20085143.png)
*Gambar 4: Respons HTTP/1.1 200 OK menyajikan konten HTML Apache dengan header keamanan X-Frame-Options, X-Content-Type-Options, dan CSP.*

### 3.6 Pengujian Akses Endpoint API Microservice Flask
Pengujian perutean API dilakukan ke endpoint `/api` (`curl -k https://localhost:8443/api`):

![Akses API Flask via Reverse Proxy](../assets/Screenshot%202026-09-22%20085154.png)
*Gambar 5: Respons JSON dari Flask mengonfirmasi penerusan header X-Forwarded-Proto bernilai https dan client_ip teridentifikasi.*

### 3.7 Validasi Kriptografi Handshake TLS 1.3 via OpenSSL
Audit cipher suite dan sertifikat dilakukan melalui `openssl s_client -connect localhost:8443`:

![Validasi TLS 1.3 via OpenSSL](../assets/Screenshot%202026-09-22%20085220.png)
*Gambar 6: Sesi TLS menegosiasikan protokol TLSv1.3, cipher TLS_AES_256_GCM_SHA384, dan algoritma pertukaran kunci hybrid X25519MLKEM768.*

---

## 4. Analisis Masalah dan Diagnostik (Wajib)

Selama pelaksanaan praktikum, ditemukan tiga kondisi diagnostik penting yang dianalisis:
1. **Peringatan FQDN Apache (`AH00558`)**:
   - *Temuan*: Pada log Apache (Gambar 2), muncul pesan `AH00558: httpd: Could not reliably determine the server's fully qualified domain name, using 172.21.0.2`.
   - *Diagnosis*: Direktif `ServerName` belum didefinisikan secara eksplisit di berkas `httpd.conf`, sehingga daemon Apache otomatis menggunakan alamat IP kontainer sebagai fallback. Masalah ini bersifat non-fatal, namun pada lingkungan produksi harus ditetapkan direktif `ServerName localhost:80` untuk mencegah perilaku redirection yang anomali.
2. **Peringatan Modifikasi Sistem Berkas Nginx**:
   - *Temuan*: Skrip inisialisasi Nginx mencatat `can not modify /etc/nginx/conf.d/default.conf (read-only file system?)`.
   - *Diagnosis*: Skrip bawaan `10-listen-on-ipv6-by-default.sh` mencoba menyuntikkan listen IPv6 ke konfigurasi default. Karena volume dipasang dengan atribut `:ro` (*read-only*), penulisan ditolak oleh kernel. Hal ini justru memvalidasi bahwa mekanisme isolasi berkas berhasil melindungi konfigurasi host dari modifikasi kontainer.
3. **Peringatan Verifikasi Sertifikat Self-Signed**:
   - *Temuan*: Perintah `curl` mewajibkan flag `-k` (*insecure*) dan OpenSSL mencatat `verify error:num=18:self-signed certificate`.
   - *Diagnosis*: Sertifikat dibuat secara mandiri (*self-signed*) tanpa penandatanganan oleh *Certificate Authority* (CA) terpercaya yang ada pada trust store lokal sistem. Pada pengujian lab hal ini wajar, namun di produksi wajib menggunakan sertifikat resmi.

---

## 5. Analisis Risiko Keamanan & Operasional (DevSecOps) (Wajib)

1. **Risiko Private Key pada Bind Mount**: Berkas kunci privat TLS (`lab.key`) dipetakan via bind mount biasa. Jika host atau kontainer memiliki kelemahan perizinan berkas (*file permission lax*), kunci privat dapat diekstraksi penyerang untuk mendekripsi rekaman lalu lintas jaringan (*eavesdropping*). Kunci privat seharusnya dikelola melalui *Docker Secrets* atau *Secret Manager* terenkripsi.
2. **Risiko Header Spoofing & Trust Boundary**: Microservice Flask mengandalkan header `X-Forwarded-Proto` untuk mendeteksi skema koneksi aman. Jika kontainer `flask-app` tidak diisolasi dalam jaringan privat dan portnya dibuka ke host, penyerang dapat memotong proxy (*bypass*) dan menyuntikkan header palsu untuk mengelabui logika otorisasi aplikasi.
3. **Penerapan Header Keamanan HTTP**: Nginx dikonfigurasi menyuntikkan `X-Frame-Options: DENY` (mitigasi serangan Clickjacking), `X-Content-Type-Options: nosniff` (mitigasi MIME-confusion attack), dan `Content-Security-Policy: "default-src 'self'"` (mitigasi XSS).
4. **Analisis Kriptografi TLS 1.3 & Post-Quantum Key Exchange**: Sesi HTTPS menegosiasikan `TLS_AES_256_GCM_SHA384` dengan algoritma pertukaran kunci hybrid `X25519MLKEM768`. Kombinasi kurva eliptik X25519 dan kisi matematis ML-KEM-768 memberikan ketahanan terhadap ancaman komputasi kuantum di masa depan (*quantum-resistant cryptography*).

---

## 6. Rekomendasi Perbaikan untuk Lingkungan Produksi (Wajib)

1. **Sertifikat CA Publik Terpercaya & ACME**: Ganti sertifikat *self-signed* dengan sertifikat dari CA publik (Let's Encrypt / DigiCert) menggunakan protokol ACME (*Certbot*) untuk rotasi sertifikat otomatis sebelum masa berlaku 90 hari berakhir.
2. **Penyimpanan Kunci via Docker Secrets / Vault**: Hilangkan bind mount direktori `certs` dan gunakan mekanisme *Docker Secrets* (`/run/secrets/tls_key`) dengan permission `0400` atau integrasi HashiCorp Vault.
3. **Enkripsi End-to-End (mTLS)**: Untuk kepatuhan standar industri (PCI-DSS / HIPAA), terapkan TLS timbal balik (*mutual TLS*) antara Nginx reverse proxy dan backend Flask guna mencegah penyadapan lalu lintas pada jaringan internal host.
4. **Pengguna Non-Root & Pembatasan Sumber Daya**: Pastikan seluruh kontainer (khususnya Flask dan Nginx) dijalankan dengan pengguna non-root (UID 10001) serta dibatasi alokasi CPU dan memorinya via blok `deploy.resources.limits`.

---

## 7. Evaluasi dan Latihan Mandiri

1. **Mengapa reverse proxy tidak seharusnya menjalankan semua logic aplikasi?**  
   *Jawaban*: Reverse proxy dirancang untuk menangani tugas tingkat transport dan protokol (seperti terminasi TLS, perutean jalur URL, kompresi respons, caching aset statis, dan mitigasi DDoS). Menjalankan logika bisnis kompleks di reverse proxy akan membebani siklus event-loop non-blocking, meningkatkan latensi koneksi, mengaburkan batas tanggung jawab arsitektural (*separation of concerns*), dan memperluas *attack surface* pada lapisan terluar jaringan.
2. **Apa perbedaan TLS termination dan end-to-end TLS?**  
   *Jawaban*: Pada *TLS termination*, koneksi terenkripsi HTTPS didekripsi di reverse proxy, lalu trafik diteruskan ke backend dalam bentuk HTTP teks biasa (unencrypted) melalui jaringan privat. Pada *end-to-end TLS*, enkripsi dipertahankan dari klien hingga ke backend, di mana proxy melakukan re-enkripsi atau meneruskan koneksi TLS (SNI pass-through / mTLS) sehingga lalu lintas pada jaringan internal tetap terlindungi dari penyadapan internal.
3. **Bagaimana cara mengisolasi backend agar tidak langsung diakses dari host?**  
   *Jawaban*: Cara terbaik adalah: (1) Menempatkan kontainer backend pada user-defined bridge network internal (`web-net`) tanpa mendeklarasikan pemetaan port (`ports`) ke host; (2) Hanya mengekspos port melalui kontainer reverse proxy; dan (3) Jika port backend terpaksa dibuka ke host untuk kebutuhan diagnostik, batasi binding secara ketat pada alamat loopback lokal host (`127.0.0.1:5000:5000`), bukan di `0.0.0.0`.
4. **Apa konsekuensi menyimpan private key TLS di bind mount?**  
   *Jawaban*: Kunci privat yang disimpan pada direktori bind mount rentan terbaca oleh pengguna host non-root jika izin berkas terlalu longgar (*lax permissions*). Selain itu, berkas kunci berisiko terkomit secara tidak sengaja ke repositori Git publik (*credential leak*), serta tidak terlindungi oleh mekanisme enkripsi saat istirahat (*encryption at rest*) bawaan sistem container engine.
5. **Bandingkan log Nginx dan log Apache dari sisi format dan kegunaan debugging.**  
   *Jawaban*:  
   - **Log Apache**: Menggunakan format Common Log Format (CLF) atau Combined. Error log Apache berorientasi modul (`[module:level] [pid:tid] AHxxxxx: message`), sangat informatif untuk mendiagnosis kegagalan internal modul web server (seperti MPM event, modul rewriting, atau izin akses berkas direktori htdocs).  
   - **Log Nginx**: Menyediakan variabel upstream yang kaya (`$upstream_addr`, `$upstream_status`, `$upstream_response_time`). Nginx access dan error log sangat unggul untuk menelusuri performa jaringan, latensi layanan backend, kesalahan resolusi DNS internal kontainer, serta pemecahan masalah koneksi reverse proxy (*connection refused* atau *502 Bad Gateway*).

---

## 8. Kesimpulan

Praktikum Bab 4 membuktikan keberhasilan implementasi arsitektur web service multi-kontainer modern dengan memadukan Apache sebagai penyaji konten statis, Flask sebagai microservice API, dan Nginx sebagai reverse proxy sekaligus gerbang TLS ingress. Pengujian cURL dan OpenSSL membuktikan berfungsinya pengalihan otomatis HTTP 301 ke HTTPS, perutean path `/` dan `/api`, penerusan header identitas (`X-Forwarded-Proto`), serta negosiasi enkripsi modern TLS 1.3 dengan cipher `TLS_AES_256_GCM_SHA384` dan pertukaran kunci pasca-kuantum `X25519MLKEM768`. Dari perspektif DevSecOps, isolasi backend tanpa paparan port host, penegakan header keamanan HTTP, penggunaan *read-only bind mount* (`:ro`), serta orkestrasi dependensi cerdas (`service_healthy`) berhasil membentuk perimeter pertahanan yang andal sesuai prinsip *Least Privilege* dan *Least Exposure*.
