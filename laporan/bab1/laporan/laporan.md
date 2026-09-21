# LAPORAN PRAKTIKUM BAB 1
## Fondasi Teoretis dan Kerangka Kerja DevSecOps

**Nama**: ........................................................  
**NIM**: ..........................................................  
**Kelas**: ........................................................  
**Tanggal pelaksanaan**: 27 Agustus 2026  

---

## 1. Tujuan Praktikum

Praktikum Bab 1 bertujuan untuk menetapkan *baseline* laboratorium DevSecOps dan memahami verifikasi awal yang diperlukan sebelum rangkaian eksperimen keamanan pada bab-bab berikutnya dilaksanakan. *Baseline* ini mencakup:
1. Pembuatan struktur direktori kerja terisolasi untuk memisahkan aplikasi, kebijakan (*policy*), laporan audit (*reports*), artefak dependensi/SBOM, dan material kriptografi (*keys*).
2. Perekaman versi perangkat lunak fundamental (Git, OpenSSL, cURL, Docker Engine, dan Docker Compose v2/v5).
3. Verifikasi ketersediaan dan opsi keamanan (*SecurityOptions*) pada daemon Docker pada lingkungan WSL2 (*Windows Subsystem for Linux*).
4. Melatih sikap kritis dalam menganalisis keluaran perintah, mengidentifikasi kendala lingkungan (*troubleshooting* integrasi Docker Desktop dengan WSL2), dan menyusun *threat statement* awal.

---

## 2. Dasar Teori Singkat

DevSecOps adalah pendekatan sosio-teknis yang mengintegrasikan keamanan ke dalam seluruh siklus hidup perangkat lunak (*software development lifecycle* / SDLC)—mulai dari perencanaan (*plan*), penulisan kode (*code*), pembangunan (*build*), pengujian (*test*), rilis (*release*), penerapan (*deploy*), hingga operasi dan pemantauan (*operate & monitor*). DevSecOps bukan sekadar menambahkan alat pemindai (*security scanner*) ke dalam *pipeline* CI/CD, melainkan mendistribusikan tanggung jawab keamanan (*shared responsibility*) kepada seluruh pemangku kepentingan dengan bahasa risiko dan bukti jaminan (*evidence*) yang dapat diaudit.

Dua pilar penting dalam integrasi keamanan adalah:
- **Shift-Left**: Memindahkan kontrol keamanan sedini mungkin ke tahap awal siklus pengembangan (seperti *threat modeling*, *secure coding*, *secret scanning*, SAST, dan SCA), di mana biaya perbaikan kelemahan masih jauh lebih rendah dibandingkan saat sistem telah berada di produksi.
- **Shift-Right**: Melengkapi pengujian statis dengan pengujian dan pengawasan pada lingkungan dinamis/operasional (seperti DAST, *runtime container detection*, *observability*, manajemen insiden, dan evaluasi kepatuhan kebijakan).

Perekaman *baseline* lingkungan laboratorium sangat penting agar seluruh eksperimen dapat direproduksi (*reproducible*). Perbedaan versi *engine*, pustaka kriptografi, kernel, maupun konfigurasi isolasi *container* (seperti profil `seccomp` dan `cgroupns`) akan menghasilkan perilaku dan hasil pemindaian keamanan yang berbeda. Oleh karena itu, verifikasi sistem operasi, hak akses pengguna (*least privilege*), dan daemon *container* menjadi prasyarat mutlak sebelum eksperimen lanjutan dijalankan.

---

## 3. Alat dan Lingkungan

Berdasarkan pengujian aktual di laboratorium, lingkungan kerja berpindah dari pengujian awal di distro internal Docker Desktop menuju distribusi Ubuntu 26.04 LTS pada WSL2 yang telah diintegrasikan dengan Docker Desktop.

| Komponen | Identifikasi Lingkungan Awal (Gagal) | Hasil Identifikasi Akhir (Baseline Valid) |
|---|---|---|
| **Host OS** | Windows 11 Enterprise / Pro (`10.0.26200.9168`) | Windows 11 Enterprise / Pro (`10.0.26200.9168`) |
| **Platform Virtualisasi** | WSL2 (`docker-desktop` distro) | WSL2 (`Ubuntu` default distro) |
| **Distribusi Linux** | Distro internal Docker Desktop (minimal / Alpine-based) | Ubuntu 26.04 LTS (*Resolute Raccoon*) |
| **Arsitektur Host** | `x86_64` / `linux/amd64` | `x86_64` / `linux/amd64` |
| **Pengguna Eksekusi** | `root` (`PC-PDEAFFAN-PDEK348:~#`) | `affan` (`affan@PC-PDEAFFAN-PDEK348`) — *Non-root* |
| **Direktori Kerja** | `/root/devsecops-lab/` | `/home/affan/devsecops-lab/` (`~/devsecops-lab`) |
| **Git** | Tidak tersedia (`-sh: git: not found`) | `git version 2.53.0` |
| **OpenSSL** | Tidak tersedia (`-sh: openssl: not found`) | `OpenSSL 3.5.5 27 Jan 2026` |
| **cURL** | Tidak tersedia (`-sh: curl: not found`) | `curl 8.18.0 (x86_64-pc-linux-gnu)` |
| **Docker Engine** | Tidak dapat dipanggil dari CLI distro ini | `29.6.2` (Client & Server Engine, API 1.55) |
| **Docker Desktop** | `Docker Desktop` (Distro Stopped/Internal) | `Docker Desktop 4.84.0 (234817)` |
| **Docker Compose** | Tidak tersedia | `Docker Compose version v5.3.1` |
| **Security Options** | Tidak dapat diperiksa | `["name=seccomp,profile=builtin","name=cgroupns"]` |

---


## 4. Langkah Praktikum dan Troubleshooting

### 4.1 Upaya Awal dan Kendala Lingkungan (Troubleshooting WSL2)

Pada pengujian awal, pembuatan struktur direktori dan eksekusi perintah verifikasi dilakukan di dalam konteks distribusi WSL internal Docker Desktop (`docker-desktop`):

```bash
mkdir -p ~/devsecops-lab/{app,policy,reports,sbom,keys}
cd ~/devsecops-lab/
docker compose version
git --version
openssl version
curl --version
```

**Kendala yang Ditemukan**:
1. Pemanggilan perintah `docker compose version` menghasilkan pesan kesalahan dari daemon Docker Desktop:
   ```text
   It looks like you have tried to invoke the docker CLI from the docker-desktop WSL2 distribution. This is not supported.
   Please invoke the docker CLI from the Windows Command Prompt, PowerShell, or other compatible terminals.
   If you wish to interact with Docker Desktop from a third-party WSL2 distribution, such as Ubuntu, please enable the Docker Desktop WSL2 integration for it.
   ```
2. Utilitas dasar seperti `git`, `openssl`, dan `curl` menghasilkan status `-sh: command: not found` karena distribusi `docker-desktop` merupakan lingkungan internal minimal berbasis Alpine yang tidak ditujukan sebagai *interactive development environment*.

### 4.2 Langkah Remediasi dan Integrasi WSL2

Untuk mengatasi kendala tersebut, dilakukan serangkaian tindakan perbaikan:
1. **Pemeriksaan Status Distribusi WSL**:
   Melalui Administrator Command Prompt di Windows:
   ```cmd
   wsl -l -v
   ```
   Teridentifikasi bahwa distribusi default sebelumnya mengarah ke `docker-desktop` yang berstatus `Stopped`.
2. **Pengecekan Distribusi yang Tersedia**:
   Menampilkan daftar distribusi Linux yang terpasang di host Windows, yang mengonfirmasi ketersediaan distribusi Ubuntu (`Ubuntu 26.04 LTS`).
3. **Aktivasi Integrasi Docker Desktop WSL2**:
   - Membuka aplikasi **Docker Desktop GUI** -> Masuk ke menu **Settings** -> **Resources** -> **WSL integration**.
   - Memastikan opsi **"Enable integration with my default WSL distro"** dicentang.
   - Mengaktifkan *toggle switch* integrasi untuk distribusi **Ubuntu**.
   - Menekan tombol **Apply & restart** untuk menerapkan konfigurasi jembatan (*socket forwarding*).
4. **Verifikasi Kesiapan WSL**:
   Memastikan melalui Command Prompt bahwa distribusi `Ubuntu` telah aktif (`Running`) sebagai default distro bersama dengan `docker-desktop`.

### 4.3 Pembuatan Struktur Direktori di Lingkungan Ubuntu

Setelah berpindah ke terminal WSL2 Ubuntu sebagai pengguna non-root (`affan`), struktur direktori laboratorium DevSecOps dibuat ulang:

```bash
mkdir -p ~/devsecops-lab/{app,policy,reports,sbom,keys}
cd ~/devsecops-lab/
```

Struktur direktori kerja yang terbentuk adalah sebagai berikut:

```text
/home/affan/devsecops-lab/
├── app/        # Tempat menyimpan source code aplikasi dan Dockerfile
├── keys/       # Tempat penyimpanan material kunci kriptografi dan sertifikat
├── policy/     # Tempat menyimpan aturan kebijakan keamanan (OPA, Conftest, Trivy config)
├── reports/    # Direktori keluaran laporan pemindaian keamanan (SARIF, JSON, TXT)
└── sbom/       # Tempat penyimpanan artefak Software Bill of Materials (SPDX, CycloneDX)
```

### 4.4 Pencatatan Versi dan Opsi Keamanan Host

Perintah verifikasi baseline dieksekusi secara berurutan di dalam `~/devsecops-lab/`:

```bash
docker version
docker compose version
git --version
openssl version
curl --version
docker info --format '{{json .SecurityOptions}}'
```

---


## 5. Hasil Pengujian

### 5.1 Hasil Perintah Utama

| Pemeriksaan | Hasil Aktual | Status | Keterangan |
|---|---|---|---|
| Struktur direktori lab | `app`, `policy`, `reports`, `sbom`, `keys` berhasil dibuat | **Terpenuhi** | Terbentuk di `/home/affan/devsecops-lab` |
| `docker version` | Client: `29.6.2`, Server: `Docker Desktop 4.84.0` (Engine `29.6.2`) | **Terpenuhi** | Daemon Docker Desktop aktif dan terhubung ke WSL2 |
| `docker compose version` | `Docker Compose version v5.3.1` | **Terpenuhi** | Menggunakan Docker Compose plugin v5 |
| `git --version` | `git version 2.53.0` | **Terpenuhi** | Siap untuk pelacakan commit dan version control |
| `openssl version` | `OpenSSL 3.5.5 27 Jan 2026` | **Terpenuhi** | Siap untuk penandatanganan artefak & kriptografi |
| `curl --version` | `curl 8.18.0` (dengan libcurl 8.18.0 & OpenSSL 3.5.5) | **Terpenuhi** | Siap untuk interaksi HTTP/API |
| `SecurityOptions` | `["name=seccomp,profile=builtin","name=cgroupns"]` | **Terpenuhi** | Mendukung pembatasan syscall (`seccomp`) & isolasi cgroup |
| Hak akses pengguna | Pengguna `affan` (non-root) | **Terpenuhi** | Sesuai prinsip *least privilege* |

---

### 5.2 Bukti Output dan Tangkapan Layar

#### A. Kendala Awal pada Distro `docker-desktop`
Pada tangkapan layar pertama, terlihat bahwa pemanggilan Docker CLI di dalam distro `docker-desktop` ditolak oleh sistem dan utilitas pendukung belum terpasang.

![Kendala pemanggilan CLI pada distro docker-desktop](../assets/Screenshot%202026-08-27%20085821.png)  
*Gambar 5.1: Pesan penolakan eksekusi Docker CLI dan ketiadaan git, openssl, dan curl pada distro docker-desktop.*

```text
PC-PDEAFFAN-PDEK348:~# mkdir -p ~/devsecops-lab/{app,policy,reports,sbom,keys}
PC-PDEAFFAN-PDEK348:~# cd ~/devsecops-lab/
PC-PDEAFFAN-PDEK348:~/devsecops-lab# docker compose version
It looks like you have tried to invoke the docker CLI from the docker-desktop WSL2 distribution. This is not supported.
Please invoke the docker CLI from the Windows Command Prompt, PowerShell, or other compatible terminals.
If you wish to interact with Docker Desktop from a third-party WSL2 distribution, such as Ubuntu, please enable the Docker Desktop WSL2 integration for it.
PC-PDEAFFAN-PDEK348:~/devsecops-lab# git --version
-sh: git: not found
PC-PDEAFFAN-PDEK348:~/devsecops-lab# openssl version
-sh: openssl: not found
PC-PDEAFFAN-PDEK348:~/devsecops-lab# curl --version
-sh: curl: not found
```

#### B. Identifikasi dan Pemeriksaan WSL pada Host Windows
Pemeriksaan dilakukan melalui Administrator Command Prompt untuk melihat daftar distro dan status virtualisasinya.

![Pengecekan status WSL melalui Windows Command Prompt](../assets/Screenshot%202026-08-27%20090036.png)  
*Gambar 5.2: Pengecekan daftar dan status awal WSL via `wsl -l -v`.*

![Daftar distribusi Linux yang tersedia pada host](../assets/Screenshot%202026-08-27%20090553.png)  
*Gambar 5.3: Daftar distribusi Linux yang terdaftar pada sistem host.*

```text
C:\Windows\System32>wsl -l -v
  NAME            STATE           VERSION
* docker-desktop  Stopped         2
```

#### C. Konfigurasi WSL Integration pada Docker Desktop GUI
Untuk menghubungkan Docker daemon dengan lingkungan Linux Ubuntu, fitur WSL Integration diaktifkan secara spesifik untuk distro `Ubuntu`.

![Pengaturan WSL Integration pada Docker Desktop GUI](../assets/Screenshot%202026-08-27%20102258.png)  
*Gambar 5.4: Konfigurasi Docker Desktop Settings -> Resources -> WSL integration (mengaktifkan integrasi dengan Ubuntu).*

![Status WSL setelah integrasi](../assets/Screenshot%202026-08-27%20102231.png)  
*Gambar 5.5: Verifikasi status distro Ubuntu dan docker-desktop yang kini keduanya berstatus 'Running'.*

```text
C:\Windows\System32>wsl -l -v
  NAME            STATE           VERSION
* Ubuntu          Running         2
  docker-desktop  Running         2
```

#### D. Verifikasi Lingkungan Ubuntu dan Ketersediaan Perangkat
Pengecekan versi OS Ubuntu 26.04 LTS (*Resolute Raccoon*) serta verifikasi awal ketersediaan Git, cURL, OpenSSL, dan Docker CLI.

![Verifikasi versi OS dan utilitas pada Ubuntu WSL2](../assets/Screenshot%202026-08-27%20091704.png)  
*Gambar 5.6: Perbandingan output OS Release Ubuntu 26.04 LTS serta kesiapan Git, cURL, OpenSSL, dan Docker.*

```text
PRETTY_NAME="Ubuntu 26.04 LTS"
NAME="Ubuntu"
VERSION_ID="26.04"
VERSION="26.04 (Resolute Raccoon)"
VERSION_CODENAME=resolute
ID=ubuntu
ID_LIKE=debian

affan@PC-PDEAFFAN-PDEK348:/mnt/c/Windows/System32$ git --version
git version 2.53.0
affan@PC-PDEAFFAN-PDEK348:/mnt/c/Windows/System32$ curl --version
curl 8.18.0 (x86_64-pc-linux-gnu) libcurl/8.18.0 OpenSSL/3.5.5 zlib/1.3.1 brotli/1.2.0 zstd/1.5.7 libidn2/2.3.8 libpsl/0.21.2 libssh2/1.11.1 nghttp2/1.68.0 librtmp/2.3 mit-krb5/1.22.1 OpenLDAP/2.6.10
affan@PC-PDEAFFAN-PDEK348:/mnt/c/Windows/System32$ openssl version
OpenSSL 3.5.5 27 Jan 2026 (Library: OpenSSL 3.5.5 27 Jan 2026)
affan@PC-PDEAFFAN-PDEK348:/mnt/c/Windows/System32$ docker --version
Docker version 29.6.2, build dfc4efb
affan@PC-PDEAFFAN-PDEK348:/mnt/c/Windows/System32$ docker compose version
Docker Compose version v5.3.1
```

#### E. Eksekusi Baseline Lengkap di Direktori Lab DevSecOps
Eksekusi akhir di dalam direktori `~/devsecops-lab/` membuktikan bahwa seluruh prasyarat baseline telah terpenuhi secara utuh dan siap digunakan.

![Eksekusi docker version pada direktori devsecops-lab](../assets/Screenshot%202026-08-27%20102940.png)  
*Gambar 5.7: Detail informasi Client dan Server Docker Engine.*

![Eksekusi lengkap baseline DevSecOps di Ubuntu WSL2](../assets/Screenshot%202026-08-27%20103004.png)  
*Gambar 5.8: Hasil eksekusi lengkap `docker version`, `docker compose version`, `git`, `openssl`, `curl`, dan `docker info SecurityOptions`.*

```text
affan@PC-PDEAFFAN-PDEK348:~$ mkdir -p ~/devsecops-lab/{app,policy,reports,sbom,keys}
affan@PC-PDEAFFAN-PDEK348:~$ cd ~/devsecops-lab/
affan@PC-PDEAFFAN-PDEK348:~/devsecops-lab$ docker version
Client:
 Version:           29.6.2
 API version:       1.55
 Go version:        go1.26.5
 Git commit:        dfc4efb
 Built:             Thu Jul 16 16:11:35 2026
 OS/Arch:           linux/amd64
 Context:           default

Server: Docker Desktop 4.84.0 (234817)
 Engine:
  Version:          29.6.2
  API version:      1.55 (minimum version 1.40)
  Go version:       go1.26.5
  Git commit:       3d80467
  Built:            Thu Jul 16 16:12:20 2026
  OS/Arch:          linux/amd64
  Experimental:     false
 containerd:
  Version:          v2.2.5
  GitCommit:        e53c7c1516c3b2bff98eb76f1f4117477e6f4e66
 runc:
  Version:          1.3.6
  GitCommit:        v1.3.6-0-g491b69ba
 docker-init:
  Version:          0.19.0
  GitCommit:        de40ad0

affan@PC-PDEAFFAN-PDEK348:~/devsecops-lab$ docker compose version
Docker Compose version v5.3.1

affan@PC-PDEAFFAN-PDEK348:~/devsecops-lab$ git --version
git version 2.53.0

affan@PC-PDEAFFAN-PDEK348:~/devsecops-lab$ openssl version
OpenSSL 3.5.5 27 Jan 2026 (Library: OpenSSL 3.5.5 27 Jan 2026)

affan@PC-PDEAFFAN-PDEK348:~/devsecops-lab$ curl --version
curl 8.18.0 (x86_64-pc-linux-gnu) libcurl/8.18.0 OpenSSL/3.5.5 zlib/1.3.1 brotli/1.2.0 zstd/1.5.7 libidn2/2.3.8 libpsl/0.21.2 libssh2/1.11.1 nghttp2/1.68.0 librtmp/2.3 mit-krb5/1.22.1 OpenLDAP/2.6.10
Release-Date: 2026-01-07, security patched: 8.18.0-1ubuntu2
Protocols: dict file ftp ftps gopher gophers http https imap imaps ipfs ipns ldap ldaps mqtt pop3 pop3s rtmp rtsp scp sftp smb smbs smtp smtps telnet tftp ws wss
Features: alt-svc AsynchDNS brotli GSS-API HSTS HTTP2 HTTPS-proxy IDN IPv6 Kerberos Largefile libz NTLM PSL SPNEGO SSL threadsafe TLS-SRP UnixSockets zstd

affan@PC-PDEAFFAN-PDEK348:~/devsecops-lab$ docker info --format '{{json .SecurityOptions}}'
["name=seccomp,profile=builtin","name=cgroupns"]
```

---


## 6. Threat Statement

- **Aset yang Dilindungi**: Source code aplikasi, berkas konfigurasi *pipeline*, berkas kebijakan keamanan (`policy/`), laporan hasil pemindaian kerentanan (`reports/`), artefak SBOM (`sbom/`), material kunci kriptografi/sertifikat (`keys/`), serta kredensial/token komunikasi pada daemon Docker dan WSL2.
- **Aktor Ancaman**: Pengguna lokal lain pada host yang tidak berwenang, aplikasi/proses berbahaya yang berjalan di latar belakang host Windows, artefak *dependency* pihak ketiga yang terkompromi (*supply chain attack*), serta *container breakout* yang memanfaatkan kelemahan isolasi kernel bersama.
- **Jalur Serangan**:
  1. *Unrestricted file permissions*: Pembacaan tanpa izin terhadap isi direktori sensitif (`keys/`, `reports/`) oleh proses non-privileged pada host bersama.
  2. *Docker Socket Misuse*: Penggunaan socket Docker (`/var/run/docker.sock`) tanpa pembatasan yang memungkinkan eskalasi hak akses dari dalam container menuju host.
  3. *Unpatched vulnerabilities*: Kerentanan pada dependensi atau pustaka sistem (Git, OpenSSL, cURL, atau kernel WSL2) yang dieksploitasi untuk modifikasi artefak atau kebocoran kunci.
- **Dampak**: Kompromi kerahasiaan (*confidentiality*) kunci privat, hilangnya integritas (*integrity*) laporan audit keamanan yang menyebabkan temuan palsu atau lolosnya kerentanan kritis, manipulasi rilis perangkat lunak, serta potensi pengambilalihan hak akses penuh terhadap lingkungan host.

---

## 7. Analisis

### 7.1 Analisis Kendala Distro `docker-desktop` vs `Ubuntu` WSL2
Kendala awal yang muncul saat mengeksekusi perintah pada distro `docker-desktop` memberikan pelajaran teknis mendasar mengenai arsitektur Docker Desktop di Windows. Docker Desktop mengelola dua distribusi internal WSL2: `docker-desktop` dan `docker-desktop-data`. Distro ini dirancang khusus untuk menjalankan daemon Docker dan runtime container, bukan sebagai *interactive development environment*. Oleh sebab itu:
1. Docker CLI sengaja dibatasi agar tidak dipanggil langsung dari dalam distro tersebut untuk mencegah konflik soket dan konteks.
2. Distro internal tidak dilengkapi paket standar pengembangan seperti Git, OpenSSL, maupun cURL.

Solusi yang tepat dan sesuai praktik rekayasa perangkat lunak adalah mengaktifkan **WSL Integration** pada distribusi kerja sesungguhnya, yaitu Ubuntu 26.04 LTS. Dengan demikian, pengembang bekerja di dalam user space Ubuntu yang lengkap dengan isolasi pengguna yang tepat, sementara perintah `docker` berkomunikasi secara mulus dengan daemon melalui soket yang dijembatani oleh Docker Desktop.

### 7.2 Analisis Opsi Keamanan (`SecurityOptions`)
Pemeriksaan `docker info --format '{{json .SecurityOptions}}'` menghasilkan:
```json
["name=seccomp,profile=builtin","name=cgroupns"]
```
- **`name=seccomp,profile=builtin`**: Menunjukkan bahwa Docker Engine pada host telah mengaktifkan *Secure Computing Mode* dengan profil bawaan (*builtin*). Profil ini memblokir sejumlah besar pemanggilan sistem (*system calls*) yang berbahaya atau tidak diperlukan oleh container biasa (misalnya `reboot`, `sys_ptrace`, dan manipulasi modul kernel), sehingga secara signifikan mengurangi *attack surface* kernel.
- **`name=cgroupns`**: Menunjukkan bahwa *cgroup namespace* diaktifkan. Mekanisme ini membatasi container agar hanya dapat melihat hierarki cgroup miliknya sendiri, mencegah container membaca atau memanipulasi batasan sumber daya (*resource limits*) dari host atau container tetangga.
- **Catatan Kritis**: Tersedianya opsi ini adalah kapabilitas daemon, **bukan jaminan bahwa setiap container yang dijalankan secara otomatis aman**. Hardening container tetap membutuhkan konfigurasi eksplisit pada level aplikasi dan compose file, seperti penggunaan *non-root user*, *read-only root filesystem*, *no-new-privileges*, *drop capabilities*, dan pembatasan mount terhadap Docker socket.

### 7.3 Analisis Hak Akses Pengguna (*Principle of Least Privilege*)
Pada pengujian awal di distro `docker-desktop`, perintah dijalankan sebagai `root` (`#`), yang sangat tidak direkomendasikan karena kesalahan konfigurasi atau eksploitasi dapat berdampak langsung pada seluruh sistem. Pada lingkungan akhir Ubuntu, perintah dieksekusi oleh akun standar non-root `affan` (`$`). Hal ini sejalan dengan prinsip *least privilege* pada DevSecOps, di mana hak istimewa administratif hanya diberikan melalui `sudo` saat benar-benar diperlukan.

---


## 8. Tindak Lanjut

Berdasarkan penetapan baseline yang telah berhasil diverifikasi, tindak lanjut yang perlu dilaksanakan adalah:
1. **Penerapan *File Permission Hardening***: Menetapkan izin akses ketat pada direktori kerja, khususnya membatasi direktori `keys/` ke mode `700` (`chmod 700 ~/devsecops-lab/keys`) agar hanya dapat dibaca oleh pemilik akun `affan`.
2. **Pencegahan Publikasi Web Root**: Memastikan bahwa direktori `reports/`, `sbom/`, dan `keys/` tidak secara sengaja terpapar sebagai *public web root* pada container atau web server yang akan dibangun di bab-bab berikutnya.
3. **Penyusunan Aturan Penanganan Secret**: Menghindari penyimpanan kunci nyata, kata sandi, atau token di dalam repository Git lokal maupun commit history; menggunakan *environment variable* atau Docker BuildKit secret mount pada tahap build.
4. **Persiapan Modul Bab 2**: Menggunakan baseline lingkungan ini untuk memulai pemodelan ancaman (*threat modeling*) dan penulisan Dockerfile yang telah di-hardening.

---

## 9. Kesimpulan

Praktikum Bab 1 telah berhasil menetapkan *baseline* laboratorium DevSecOps secara lengkap dan valid pada lingkungan Windows 11 melalui WSL2 (Ubuntu 26.04 LTS) yang terintegrasi dengan Docker Desktop 4.84.0. Seluruh komponen inti—meliputi struktur direktori lab, Git 2.53.0, OpenSSL 3.5.5, cURL 8.18.0, Docker Engine 29.6.2, Docker Compose v5.3.1, serta mekanisme keamanan daemon `seccomp` dan `cgroupns`—telah terpasang, terkonfigurasi, dan terverifikasi berdasarkan bukti keluaran terminal aktual.

Kendala eksekusi yang sempat terjadi pada distro internal Docker Desktop berhasil diselesaikan melalui investigasi sistemik dan konfigurasi *WSL integration*, sehingga membuktikan pentingnya pemahaman arsitektur virtualisasi dan isolasi sistem dalam praktik DevSecOps. Lingkungan laboratorium kini telah siap digunakan untuk eksperimen keamanan tingkat lanjut pada bab berikutnya secara aman, konsisten, dan dapat direproduksi (*reproducible*).

---

## 10. Referensi

1. Ferry Astika Saputra, “Bab 1 — Fondasi Teoretis dan Kerangka Kerja DevSecOps,” repository DevSecOps PENS, `bab-01.md`, diakses 27 Agustus 2026: https://github.com/ferryas-pens/devsecops/blob/main/bab-01.md
2. NIST SP 800-218, *Secure Software Development Framework (SSDF) Version 1.1: Recommendations for Mitigating the Risk of Software Vulnerabilities*.
3. OWASP Foundation, *OWASP DevSecOps Guideline*.
4. Docker Documentation, *Docker Desktop WSL 2 backend and distro integration guidelines*.


