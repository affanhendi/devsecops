# LAPORAN PRAKTIKUM DEVOPS & CLOUD COMPUTING
## BAB 8: HARDENING CONTAINER, SECRETS, TRIVY, DAN PRIVATE REGISTRY

### IDENTITAS MAHASISWA

* **Nama Lengkap** : Mohammad Affan Hendi Firmansyah
* **NIM** : 3126640049
* **Kelas** : 1 IT-B S.Tr.Lj
---

## RINGKASAN EKSEKUTIF

Praktikum Bab 8 membangun aplikasi Flask (`pens-web:1.0`) dengan prinsip *container hardening*, memisahkan secret dari image, memindai image dengan **Trivy** sebagai security gate, dan menyiapkan **private registry** dengan TLS serta autentikasi `htpasswd` bcrypt. Trivy memindai arsip image (`docker image save`) sehingga tidak perlu mount `/var/run/docker.sock`.

Hasil akhir praktikum:

| No. | Target | Status |
|---:|---|---|
| 1 | Build multi-stage image non-root (UID 10001) | **PASS** |
| 2 | Runtime hardening (read-only rootfs, `cap_drop: ALL`, `no-new-privileges`, limit resource) | **PASS** |
| 3 | Secret dipasang sebagai file `/run/secrets/app_secret`, bukan env var | **PASS** |
| 4 | `verify-hardening.sh` | **PASS** (11 dari 11 kontrol) |
| 5 | Registry TLS menolak akses anonim (HTTP 401) | **PASS** |
| 6 | Trivy security gate | **BLOCKED** (ada temuan HIGH/CRITICAL yang sudah punya perbaikan) |
| 7 | Push ke private registry | **Tidak dijalankan** (diblokir gate, sesuai desain) |

Gate berstatus `BLOCKED` adalah perilaku yang benar: `push-registry.sh` menolak mempromosikan image yang belum lulus gate. Status gate tidak diubah secara manual.

---

## BAB VIII: TUJUAN PEMBELAJARAN DAN LANDASAN TEORI

### Tujuan

1. Menerapkan hardening runtime: non-root, read-only rootfs, drop capability, `no-new-privileges`, limit CPU/memory/PID.
2. Mengelola secret melalui file mount, bukan image atau environment variable.
3. Memindai image dengan Trivy (vuln, secret, misconfig), membuat SBOM CycloneDX, dan menerapkan security gate.
4. Menjalankan private registry dengan TLS dan autentikasi.
5. Menguji kontrol dengan negative test.

### Konsep Inti

| Konsep | Penjelasan |
|---|---|
| Multi-stage build | Dependency dipasang pada stage `builder`; stage `runtime` hanya menyalin venv dan kode aplikasi. |
| Non-root user | Proses berjalan sebagai UID/GID 10001 sehingga dampak kompromi lebih kecil. |
| Read-only rootfs + tmpfs | Filesystem root tidak dapat ditulis; hanya `/tmp` (tmpfs `noexec,nosuid`) yang writable. |
| `cap_drop: ALL` | Seluruh Linux capability dihapus (`CapEff` = 0). |
| `no-new-privileges` | Mencegah proses menaikkan hak akses melalui setuid/setcap. |
| Docker secret (file) | Secret muncul di `/run/secrets/<nama>`, tidak tersimpan di layer image maupun `docker inspect`. |
| Trivy gate | Gagal (exit 1) bila ada HIGH/CRITICAL yang sudah ada fix (`--ignore-unfixed`). |
| SBOM | Daftar komponen image (CycloneDX) untuk audit rantai pasok. |
| Registry TLS + htpasswd | Registry hanya melayani HTTPS dan meminta kredensial bcrypt. |

Scanner tidak menggantikan triage: severity bukan otomatis risiko aktual, dan image yang sama dapat memperoleh temuan baru ketika database vulnerability diperbarui.

---

## BAB VIII: LANGKAH-LANGKAH PRAKTIKUM

### 8.1 Penyiapan Direktori

```bash
mkdir -p ~/docker-lab/bab-8/{app,secrets,registry/certs,registry/auth,scripts,reports}
cd ~/docker-lab/bab-8
touch reports/.gitkeep
```

![Pembuatan struktur direktori](../assets/Screenshot%202026-11-17%20065855.png)

### 8.2 Pembuatan Berkas Konfigurasi

Berkas yang dibuat sesuai cheatsheet: `.env.example`, `.gitignore`, `.dockerignore`, `app/requirements.txt`, `app/app.py`, `app/Dockerfile`, `secrets/app_secret.txt.example`, `compose.yaml`, dan empat script di `scripts/`.

| Berkas | Bukti |
|---|---|
| `.env.example` (credential sintetis lab) | ![env](../assets/Screenshot%202026-11-17%20065924.png) |
| `.gitignore` (mengecualikan `.env`, secret, key, laporan) | ![gitignore](../assets/Screenshot%202026-11-17%20065955.png) |
| `.dockerignore` (secret/registry/reports tidak masuk build context) | ![dockerignore](../assets/Screenshot%202026-11-17%20070027.png) |
| `app/requirements.txt` (Flask 3.1.3, gunicorn 26.1.0 dipin) | ![req](../assets/Screenshot%202026-11-17%20070116.png) |
| `app/app.py` (hanya melaporkan keberadaan secret, bukan nilainya) | ![app](../assets/Screenshot%202026-11-17%20070210.png) |
| `app/Dockerfile` (multi-stage, `USER 10001:10001`) | ![dockerfile](../assets/Screenshot%202026-11-17%20070241.png) |
| `compose.yaml` (hardening runtime) | ![compose](../assets/Screenshot%202026-11-17%20071401.png) |

Aktivasi konfigurasi lokal:

```bash
cp .env.example .env
chmod 600 .env
```

### 8.3 Pembuatan Secret, Sertifikat, dan Akun Registry

```bash
openssl rand -hex 32 > secrets/app_secret.txt
chmod 600 secrets/app_secret.txt
./scripts/generate-registry-assets.sh
```

![Secret dan aset registry dibuat](../assets/Screenshot%202026-11-17%20071924.png)

Output `[PASS] Sertifikat dan htpasswd berhasil dibuat.` menandakan sertifikat self-signed (SAN `localhost`, `127.0.0.1`, RSA 3072) dan htpasswd bcrypt berhasil dibuat.

### 8.4 Memercayai CA Registry pada Docker Engine

Pada WSL 2 terdapat dua kendala: percobaan `sudo` pertama gagal autentikasi (salah password), dan perintah rootless `systemctl --user restart docker` gagal karena `docker.service` tidak ada (Docker berjalan melalui Docker Desktop, bukan Engine native).

![Trust CA registry](../assets/Screenshot%202026-11-17%20072202.png)

Sertifikat tetap disalin ke `/etc/docker/certs.d/localhost:5000/ca.crt` dan `~/.config/docker/certs.d/...`. Karena Docker Desktop, trust store yang relevan adalah `~/.docker/certs.d/localhost:5000/ca.crt` disertai restart Docker Desktop.

### 8.5 Build dan Menjalankan Runtime

```bash
docker compose build --pull app
docker compose up -d app registry
docker compose ps
```

![Build image](../assets/Screenshot%202026-11-17%20072343.png)

Build selesai dalam 39,2 detik. Image `pens-web:1.0` dibangun dengan dua stage (`builder` dan `runtime`).

### 8.6 Verifikasi Response Aplikasi

```bash
curl --fail --silent --show-error http://127.0.0.1:8088/ | python3 -m json.tool
```

![Response aplikasi](../assets/Screenshot%202026-11-17%20082730.png)

Response menunjukkan `uid` = `gid` = `10001` dan `secret_mounted: true`.

### 8.7 Negative Test Hardening

```bash
./scripts/verify-hardening.sh
```

![verify-hardening PASS](../assets/Screenshot%202026-11-17%20084748.png)

| No. | Kontrol | Hasil |
|---:|---|---|
| 1 | Proses berjalan UID 10001 | PASS |
| 2 | Penulisan ke root filesystem ditolak | PASS |
| 3 | tmpfs `/tmp` dapat dipakai | PASS |
| 4 | `CapEff` = `0000000000000000` | PASS |
| 5 | `NoNewPrivs` = 1 | PASS |
| 6 | Secret tersedia sebagai file read-only | PASS |
| 7 | Secret tidak ada sebagai env `APP_SECRET` | PASS |
| 8 | Docker socket tidak terpasang | PASS |
| 9 | Limit memory, CPU, PID, dan read-only rootfs aktif | PASS |
| 10 | Health endpoint merespons sukses | PASS |
| 11 | Registry menolak akses anonim dengan HTTP 401 | PASS (setelah perbaikan, lihat 8.9) |

Total kontrol terverifikasi: **11**.

### 8.8 Trivy, SBOM, dan Security Gate

```bash
./scripts/scan-image.sh
cat reports/gate-status.txt
sha256sum --check reports/SHA256SUMS
```

![Trivy mengunduh database](../assets/Screenshot%202026-11-17%20085152.png)
![Gate BLOCKED](../assets/Screenshot%202026-11-17%20085224.png)

Log memperlihatkan Trivy 0.74.0 mendeteksi OS Debian 13.7 (87 paket) dan paket Python, lalu gate memberi `[BLOCKED] Temuan HIGH/CRITICAL yang dapat diperbaiki terdeteksi.` `gate-status.txt` berisi `BLOCKED`.

`sha256sum --check reports/SHA256SUMS` gagal (`No such file or directory`) karena script berhenti (`exit 1`) sebelum tahap pembuatan checksum. Ini konsisten dengan desain: checksum hanya dibuat bila gate lulus.

Sesuai prosedur cheatsheet, status gate tidak diubah manual. Tindak lanjut yang benar adalah meninjau `reports/trivy-gate.txt`, memperbarui base image atau dependency, membangun ulang, lalu memindai ulang.

### 8.9 Pengujian Private Registry

```bash
curl --silent --output /dev/null --write-out 'HTTP %{http_code}\n' \
  --cacert registry/certs/domain.crt https://localhost:5000/v2/
```

![Registry menolak anonim](../assets/Screenshot%202026-11-17%20085258.png)

Hasil `HTTP 401`: TLS tervalidasi dengan sertifikat lab dan registry menolak akses tanpa kredensial. Script `push-registry.sh` **tidak dijalankan** karena gate masih `BLOCKED`, sehingga push, pull, katalog, dan digest belum dibuktikan.

### 8.10 Kotak Perintah I dan J

Pembuktian secret tidak ada di image (`docker history`, `docker run ... test ! -e /run/secrets/app_secret`) dan cleanup (`docker compose --profile tools down --volumes --remove-orphans`) **belum didokumentasikan** pada praktikum ini.

---

## VERIFIKASI DAN SKENARIO PENGUJIAN

| No. | Kontrol | Evidence | Hasil |
|---:|---|---|:---:|
| 1 | User non-root | Response `uid` 10001; `verify-hardening.sh` | PASS |
| 2 | Read-only rootfs | `touch /unauthorized-write` ditolak | PASS |
| 3 | Writable path terkontrol | `/tmp` tmpfs dapat ditulis | PASS |
| 4 | Capability | `CapEff` bernilai nol | PASS |
| 5 | Privilege escalation | `NoNewPrivs` = 1 | PASS |
| 6 | Secret injection | File ada, tidak ada env `APP_SECRET` | PASS |
| 7 | Docker socket | Tidak terpasang | PASS |
| 8 | Resource limit | Memory, CPU, PID aktif | PASS |
| 9 | Healthcheck | Container `healthy`, `/health` 200 | PASS |
| 10 | Scan lengkap (JSON, SBOM, config, secret) | Berhenti sebelum checksum karena gate gagal | Parsial |
| 11 | Security gate | `gate-status.txt` = `BLOCKED` | FAIL (BLOCKED) |
| 12 | TLS registry | `curl --cacert` berhasil | PASS |
| 13 | Autentikasi registry | HTTP 401 anonim | PASS |
| 14 | Distribusi (push/pull/katalog/digest) | Tidak dijalankan karena gate | Belum diuji |

---

## TROUBLESHOOTING DAN ANALISIS HASIL

Masalah yang muncul selama praktikum, beserta diagnosis dan perbaikannya:

| Gejala | Diagnosis | Tindakan korektif |
|---|---|---|
| `curl http://127.0.0.1:8088/` gagal `Could not connect to server`; `docker compose ps` hanya menampilkan `8080/tcp` tanpa mapping host | Port tidak terpublikasi ke host. `docker compose config` menunjukkan `ports` benar (`host_ip 127.0.0.1`, `published 8088`), sehingga penyebabnya ada pada network: `app-net` dan `registry-net` dideklarasikan `internal: true`, dan Docker tidak mempublikasikan port untuk container yang hanya terhubung ke network internal. | Memberi akses network non-internal pada service yang perlu dijangkau host (atau membuat network publikasi terpisah). Setelah itu `curl` ke port 8088 berhasil (8.6). |
| Registry berstatus `Restarting`; log `panic: unable to configure authorization (htpasswd): open /auth/htpasswd: permission denied` lalu `open /certs/domain.key: permission denied` | Script membuat `htpasswd` dan `domain.key` dengan mode 600 milik user host. Proses registry berjalan non-root di dalam container sehingga tidak dapat membaca berkas pada bind mount. | `chmod -R a+rX registry/ secrets/` lalu `docker compose restart registry`. Registry `Up`, log menampilkan `configured "htpasswd" access controller`. |
| `verify-hardening.sh`: `[FAIL] Registry memberi status anonim 000` | Kode `000` berarti koneksi gagal (bukan respons HTTP). `curl -v` ke `127.0.0.1:5000` menunjukkan `Connection refused` karena port registry belum terpublikasi. | Masalah port dan permission di atas diperbaiki; hasil ulang `HTTP 401` dan 11 kontrol PASS. |
| Trivy: `no space left on device` saat mengunduh `trivy-db` (134 MiB) | Direktori sementara Trivy berupa tmpfs `size=64m` (`/tmp` pada service `trivy`) lebih kecil dari arsip database. | Memperbesar tmpfs service `trivy` (atau memakai volume `trivy-cache`), lalu mengulang scan; database berhasil diunduh. |
| `sha256sum --check` gagal `No such file` | `SHA256SUMS` dibuat setelah gate lulus; gate `BLOCKED` sehingga script berhenti. | Bukan bug: selesaikan temuan gate, bangun ulang, scan ulang. |
| Log aplikasi `Control server error: Read-only file system: '/home/appuser'` | Gunicorn 26 mencoba membuat control socket di home directory (`--no-create-home`, rootfs read-only). Bukan fatal: worker tetap menerima request dan `/health` merespons 200. | Dapat diredam dengan mengarahkan lokasi control socket ke `/tmp`, tanpa melonggarkan read-only rootfs. |

### Risiko keamanan dan operasional

* **Scanner bukan jaminan**: image yang sama dapat berubah dari lulus menjadi `BLOCKED` ketika database vulnerability diperbarui; versi Trivy dan waktu scan perlu dicatat.
* **Sertifikat self-signed dan credential `.env`** hanya layak untuk lab. Private key dan htpasswd yang dibuat `chmod a+rX` pada solusi permission lebih longgar dari mode 600 dan memberi akses baca ke semua user lokal; pada lingkungan bersama, gunakan pemilik berkas yang sesuai UID registry atau Docker secret.
* **Basic auth registry** tidak menyediakan otorisasi granular per repository.
* **Hardening harus diuji terhadap fungsi aplikasi**: read-only rootfs menimbulkan galat Gunicorn di atas; kontrol yang ketat tetap membutuhkan penyesuaian jalur tulis paling sempit.
* **Trust CA pada Docker Desktop/WSL** berbeda dari Engine native; menyalin CA ke lokasi yang salah membuat `docker login` gagal `x509`.

### Rekomendasi untuk lingkungan production-like

1. Gunakan CA terpercaya, nama DNS nyata, dan rotasi sertifikat serta password registry terjadwal.
2. Pin base image dengan digest dan jalankan `scan-image.sh` pada pipeline CI dengan versi Trivy yang dipin.
3. Gunakan secret manager (Vault/Swarm/Kubernetes Secrets) menggantikan file `.env`.
4. Atur kepemilikan berkas registry sesuai UID proses, bukan membuka izin baca bagi semua user.
5. Dokumentasikan triage dan exception (owner, alasan, mitigasi, masa berlaku) untuk CVE yang belum dapat diperbaiki.
6. Simpan laporan scan, SBOM, dan checksum sebagai evidence yang dapat ditelusuri.

---

## EVALUASI DAN LATIHAN MANDIRI

1. **Mengapa `--ignore-unfixed` hanya dipakai pada gate?** Agar gate tidak berhenti pada temuan yang belum punya perbaikan; temuan tersebut tetap tercatat di `trivy-image.json` dan harus ditriase atau diterima dengan dokumentasi.
2. **Apa yang dibuktikan `CapEff` nol?** Proses tidak memiliki Linux capability efektif sehingga operasi privileged (mis. mengubah jaringan, `chown` sembarang) tidak dapat dilakukan meski proses dikompromikan.
3. **Mengapa secret tidak ditaruh di environment variable?** Env var terlihat melalui `docker inspect`, dapat bocor ke proses anak dan log crash; file mount `/run/secrets` hanya dapat dibaca proses yang berwenang.
4. **Mengapa Trivy memindai arsip image, bukan lewat Docker socket?** Mount `docker.sock` ke container setara akses root pada host; arsip `.tar` cukup dan jauh lebih aman.
5. **Mengapa gate `BLOCKED` tidak boleh diedit manual?** Status adalah evidence kontrol; mengeditnya meniadakan fungsi gate dan merusak keterlacakan.

---

## FORMAT LAPORAN PRAKTIKUM

### Bukti minimum

| Bukti | Referensi |
|---|---|
| `docker compose ps` yang menunjukkan service berjalan | Bagian 8.5 dan troubleshooting (aplikasi `healthy`, registry `Up` setelah perbaikan) |
| Hasil curl/API sesuai target bab | Bagian 8.6 (response JSON), 8.9 (HTTP 401) |
| Log/query yang membuktikan sistem bekerja | Bagian 8.7 (`verify-hardening.sh` 11 PASS), 8.8 (log Trivy dan gate) |

### Analisis wajib

* **Masalah dan diagnosis**: port tidak terpublikasi (network `internal: true`) dan registry crash karena permission `htpasswd`/`domain.key`. Diagnosis memakai `docker compose ps`, `docker compose config`, `docker compose logs registry`, dan `curl -v` (bagian Troubleshooting).
* **Risiko**: lihat bagian *Risiko keamanan dan operasional*.
* **Rekomendasi production-like**: lihat bagian *Rekomendasi*.

### Catatan keterbatasan

Security gate masih `BLOCKED`, sehingga SBOM/checksum, push-pull-katalog-digest, dan pembuktian secret tidak ada di image (Kotak Perintah I) belum didokumentasikan. Langkah tersebut dilanjutkan setelah base image atau dependency diperbarui dan gate berstatus `PASS`.

---

## REFERENSI UTAMA

1. [NIST SP 800-190 — Application Container Security Guide](https://csrc.nist.gov/pubs/sp/800/190/final).
2. [Docker — Building best practices](https://docs.docker.com/build/building/best-practices/).
3. [Docker — Resource constraints](https://docs.docker.com/engine/containers/resource_constraints/).
4. [Docker — Manage secrets in Compose](https://docs.docker.com/compose/how-tos/use-secrets/).
5. [Docker — Verify registry certificates](https://docs.docker.com/engine/security/certificates/).
6. [CNCF Distribution — Deploy a registry](https://distribution.github.io/distribution/about/deploying/).
7. [Trivy — Container image scanning](https://trivy.dev/docs/latest/guide/target/container_image/).
8. [OWASP Docker Security Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Docker_Security_Cheat_Sheet.html).
