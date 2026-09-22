# LAPORAN PRAKTIKUM BAB 2
## Konsep Container dan Instalasi Docker

**Nama**: ........................................................  
**NIM**: ..........................................................  
**Kelas**: ........................................................  
**Tanggal pelaksanaan**: 02 September 2026  

---

## 1. Tujuan Praktikum

Praktikum Bab 2 berfokus pada penguasaan konsep fundamental kontainerisasi (*containerization*), instalasi komponen *Docker Community Edition* (CE) pada sistem operasi Ubuntu 26.04 LTS (WSL2), serta penerapan prinsip operasional dan keamanan pada siklus hidup container. Tujuan spesifik dari praktikum ini meliputi:

1. **Memahami Arsitektur dan Isolasi Container**: Mengidentifikasi perbedaan arsitektural antara mesin virtual (*Virtual Machine* / VM) dan container, khususnya peran kernel Linux primitives (*namespaces*, *control groups* / cgroups, dan *copy-on-write filesystem*) dalam menyediakan isolasi proses yang efisien dan berbobot ringan.
2. **Instalasi dan Konfigurasi Docker Engine**: Melakukan konfigurasi repositori APT resmi Docker, mengimpor kunci publik GPG terverifikasi, memasang paket `docker-ce`, `docker-ce-cli`, `containerd.io`, `docker-buildx-plugin`, dan `docker-compose-plugin`, serta mengonfigurasi hak akses non-root bagi pengguna lokal (`affan`).
3. **Manajemen Siklus Hidup Container**: Mengoperasikan perintah-perintah dasar Docker CLI untuk mengunduh image (*pull*), menjalankan container di latar belakang (*detached mode*) dengan pemetaan port (*port mapping*), menginspeksi log proses, mengeksekusi container interaktif berbasis shell, dan melakukan terminasi serta pembersihan (*cleanup*) resource.
4. **Pembangunan Image Kustom Melalui Dockerfile**: Merancang Dockerfile berbasis distribusi minimalis Alpine Linux (`nginx:1.26-alpine`), menyematkan metadata dan halaman statis HTML kustom, melakukan proses kompilasi image menggunakan Docker BuildKit, serta menguji verifikasi akses melalui port host.
5. **Analisis Troubleshooting dan Keamanan DevSecOps**: Menginvestigasi galat sintaks dan dependensi lingkungan (*util-linux-extra*, kesalahan penulisan OCI tag), mengevaluasi risiko eskalasi hak akses grup `docker`, menganalisis bahaya penggunaan tag `latest`, serta membedakan instruksi metadata `EXPOSE` dengan flag publikasi runtime `-p`.

---

## 2. Dasar Teori Singkat

### 2.1 Containerization vs Virtual Machine
Containerization adalah metodologi pengemasan aplikasi beserta seluruh pustaka dependensi, file konfigurasi, dan *userspace environment* ke dalam satu unit eksekusi yang konsisten di berbagai lingkungan komputasi. Tidak seperti *Virtual Machine* (VM) yang memvirtualisasikan perangkat keras fisik dan mewajibkan eksekusi kernel sistem operasi tamu (*guest OS*) di atas *Hypervisor*, container berjalan langsung di atas kernel sistem operasi host.

Isolasi proses pada container Linux diwujudkan melalui kombinasi fitur kernel:
- **Linux Namespaces**: Menyediakan partisi virtual terhadap sumber daya global sistem operasi. Enam namespace fundamental meliputi *PID* (penomoran dan isolasi proses), *NET* (antarmuka jaringan, routing table, dan firewall rules), *MNT* (tampilan hierarki mount filesystem), *IPC* (komunikasi antarproses dan shared memory), *UTS* (hostname dan nama domain), serta *USER* (pemetaan UID/GID container ke host).
- **Control Groups (cgroups v2)**: Mengatur batasan (*limits*), prioritas, dan akuntansi pemakaian sumber daya perangkat keras fisik, seperti kapasitas memori RAM, kuota CPU time, I/O bandwidth penyimpanan, dan batasan jumlah thread/proses (*pids limit*).
- **Copy-on-Write (CoW) / Union Filesystem**: Melalui driver penyimpanan seperti `overlay2`, container memanfaatkan sistem berkas berlapis (*layering*). Layer image bersifat *read-only* yang dapat dibagi pakai (*shared*) oleh banyak container, sedangkan perubahan data saat runtime disimpan pada satu layer teratas yang bersifat sementara dan dapat ditulis (*writable container layer*).

Pendekatan ini memberikan keunggulan signifikan pada container dalam hal efisiensi penyimpanan (*footprint* berukuran puluhan megabyte dibanding belasan gigabyte pada VM), waktu inisialisasi (*startup time* dalam hitungan milidetik), dan densitas utilisasi perangkat keras host yang jauh lebih tinggi.

### 2.2 Arsitektur Docker Engine
Docker mengadopsi arsitektur *client-server* modular yang terbagi menjadi empat komponen utama:
1. **Docker Client (`docker`)**: Utilitas Command Line Interface (CLI) yang digunakan oleh operator untuk mengirimkan instruksi eksekusi melalui REST API ke Docker daemon melalui UNIX socket (`/var/run/docker.sock`) atau koneksi TCP jaringan.
2. **Docker Daemon (`dockerd`)**: Layanan persisten (*background service*) yang mengelola objek-objek Docker tingkat tinggi, seperti konfigurasi jaringan (*bridge*, *overlay*), volume penyimpanan terkelola, manajemen image lokal, serta menerima request dari Docker client.
3. **containerd**: Daemon runtime container tingkat tinggi (*high-level container runtime*) standar industri yang bertanggung jawab atas siklus hidup container lengkap, manajemen pengunduhan image OCI, verifikasi penyimpanan image, dan pengawasan eksekusi container.
4. **runc**: Utilitas runtime container tingkat rendah (*low-level OCI runtime*) yang dioperasikan oleh containerd sesuai spesifikasi *Open Container Initiative* (OCI). `runc` berinteraksi langsung dengan kernel Linux untuk membuat namespace, mengonfigurasi cgroup, mengeksekusi `pivot_root`, dan meluncurkan proses utama container.

```
+-------------------------------------------------------------+
|                     Docker Client (CLI)                     |
+-------------------------------------------------------------+
                              | (REST API via UNIX Socket)
                              v
+-------------------------------------------------------------+
|                    Docker Daemon (dockerd)                  |
+-------------------------------------------------------------+
                              | (gRPC)
                              v
+-------------------------------------------------------------+
|                     containerd runtime                      |
+-------------------------------------------------------------+
                              | (OCI Runtime Spec)
                              v
+-------------------------------------------------------------+
|                            runc                             |
+-------------------------------------------------------------+
                              | (Clone / Namespaces / cgroups)
                              v
+-------------------------------------------------------------+
|              Kernel Linux (Namespaces & cgroups)            |
+-------------------------------------------------------------+
```

### 2.3 Mekanisme Port Mapping dan Jaringan Container
Secara default, container dijalankan di dalam *bridge network* privat terisolasi (biasanya `docker0` dengan subnet `172.17.0.0/16`). Container memiliki antarmuka jaringan virtual (`eth0`) dan alamat IP internal sendiri yang tidak dapat diakses langsung dari jaringan eksternal host.

Untuk mengekspos layanan container ke jaringan luar, Docker menggunakan mekanisme *Network Address Translation* (NAT) berbasis aturan firewall Linux (`iptables` atau `nftables`). Instruksi `EXPOSE` di dalam Dockerfile hanya berfungsi sebagai metadata dokumentatif yang menginformasikan kepada operator mengenai port fungsional layanan. Publikasi port aktif secara operasional hanya terjadi saat operator menambahkan argumen `-p <host_port>:<container_port>` pada perintah `docker run`. Melalui argumen ini, Docker daemon menginjeksikan aturan DNAT (*Destination NAT*) pada chain `PREROUTING` dan `DOCKER` di tabel iptables host, sehingga seluruh paket data yang masuk ke `<host_port>` host dialihkan secara transparan ke `<container_port>` milik container.

---

## 3. Alat dan Lingkungan Praktikum

Laboratorium praktikum dilaksanakan pada lingkungan kerja WSL2 (*Windows Subsystem for Linux*) dengan integrasi distribusi Ubuntu 26.04 LTS pada mesin host Windows 11 Enterprise/Pro. Spesifikasi lingkungan operasional dirangkum dalam tabel berikut:

| Komponen Lingkungan | Spesifikasi Aktual / Versi | Catatan Operasional |
|---|---|---|
| **Sistem Operasi Host** | Windows 11 Enterprise (`10.0.26200.9168`) | Sistem operasi utama workstation |
| **Platform Virtualisasi** | WSL2 (*WSL version 2.6.2.0*) | Kernel Linux tervirtualisasi di atas Hyper-V architecture |
| **Kernel Linux** | `Linux 6.18.33.2-microsoft-standard-WSL2` | Kernel host dengan dukungan cgroups v2 dan namespaces |
| **Distribusi Pengujian** | Ubuntu 26.04 LTS (*Resolute Raccoon*) | Lingkungan eksekusi lab terisolasi |
| **Arsitektur CPU** | `x86_64` (`linux/amd64`) | Arsitektur target kompilasi dan eksekusi binary |
| **Akun Pengguna** | `affan` (`UID=1000`, `GID=1000`) | Akun non-root, anggota grup `sudo` dan `docker` |
| **Docker Engine (CE)** | `29.7.2` (API `1.55`, Go `go1.26.5`) | Daemon dan Client Docker Community Edition |
| **High-level Runtime** | `containerd.io` versi `v2.3.4` | Pengelola siklus hidup image dan container OCI |
| **Low-level Runtime** | `runc` versi `1.4.3` | Executor OCI berbasis Linux kernel primitives |
| **Docker Build Engine** | Docker BuildKit (terintegrasi CLI) | Mesin kompilasi image berbasis DAG paralel |

---

## 4. Langkah Kerja dan Bukti Pelaksanaan

Praktikum dieksekusi secara bertahap mengikuti alur kerja standardisasi deployment kontainer, dimulai dari instalasi dependensi, konfigurasi repositori, pengujian container publik, hingga kompilasi image kustom.

### 4.1 Persiapan Repositori dan Instalasi Docker CE

Langkah awal dimulai dengan membuat struktur direktori kerja terisolasi `~/docker-lab/bab-2` untuk menampung seluruh berkas konfigurasi praktikum, diikuti pembaruan indeks repositori sistem.

![Gambar 4.1: Inisialisasi direktori lab dan pembaruan indeks repositori apt](../assets/Screenshot%202026-09-02%20103901.png)
*Gambar 4.1: Pembuatan direktori `~/docker-lab/bab-2` dan eksekusi `sudo apt update` pada Ubuntu 26.04.*

Selanjutnya, dilakukan verifikasi dan pemasangan paket utilitas prasyarat keamanan jaringan, meliputi `ca-certificates`, `curl`, `gnupg`, dan `lsb-release` guna memastikan proses komunikasi repositori eksternal terenkripsi dan tervalidasi.

![Gambar 4.2: Verifikasi dependensi ca-certificates, curl, gnupg, dan lsb-release](../assets/Screenshot%202026-09-02%20104012.png)
*Gambar 4.2: Konfirmasi paket dependensi kriptografi dan jaringan telah berada pada versi termutakhir.*

Untuk mengamankan integritas paket instalasi Docker, direktori keyring `/etc/apt/keyrings` dibuat dengan hak akses `0755`. Kunci publik GPG resmi Docker diunduh dan dide-armor ke `/etc/apt/keyrings/docker.gpg`, kemudian repositori resmi Docker ditambahkan ke dalam daftar sumber APT.

![Gambar 4.3: Penambahan kunci GPG dan repositori resmi Docker](../assets/Screenshot%202026-09-02%20104118.png)
*Gambar 4.3: Konfigurasi file `/etc/apt/sources.list.d/docker.list` dengan verifikasi signature GPG.*

Paket inti Docker Community Edition dipasang ke sistem, mencakup engine utama (`docker-ce`), antarmuka baris perintah (`docker-ce-cli`), runtime container OCI (`containerd.io`), plugin pembangunan paralel (`docker-buildx-plugin`), serta orkestrator multi-container (`docker-compose-plugin`).

![Gambar 4.4: Pemasangan paket Docker CE dan containerd](../assets/Screenshot%202026-09-02%20104217.png)
*Gambar 4.4: Proses instalasi 15 paket dependensi Docker CE dan komponen jaringan firewall.*

---

### 4.2 Konfigurasi Izin Akses Non-Root dan Verifikasi Docker Engine

Secara default, Docker daemon berjalan di bawah akun `root` dan mengikat UNIX socket `/var/run/docker.sock` dengan kepemilikan grup `docker`. Agar pengguna standar `affan` dapat mengelola container tanpa eskalasi manual `sudo`, akun dimasukkan ke dalam grup sekunder `docker`.

![Gambar 4.5: Penambahan pengguna ke grup docker dan troubleshooting util-linux-extra](../assets/Screenshot%202026-09-02%20104423.png)
*Gambar 4.5: Eksekusi `usermod -aG docker`, resolusi dependensi `util-linux-extra`, dan pembaruan grup via `newgrp`.*

Setelah konfigurasi grup aktif, verifikasi menyeluruh terhadap subsistem Docker Client dan Server dilakukan menggunakan `docker version`, dilanjutkan dengan eksekusi container uji `hello-world`.

![Gambar 4.6: Verifikasi docker version dan pengujian container hello-world](../assets/Screenshot%202026-09-02%20104440.png)
*Gambar 4.6: Output `docker version` dan eksekusi sukses container `hello-world` membuktikan koneksi client-daemon.*

Keluaran terminal pada Gambar 4.6 mengonfirmasi bahwa Docker Client (v29.7.2) berhasil berkomunikasi dengan Docker Server Engine (v29.7.2), containerd (v2.3.4), dan runc (v1.4.3), serta berhasil melakukan *pulling* dan eksekusi container tanpa hak `sudo`.

---

### 4.3 Deployment Container Nginx dan Eksplorasi Container Interaktif

Pengujian dilanjutkan dengan mengunduh image web server Nginx rilis stabil. Pada tahap ini terjadi kesalahan penulisan sintaks tag yang kemudian berhasil diperbaiki ke format OCI yang valid (`nginx:1.30.4`).

![Gambar 4.7: Troubleshooting penulisan tag dan pengunduhan image nginx:1.30.4](../assets/Screenshot%202026-09-02%20104656.png)
*Gambar 4.7: Diagnosa error `pull access denied` akibat sintaks `nginx-1.30.4` dan perbaikan ke `nginx:1.30.4`.*

Container Nginx kemudian diinstansiasi di latar belakang (*detached mode*) dengan nama `web-public`, memetakan port 8080 pada host ke port 80 di dalam container. Status container dan catatan log proses pekerja (*worker processes*) diperiksa secara seksama.

![Gambar 4.8: Instansiasi container web-public, inspeksi status, dan pengecekan log](../assets/Screenshot%202026-09-02%20104803.png)
*Gambar 4.8: Container `web-public` aktif (`Up 6 seconds`) dengan port mapping `0.0.0.0:8080->80/tcp`.*

Layanan web yang berjalan di dalam container kemudian divalidasi dari sisi host menggunakan utilitas cURL ke `http://localhost:8080`.

![Gambar 4.9: Verifikasi respon HTTP server Nginx melalui curl](../assets/Screenshot%202026-09-02%20104838.png)
*Gambar 4.9: Respon payload HTML halaman selamat datang membuktikan forwarding port 8080->80 berfungsi sempurna.*

Untuk memahami isolasi sistem berkas dan namespace secara langsung, container interaktif berbasis distribusi Ubuntu 26.04 dijalankan dengan alokasi Pseudo-TTY (`-t`) dan STDIN terbuka (`-i`).

![Gambar 4.10: Eksplorasi container interaktif ubuntu:26.04](../assets/Screenshot%202026-09-02%20105418.png)
*Gambar 4.10: Akses shell interaktif `root@9fb628d5a5cf` dan verifikasi rilis OS via `/etc/os-release`.*

Setelah eksperimen container publik selesai, sanitasi sumber daya dilakukan dengan menghapus kedua container secara paksa (`docker rm -f`) guna membebaskan port 8080 dan alokasi memori sistem.

![Gambar 4.11: Pembersihan container web-public dan ubuntu-test](../assets/Screenshot%202026-09-02%20105454.png)
*Gambar 4.11: Penghapusan container uji untuk mencegah konflik sumber daya pada tahap berikutnya.*

---

### 4.4 Pembangunan dan Pengujian Image Custom `pens-web:1.0`

Tahap akhir praktikum adalah membangun image custom menggunakan Dockerfile. Direktori kerja `~/docker-lab/custom-web` dibuat, kemudian berkas `index.html` dan `Dockerfile` disusun dengan mendefinisikan image dasar minimalis `nginx:1.26-alpine`.

![Gambar 4.12: Penulisan berkas index.html dan Dockerfile custom](../assets/Screenshot%202026-09-02%20110657.png)
*Gambar 4.12: Pembuatan artefak halaman web statis dan spesifikasi instruksi build Dockerfile.*

Kandungan Dockerfile yang didefinisikan mencakup:
```dockerfile
FROM nginx:1.26-alpine
LABEL maintainer="admin@pens.ac.id"
COPY index.html /usr/share/nginx/html/index.html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

Proses kompilasi image dijalankan menggunakan perintah `docker build -t pens-web:1.0 .`. Docker BuildKit memproses 8 tahapan instruksi, mengunduh base image Alpine, menyalin berkas `index.html`, dan mengekspor image akhir bertag `pens-web:1.0`.

![Gambar 4.13: Eksekusi docker build menghasilkan image pens-web:1.0](../assets/Screenshot%202026-09-02%20110705.png)
*Gambar 4.13: BuildKit menyelesaikan proses build dalam waktu 4.8 detik dengan 8 langkah kompilasi.*

Image `pens-web:1.0` yang telah berhasil dibangun kemudian dijalankan sebagai container bernama `pens-app` dengan pemetaan port `9090:80`. Akses konten diuji melalui cURL ke `http://localhost:9090`.

![Gambar 4.14: Menjalankan container pens-app dan validasi konten kustom via curl](../assets/Screenshot%202026-09-02%20110731.png)
*Gambar 4.14: Container `pens-app` berhasil merespon dengan konten HTML kustom `Docker Lab PENS`.*

---

## 5. Analisis Masalah dan Troubleshooting

Selama pelaksanaan eksperimen laboratorium Bab 2, ditemukan tiga kendala teknis operasional yang berhasil diidentifikasi akar masalahnya dan diselesaikan secara sistemik:

### 5.1 Kendala Ketiadaan Utilitas `newgrp` pada Instalasi Minimal Ubuntu
- **Gejala / Error**: Ketika pengguna menjalankan perintah `newgrp docker` untuk memperbarui sesi shell dengan keanggotaan grup baru tanpa harus logout, sistem mengembalikan pesan kesalahan:
  ```text
  Command 'newgrp' not found, but can be installed with:
  sudo apt install util-linux-extra
  ```
- **Akar Masalah (*Root Cause*)**: Distribusi Ubuntu 26.04 LTS versi minimal (khususnya *cloud/WSL images*) mengoptimalkan ukuran instalasi awal dengan memangkas paket-paket biner tambahan. Utilitas `newgrp` yang secara historis berada di dalam paket `login` atau `util-linux`, pada rilis Ubuntu modern dipisahkan ke dalam paket terpisah bernama `util-linux-extra`.
- **Solusi dan Tindakan Korektif**: Melakukan instalasi paket penyedia biner melalui perintah `sudo apt install util-linux-extra`. Setelah paket terpasang beserta dependensinya (`liblastlog2-2`), perintah `newgrp docker` berhasil dieksekusi dan pengguna `affan` langsung memperoleh hak akses ke Docker daemon socket tanpa perlu me-restart sesi WSL2.

### 5.2 Kesalahan Sintaks Delimiter Penamaan Image OCI (`nginx-1.30.4`)
- **Gejala / Error**: Perintah pengunduhan image gagal dengan pesan penolakan akses:
  ```text
  Error response from daemon: pull access denied for nginx-1.30.4, repository does not exist or may require 'docker login'
  ```
- **Akar Masalah (*Root Cause*)**: Terjadi kesalahan penulisan sintaks (*syntax error*) di mana pemisah antara nama repositori (`nginx`) dan versi tag (`1.30.4`) menggunakan tanda hubung (*hyphen* `-`) alih-alih tanda titik dua (*colon* `:`). Sesuai spesifikasi OCI (*Open Container Initiative Distribution Spec*), Docker menginterpretasikan `nginx-1.30.4` sebagai nama repositori tunggal bertag implisit `:latest` (`docker.io/library/nginx-1.30.4:latest`), yang tidak terdaftar pada Docker Hub.
- **Solusi dan Tindakan Korektif**: Mengoreksi perintah menjadi `docker pull nginx:1.30.4`. Docker daemon berhasil mengenali repositori resmi `library/nginx` dengan tag `1.30.4` dan mengunduh seluruh layer image secara sempurna.

### 5.3 Interupsi Input EOF pada Pembuatan Berkas Web Statis
- **Gejala / Error**: Muncul karakter pembatalan `^C` pada baris perintah saat mencoba menulis berkas `index.html` menggunakan *heredoc* (`cat > index.html << 'EOF'`).
- **Akar Masalah (*Root Cause*)**: Operator menekan tombol kombinasi `Ctrl+C` sebelum memasukkan token penutup `EOF`, sehingga proses penulisan terputus dan berkas belum terbuat atau berukuran 0 byte (terlihat dari hasil `ls` berikutnya yang masih kosong).
- **Solusi dan Tindakan Korektif**: Operator mengulang eksekusi heredoc secara utuh dengan memasukkan baris kode HTML dan mengakhirinya dengan token penutup `EOF` pada baris baru tanpa spasi. Berkas `index.html` berhasil dibuat dengan integritas data yang valid.

---

## 6. Analisis Keamanan dan Operasional (DevSecOps)

### 6.1 Risiko Keamanan Hak Akses Grup `docker` (Ekuivalensi Hak Root Host)
Menambahkan pengguna standar ke dalam grup `docker` (`usermod -aG docker $USER`) adalah kemudahan operasional yang umum digunakan di lingkungan pengembangan lokal, namun **memiliki risiko keamanan kritis yang setara dengan memberikan hak `sudo` tanpa kata sandi (*passwordless root*)**.

Akar risiko ini terletak pada sifat komunikasi Docker. Docker daemon berjalan dengan hak istimewa penuh (`root`) pada host. Setiap entitas yang memiliki izin baca-tulis (*read-write*) ke UNIX socket `/var/run/docker.sock` dapat memerintahkan daemon untuk mengeksekusi aksi apapun pada host. Sebagai ilustrasi kerentanan:
```bash
# Eksploitasi sederhana untuk membaca shadow file host tanpa sudo:
docker run --rm -v /:/host-root ubuntu:26.04 cat /host-root/etc/shadow
```
Melalui perintah di atas, container dapat me-mount seluruh root filesystem host (`/`) ke dalam direktori container, memberikan kemampuan bagi pengguna biasa untuk memodifikasi konfigurasi sistem, menambahkan SSH key baru, atau membaca berkas rahasia host.

**Rekomendasi DevSecOps**:
1. Di lingkungan multi-pengguna atau produksi, hindari menambahkan akun pengembang ke grup `docker`.
2. Terapkan **Rootless Docker** (`dockerd-rootless.sh`), di mana daemon Docker berjalan di dalam *user namespace* milik pengguna non-root tanpa hak istimewa kernel host.
3. Gunakan perkakas alternatif seperti **Podman** yang secara arsitektural tidak bergantung pada daemon terpusat (*daemonless*) dan secara bawaan mengisolasi container dalam non-root user namespace.

### 6.2 Bahaya Penggunaan Tag `latest` pada Pipeline CI/CD
Penggunaan tag `:latest` (atau image tanpa tag eksplisit) sangat tidak dianjurkan dalam implementasi DevSecOps karena melanggar prinsip *reproducibility* dan *immutability*. Tag `:latest` bersifat dinamis (*pointer mutable*); pemilik repositori dapat memperbarui image di balik tag tersebut kapan saja tanpa pemberitahuan.

Konsekuensi risiko meliputi:
- **Build & Deployment Non-Deterministik**: Dua build pipeline yang dijalankan pada waktu berbeda dengan kode sumber identik dapat menghasilkan artefak dengan perilaku berbeda karena dependensi dasar image berubah secara tiba-tiba.
- **Kerentanan Pasokan Perangkat Lunak (*Supply Chain Attack*)**: Jika akun registry image terkompromi, penyerang dapat menimpa tag `:latest` dengan image berbahaya (*malicious image*) yang secara otomatis ditarik oleh sistem produksi.
- **Kesulitan Audit dan Forensik**: Ketika insiden keamanan terjadi, tim forensik tidak dapat memastikan secara pasti versi kode atau biner apa yang dieksekusi di runtime hanya berdasarkan nama tag `:latest`.

**Rekomendasi DevSecOps**:
Gunakan penomoran versi semantik ketat (*Semantic Versioning*, misal `pens-web:1.0.0`), atau lebih aman lagi, kunci referensi image menggunakan digest kriptografis SHA-256 yang bersifat *immutable*:
```dockerfile
FROM nginx@sha256:09cc2702709e6388d979d8030e3ab4eb1ceb699b2dced26d7543e872a822e823
```

### 6.3 Perbedaan Mendasar Instruksi `EXPOSE` vs Flag Runtime `-p` (`--publish`)
Terdapat kesalahpahaman umum bahwa instruksi `EXPOSE` pada Dockerfile membuka akses port container ke dunia luar. Secara teknis, kedua mekanisme ini memiliki fungsi yang sepenuhnya berbeda:

| Parameter | Level Operasi | Fungsi Teknis | Efek Jaringan Host |
|---|---|---|---|
| `EXPOSE <port>` | Build Time (Dockerfile) | Metadata & Dokumentasi | **Tidak membuka port host**. Hanya mencatat port fungsional layanan pada manifest image OCI dan menjadi acuan flag `-P` (publikasi port acak). |
| `-p <host>:<cont>` | Runtime (`docker run`) | Alokasi Jaringan Nyata | **Membuka port host**. Memerintahkan Docker daemon untuk menyuntikkan aturan DNAT pada firewall iptables/nftables host dan mengarahkan lalu lintas data ke IP container. |

Implikasi keamanannya: Layanan yang di-`EXPOSE` pada Dockerfile tidak rentan terhadap serangan dari luar host sebelum flag `-p` diberikan secara sadar oleh operator. Namun, jika operator menjalankan `docker run -P` (huruf kapital), Docker akan mempublikasikan seluruh port yang terdaftar di `EXPOSE` ke port acak berperingkat tinggi pada host, yang dapat membuka antarmuka administratif yang tidak diinginkan ke jaringan publik.

### 6.4 Perbandingan Base Image: Debian (`nginx:1.30.4`) vs Alpine (`nginx:1.26-alpine`)
Pada praktikum ini, digunakan dua varian base image Nginx: `nginx:1.30.4` (berbasis Debian) dan `nginx:1.26-alpine` (berbasis Alpine Linux). Perbandingan metrik keamanan dan operasionalnya disajikan dalam tabel berikut:

| Parameter Evaluasi | `nginx:1.30.4` (Debian-based) | `nginx:1.26-alpine` (Alpine-based) | Analisis DevSecOps |
|---|---|---|---|
| **Ukuran Image** | ~140 MB – 190 MB | ~40 MB – 45 MB | Alpine menghemat storage host hingga 75% dan mempercepat proses penarikan image di pipeline CI/CD. |
| **C Library** | GNU C Library (`glibc`) | `musl libc` | `musl libc` jauh lebih ringkas, namun perlu uji kompatibilitas terhadap aplikasi C/C++ tertentu. |
| **Utilitas Sistem / Shell** | Bash, Coreutils lengkap, Perl, apt | BusyBox, Almquist Shell (`ash`), apk | Alpine meminimalkan utilitas bawaan; ketiadaan compiler dan biner berlebih menyulitkan penyerang saat *post-exploitation*. |
| **Attack Surface & CVE** | Lebih besar (puluhan dependensi OS) | Sangat minimal (komponen esensial saja) | Pengurangan jumlah paket biner berbanding lurus dengan penurunan potensi *Known Vulnerabilities* (CVE). |

---

## 7. Evaluasi dan Jawaban Latihan Mandiri

Berikut adalah pembahasan komprehensif terhadap lima pertanyaan evaluasi yang diajukan pada modul Bab 2:

### 1. Mengapa penggunaan tag `latest` tidak dianjurkan untuk deployment yang harus reproducible?
**Jawaban**:
Tag `latest` bukanlah penanda versi yang statis, melainkan alias *mutable* (dapat ditimpa) yang secara otomatis menunjuk pada commit atau build terakhir yang di-push ke registry. Penggunaan tag ini merusak prinsip *reproducible deployment* karena:
1. Dua mesin atau dua proses pipeline build yang dijalankan pada waktu berbeda dapat mengunduh konten biner yang berbeda meskipun menggunakan nama tag yang sama (`latest`), jika image dasar telah di-update oleh vendor.
2. Mekanisme caching lokal pada Docker host dapat menyebabkan inkonsistensi: satu host menggunakan image `latest` versi lama yang telah tersimpan di cache lokal, sedangkan host lain mengunduh image `latest` versi terbaru dari registry.
3. Menghalangi proses *rollback* yang presisi saat terjadi insiden produksi, karena riwayat identitas image sebelumnya telah tertimpa oleh pointer `latest` baru.

### 2. Jelaskan peran `containerd` dan `runc` dalam arsitektur Docker.
**Jawaban**:
Dalam standarisasi arsitektur kontainer modern (OCI):
- **`containerd`** bertindak sebagai *high-level container runtime*. Peran utamanya meliputi pengelolaan siklus hidup container secara menyeluruh (start, stop, pause, resume), penanganan transfer dan penyimpanan image dari registry OCI, manajemen volume storage dan network namespace, serta meneruskan instruksi eksekusi ke low-level runtime.
- **`runc`** bertindak sebagai *low-level OCI runtime*. `runc` adalah utilitas CLI ringan yang dibuat berdasarkan spesifikasi OCI Runtime. Perannya sangat spesifik dan berdurasi singkat: menerima bundle OCI (rootfs dan berkas `config.json`) dari `containerd`, memanggil syscall kernel Linux (`clone`, `unshare`, `setns`) untuk menciptakan namespace terisolasi, mengonfigurasi batas cgroup, menetapkan seccomp filter, dan mengeksekusi proses utama container. Setelah container berjalan, proses `runc` keluar (*exits*), menyerahkan pengawasan proses ke `containerd-shim`.

### 3. Apa konsekuensi keamanan dari memasukkan user ke group `docker`?
**Jawaban**:
Memasukkan akun pengguna ke dalam grup `docker` memberikan hak akses baca-tulis penuh terhadap UNIX socket Docker daemon (`/var/run/docker.sock`). Karena daemon Docker dieksekusi dengan privilege `root` pada kernel host, kepemilikan akses ini secara teknis **memberikan hak istimewa setara `root` tanpa pengawasan password (*unrestricted root equivalent*)**. Pengguna dapat dengan mudah melewati seluruh restriksi direktori host dengan menjalankan container yang me-mount direktori sensitif host (`-v /:/host`), memanipulasi file `/etc/passwd`, `/etc/sudoers`, atau mengambil alih kendali sistem operasi host secara keseluruhan.

### 4. Bandingkan layer image `nginx:1.26-alpine` dan image custom `pens-web:1.0` yang Anda buat.
**Jawaban**:
- **Image `nginx:1.26-alpine`**: Merupakan base image yang terdiri dari layer-layer dasar Alpine Linux (root filesystem minimalis berbasis `musl libc` dan BusyBox) ditambah layer instalasi biner Nginx, modul-modul pendukung, dan konfigurasi default Nginx. Seluruh layer ini bersifat *read-only* dan memiliki hash SHA-256 tetap dari registry resmi.
- **Image Custom `pens-web:1.0`**: Dibangun di atas (*stacked upon*) image `nginx:1.26-alpine`. Berdasarkan arsitektur UnionFS/OverlayFS, image custom ini menggunakan kembali (*shares*) seluruh layer milik `nginx:1.26-alpine` tanpa duplikasi data, lalu menambahkan satu layer *read-only* baru di atasnya yang dihasilkan oleh instruksi `COPY index.html /usr/share/nginx/html/index.html` (berukuran ~68 byte). Metadata image juga diperbarui dengan instruksi `LABEL maintainer="admin@pens.ac.id"`, `EXPOSE 80`, dan `CMD`. Pendekatan layering ini memastikan proses build berlangsung sangat cepat (4.8 detik pada praktikum) dan sangat hemat ruang disk.

### 5. Kapan sebaiknya memilih VM daripada container?
**Jawaban**:
Virtual Machine (VM) sebaiknya dipilih dibanding container pada skenario-skenario berikut:
1. **Kebutuhan Isolasi Keamanan Tingkat Tinggi (*Strong Multi-Tenancy*)**: Pada lingkungan *public cloud* atau sistem perbankan di mana beban kerja dari penyewa (*tenants*) yang berbeda dan tidak saling percaya harus dieksekusi pada perangkat keras yang sama. VM menyediakan boundary isolasi perangkat keras berbasis Hypervisor yang jauh lebih kokoh dibandingkan isolasi kernel sharing pada container.
2. **Perbedaan Sistem Operasi dan Kernel**: Ketika aplikasi membutuhkan sistem operasi non-Linux (misalnya Windows Server lawas) atau memerlukan modul/versi kernel Linux yang sangat spesifik yang tidak kompatibel dengan kernel host.
3. **Pemberian Akses Administratif Penuh (*Full Kernel/Hardware Control*)**: Jika pengguna atau aplikasi memerlukan akses langsung ke konfigurasi kernel, modifikasi parameter sistem mendalam, atau perangkat keras khusus tanpa membahayakan host fisik.

---

## 8. Rekomendasi Penerapan pada Lingkungan Production-Like

Untuk mengadaptasi konfigurasi dasar laboratorium Bab 2 menuju lingkungan produksi yang memenuhi standar keamanan industri (*DevSecOps hardening*), langkah-langkah rekomendasi berikut harus diterapkan:

1. **Implementasi Non-Root User pada Container**:
   Pada Dockerfile kustom, hindari menjalankan proses Nginx sebagai `root`. Definisikan pengguna non-root menggunakan instruksi `USER`:
   ```dockerfile
   # Ubah kepemilikan direktori cache dan log nginx ke user non-root
   RUN touch /var/run/nginx.pid && \
       chown -R nginx:nginx /var/run/nginx.pid /var/cache/nginx /var/log/nginx
   USER nginx
   ```
2. **Penerapan Read-Only Filesystem dan Pembatasan Kapabilitas**:
   Jalankan container dengan filesystem sistem operasi yang dikunci (*read-only*) untuk mencegah penyerang menyuntikkan script atau malware pada direktori web:
   ```bash
   docker run -d --name pens-prod \
     --read-only \
     --tmpfs /var/run:rw,noexec,nosuid \
     --tmpfs /var/cache/nginx:rw,noexec,nosuid \
     --cap-drop ALL \
     --cap-add NET_BIND_SERVICE \
     --security-opt no-new-privileges:true \
     -p 80:8080 pens-web:1.0
   ```
3. **Pembatasan Sumber Daya Berbasis cgroups v2**:
   Tetapkan alokasi batas memori dan CPU maksimum untuk mencegah serangan *Denial of Service* (DoS) akibat kebocoran memori atau konsumsi CPU berlebih (*fork bomb*):
   ```bash
   docker run -d --name pens-prod \
     --memory="256m" \
     --cpus="0.5" \
     --pids-limit 100 \
     -p 80:80 pens-web:1.0
   ```
4. **Integrasi Pemindaian Kerentanan Image (*Vulnerability Scanning*)**:
   Sebelum image di-push ke registry produksi, integrasikan alat pemindai seperti **Trivy** atau **Grype** ke dalam pipeline CI/CD untuk mendeteksi kerentanan CVE pada paket OS dan dependensi:
   ```bash
   trivy image --severity HIGH,CRITICAL pens-web:1.0
   ```
5. **Penandatanganan Image Kriptografis (*Image Signing*)**:
   Gunakan **Cosign (Sigstore)** untuk menandatangani image yang telah lolos pengujian, dan terapkan *admission controller* (seperti Kyverno atau OPA Gatekeeper) di kluster Kubernetes untuk menolak eksekusi image yang tidak memiliki tanda tangan digital valid.

---

## 9. Kesimpulan

Praktikum Bab 2 telah berhasil membuktikan dan menguji prinsip dasar kontainerisasi, instalasi Docker Community Edition (v29.7.2), serta pengelolaan siklus hidup container pada lingkungan Ubuntu 26.04 LTS (WSL2). Seluruh target kompetensi pembelajaran telah tercapai secara komprehensif:

1. Komponen inti Docker Engine (dockerd, containerd v2.3.4, runc v1.4.3, dan Docker BuildKit) telah terpasang melalui repositori resmi terverifikasi GPG dan terbukti fungsional mengeksekusi container tanpa eskalasi hak akses `sudo`.
2. Pengujian container publik `nginx:1.30.4` dan `ubuntu:26.04` membuktikan efektivitas isolasi namespace sistem operasi serta mekanisme penerusan port (*port forwarding*) host-ke-container via iptables.
3. Pembangunan image kustom `pens-web:1.0` membuktikan efisiensi arsitektur *layering* UnionFS berbasis base image minimalis Alpine Linux (`nginx:1.26-alpine`) yang menghasilkan ukuran artefak ringkas dan waktu build cepat (4.8 detik).
4. Kendala teknis yang muncul—meliputi ketiadaan utilitas `newgrp`, kesalahan sintaks tag OCI, dan interupsi heredoc—berhasil diselesaikan melalui pendekatan investigasi sistemik.
5. Analisis keamanan DevSecOps menegaskan bahwa keanggotaan grup `docker` memiliki ekuivalensi risiko dengan hak root host, instruksi `EXPOSE` berbeda secara fundamental dari flag `-p`, dan penggunaan tag `latest` harus dihindari di lingkungan produksi demi menjamin *reproducibility* serta keamanan rantai pasok perangkat lunak.

---

## 10. Referensi

1. Ferry Astika Saputra, “Bab 2 — Konsep Container dan Instalasi Docker,” repository DevSecOps PENS, `bab-02.md`, diakses 02 September 2026: https://github.com/ferryas-pens/devsecops/blob/main/bab-02.md
2. Docker Documentation, “Docker Architecture and Overview,” Docker Docs, 2026: https://docs.docker.com/get-started/overview/
3. Open Container Initiative (OCI), “Image Format Specification (v1.1.0)” & “Runtime Specification (v1.2.0)”, 2026: https://opencontainers.org/
4. Linux Kernel Organization, “Overview of Namespaces (namespaces(7)) and Control Groups (cgroups(7)),” Linux Man Pages: https://man7.org/linux/man-pages/man7/namespaces.7.html
5. Center for Internet Security (CIS), “CIS Docker Benchmark v1.6.0,” CIS Security Guidelines, 2026.
6. NIST Special Publication 800-190, “Application Container Security Guide,” National Institute of Standards and Technology, US Department of Commerce.
