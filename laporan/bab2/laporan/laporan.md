# LAPORAN PRAKTIKUM BAB 2
## Konsep Container dan Instalasi Docker

**Nama**: ........................................................  
**NIM**: ..........................................................  
**Kelas**: ........................................................  
**Tanggal pelaksanaan**: 02 September 2026  

---

## 1. Tujuan Praktikum

1. **Memahami Arsitektur & Isolasi Kontainer**: Mengidentifikasi perbedaan teknis antara *Virtual Machine* (VM) dan kontainer, khususnya peran kernel Linux (*namespaces*, *cgroups v2*, dan *Overlay2*).
2. **Instalasi & Konfigurasi Docker Engine**: Mengonfigurasi repositori resmi Docker CE, kunci GPG terverifikasi, instalasi paket inti (`docker-ce`, `containerd.io`, `buildx`, `compose`), dan hak akses non-root grup `docker`.
3. **Manajemen Siklus Hidup Kontainer**: Mengoperasikan perintah esensial (`run`, `ps`, `logs`, `exec`, `rm`) serta memetakan port host-ke-kontainer (*port publishing*).
4. **Pembangunan Image Kustom**: Merancang Dockerfile berbasis distribusi minimalis (`nginx:1.26-alpine`), mengompilasi image `pens-web:1.0` via Docker BuildKit, dan memvalidasi akses via port host.
5. **Analisis Keamanan DevSecOps**: Mengevaluasi implikasi keamanan keanggotaan grup `docker`, bahaya tag `latest`, perbedaan instruksi `EXPOSE` vs flag `-p`, serta komparasi *attack surface* Debian vs Alpine.

---

## 2. Dasar Teori: Komparasi Virtual Machine dan Kontainer

Kontainer mengisolasi proses menggunakan fitur kernel sistem operasi host tanpa memerlukan *guest OS* atau *hypervisor*, menjadikannya jauh lebih efisien dibandingkan mesin virtual:

| Parameter Evaluasi | Virtual Machine (VM) | Kontainer (Docker) | Analisis Operasional & Keamanan |
|---|---|---|---|
| **Arsitektur Kernel** | Tiap VM membawa kernel OS sendiri | Berbagi kernel OS host (*shared kernel*) | Kontainer lebih ringan; VM memiliki isolasi perangkat keras lebih kuat. |
| **Ukuran Image** | Gigabytes (GB) | Puluhan hingga ratusan Megabytes (MB) | Kontainer mempercepat transfer jaringan dan efisiensi penyimpanan lokal. |
| **Waktu Startup** | Menit (booting full OS) | Milidetik hingga detik (eksekusi proses) | Kontainer memungkinkan *auto-scaling* elastis dan deployment instan. |
| **Mekanisme Isolasi**| Hypervisor (Type 1 / Type 2) | Linux Namespaces, cgroups, AppArmor/Seccomp | Isolasi kontainer tingkat proses; wajib konfigurasi *hardening* runtime. |
| **Kasus Penggunaan** | Multi-OS, isolasi ketat, legacy apps | Microservices, CI/CD, cloud-native apps | Praktik modern sering menjalankan kontainer di dalam VM (*hybrid*). |

---

## 3. Langkah Praktikum & Bukti Eksekusi

### 3.1 Instalasi Docker Engine & Verifikasi Izin Akses Non-Root
Repositori APT resmi Docker dikonfigurasi menggunakan kunci GPG terverifikasi pada `/etc/apt/keyrings/docker.gpg`. Paket `docker-ce`, `docker-ce-cli`, `containerd.io`, `docker-buildx-plugin`, dan `docker-compose-plugin` dipasang. Akun pengguna lokal dimasukkan ke dalam grup `docker` untuk memungkinkan eksekusi kontainer tanpa *sudo*.

```bash
sudo usermod -aG docker $USER && newgrp docker
docker version
docker run hello-world
```

![Verifikasi docker version dan pengujian container hello-world](../assets/Screenshot%202026-09-02%20104440.png)
*Gambar 1: Output docker version membuktikan integrasi Client dan Server Engine (v29.7.2) serta containerd (v2.3.4), dilanjutkan eksekusi sukses container hello-world.*

### 3.2 Deployment Nginx, Status Layanan, dan Cuplikan Log
Kontainer Nginx diunduh dan dijalankan di latar belakang (*detached mode*) dengan pemetaan port `8080:80`. Status operasional kontainer dan log proses pekerja diverifikasi sebagai bukti sistem bekerja:

```bash
docker pull nginx:1.30.4
docker run -d --name web-public -p 8080:80 nginx:1.30.4
docker ps && docker logs --tail 20 web-public
```

![Instansiasi container web-public, inspeksi status, dan pengecekan log](../assets/Screenshot%202026-09-02%20104803.png)
*Gambar 2: Output docker ps menunjukkan kontainer web-public aktif (Up 6 seconds, port 8080->80/tcp) dan docker logs mengonfirmasi worker processes siap menerima request.*

### 3.3 Verifikasi Respon HTTP Server via cURL
Layanan web Nginx yang dipublikasikan pada port 8080 host diuji keterjangkauannya menggunakan utilitas cURL:

```bash
curl http://localhost:8080
```

![Verifikasi respon HTTP server Nginx melalui curl](../assets/Screenshot%202026-09-02%20104838.png)
*Gambar 3: Respons cURL menampilkan payload HTML selamat datang Nginx, mengonfirmasi aturan port forwarding host ke container via iptables aktif.*

### 3.4 Pembangunan Image Kustom Melalui Dockerfile
Disusun berkas `Dockerfile` dan `index.html` kustom pada direktori `~/docker-lab/custom-web` berbasis base image minimalis `nginx:1.26-alpine`:

```dockerfile
FROM nginx:1.26-alpine
LABEL maintainer="admin@pens.ac.id"
COPY index.html /usr/share/nginx/html/index.html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

Image dikompilasi menggunakan Docker BuildKit: `docker build -t pens-web:1.0 .`.

![Eksekusi docker build menghasilkan image pens-web:1.0](../assets/Screenshot%202026-09-02%20110705.png)
*Gambar 4: Docker BuildKit menyelesaikan proses build 8 langkah dalam 4.8 detik dan menghasilkan image pens-web:1.0 secara efisien.*

### 3.5 Instansiasi dan Validasi Container Kustom `pens-app`
Image kustom dijalankan sebagai kontainer `pens-app` dengan pemetaan port `9090:80`, lalu diverifikasi melalui cURL ke port 9090 host:

```bash
docker run -d --name pens-app -p 9090:80 pens-web:1.0
curl http://localhost:9090
```

![Menjalankan container pens-app dan validasi konten kustom via curl](../assets/Screenshot%202026-09-02%20110731.png)
*Gambar 5: Eksekusi curl http://localhost:9090 berhasil menampilkan konten HTML kustom "Docker Lab PENS - Container berhasil berjalan".*

---

## 4. Analisis Masalah dan Diagnostik (Wajib)

Selama praktikum, ditemukan dua kendala operasional yang berhasil didiagnosis dan diselesaikan:
1. **Ketiadaan Utilitas `newgrp` pada Instalasi Minimal Ubuntu**:
   - *Gejala*: Eksekusi `newgrp docker` mengembalikan pesan `Command 'newgrp' not found`.
   - *Diagnosis*: Rilis minimal Ubuntu 26.04 (WSL2/cloud image) memisahkan utilitas `newgrp` ke dalam paket `util-linux-extra` demi perampingan footprint OS.
   - *Tindakan Korektif*: Memasang paket via `sudo apt install -y util-linux-extra`, lalu memperbarui sesi grup tanpa perlu logout.
2. **Kesalahan Format Sintaks OCI Tag pada Image Pull**:
   - *Gejala*: Perintah `docker pull nginx-1.30.4` menghasilkan galat `pull access denied for nginx-1.30.4, repository does not exist`.
   - *Diagnosis*: Format penamaan image OCI mewajibkan pemisah tanda titik dua (`:`) antara nama repositori dan tag versi (`<repository>:<tag>`). Karakter strip (`-`) dianggap sebagai bagian dari nama repositori yang tidak terdaftar di Docker Hub.
   - *Tindakan Korektif*: Memperbaiki sintaks perintah menjadi `docker pull nginx:1.30.4`, sehingga image berhasil diunduh.

---

## 5. Analisis Risiko Keamanan & Operasional (DevSecOps) (Wajib)

1. **Ekuivalensi Hak Akses Root pada Grup `docker`**:
   Memberikan keanggotaan grup `docker` kepada pengguna non-root membuka akses penuh ke UNIX socket `/var/run/docker.sock`. Karena Docker daemon berjalan sebagai root, pengguna dapat dengan mudah melakukan eskalasi hak akses (*privilege escalation*) ke root host dengan menjalankan kontainer yang me-mount filesystem host (`docker run -v /:/host alpine chroot /host`). Di lingkungan produksi, akses Docker CLI harus dibatasi ketat melalui RBAC atau menerapkan *Rootless Docker*.
2. **Bahaya Penggunaan Tag `latest`**:
   Tag `:latest` bersifat *mutable* (dapat ditimpa kapan saja oleh maintainer). Hal ini merusak prinsip *reproducibility* deployment, memicu inkonsistensi cache lokal antar-node, serta membuka celah serangan rantai pasok (*supply chain attack*). Praktik terbaik mewajibkan *semantic versioning* atau digest kriptografis SHA-256 (`nginx@sha256:...`).
3. **Perbedaan Instruksi `EXPOSE` vs Flag Runtime `-p` (`--publish`)**:
   `EXPOSE` pada Dockerfile murni berfungsi sebagai metadata dokumentasi pada manifest image OCI dan **tidak membuka port host sama sekali**. Sebaliknya, flag runtime `-p <host_port>:<container_port>` memerintahkan Docker daemon menyuntikkan aturan DNAT pada firewall *iptables/nftables* host sehingga port host benar-benar terbuka dan dapat diakses dari jaringan luar.
4. **Komparasi Base Image: Debian vs Alpine Linux**:
   - `nginx:1.30.4` (Debian): Ukuran ~140–190 MB, berbasis `glibc`, menyertakan paket utilitas lengkap (Bash, Perl, Coreutils). Memiliki *attack surface* lebih besar dengan potensi kerentanan CVE lebih tinggi.
   - `nginx:1.26-alpine` (Alpine): Ukuran ~40–45 MB (hemat 75%), berbasis `musl-libc` dan BusyBox. Sangat minim dependensi dan biner sistem, secara drastis memperkecil *attack surface* serta mempersulit penyerang saat tahap *post-exploitation*.

---

## 6. Rekomendasi Perbaikan untuk Lingkungan Produksi (Wajib)

1. **Penerapan Pengguna Non-Root**: Tambahkan instruksi pembuatan pengguna non-root pada Dockerfile (`USER appuser`, UID 10001) agar proses Nginx tidak berjalan dengan privilege root di dalam namespace kontainer.
2. **Read-Only Root Filesystem**: Jalankan kontainer dengan flag `--read-only` untuk mencegah modifikasi biner oleh penyerang, dan alokasikan `--tmpfs` pada direktori temporer seperti `/var/run` dan `/var/cache/nginx`.
3. **Pembatasan Sumber Daya (cgroups v2)**: Terapkan batas memori dan CPU eksplisit (`--memory="256m" --cpus="0.5" --pids-limit 100`) guna mencegah serangan *Denial of Service* (DoS) dan fenomena kehabisan memori host (*OOM killer*).
4. **Vulnerability Scanning & Image Signing**: Integrasikan pemindai kerentanan seperti **Trivy** pada pipeline CI/CD untuk memblokir image dengan temuan kerentanan *HIGH* atau *CRITICAL*, serta tandatangani image menggunakan **Cosign (Sigstore)** untuk menjamin integritas asal artefak.

---

## 7. Evaluasi dan Latihan Mandiri

1. **Mengapa penggunaan tag `latest` tidak dianjurkan untuk deployment yang harus reproducible?**  
   *Jawaban*: Tag `latest` adalah alias dinamis (*mutable pointer*) yang selalu menunjuk pada build terakhir. Dua build atau deployment yang dieksekusi pada waktu berbeda dengan kode sumber sama dapat menghasilkan artefak yang berbeda jika base image telah diperbarui oleh vendor, sehingga merusak replikasi lingkungan yang konsisten dan menyulitkan proses rollback.
2. **Jelaskan peran `containerd` dan `runc` dalam arsitektur Docker.**  
   *Jawaban*: `containerd` adalah *high-level container runtime* yang mengelola seluruh siklus hidup kontainer (start/stop/pause), transfer image dari registry, serta manajemen storage dan network. Sedangkan `runc` adalah *low-level OCI runtime* yang berinteraksi langsung dengan kernel Linux untuk membuat namespace, menetapkan limit cgroups, mengonfigurasi filter seccomp, dan mengeksekusi proses kontainer sebelum keluar (*exit*).
3. **Apa konsekuensi keamanan dari memasukkan user ke group `docker`?**  
   *Jawaban*: Memasukkan akun ke grup `docker` memberikan akses tulis ke socket `/var/run/docker.sock`. Karena Docker daemon berjalan dengan hak root, hal ini ekuivalen dengan memberikan hak root tanpa kata sandi (*unrestricted root equivalent*). Pengguna dapat dengan mudah mengambil alih host dengan me-mount direktori root host ke dalam kontainer.
4. **Bandingkan layer image `nginx:1.26-alpine` dan image custom yang Anda buat.**  
   *Jawaban*: Image `nginx:1.26-alpine` tersusun dari layer rootfs minimalis Alpine Linux, instalasi biner Nginx, konfigurasi default, dan direktori web standar. Image kustom `pens-web:1.0` menggunakan base image tersebut sebagai pondasi, kemudian menambahkan satu layer baru di atasnya melalui instruksi `COPY index.html ...` yang berisi artefak halaman statis kustom, serta menyematkan metadata `LABEL` dan `EXPOSE 80`.
5. **Kapan sebaiknya memilih VM daripada container?**  
   *Jawaban*: VM sebaiknya dipilih ketika: (1) Memerlukan isolasi keamanan *multi-tenant* tingkat perangkat keras (*hardware-level boundary*); (2) Menjalankan sistem operasi dengan kernel berbeda dari host (misal menjalankan Windows di host Linux); (3) Memerlukan akses modul kernel khusus atau driver perangkat keras tingkat rendah; atau (4) Menjalankan aplikasi *monolithic legacy* yang tidak dirancang untuk lingkungan modular.

---

## 8. Kesimpulan

Praktikum Bab 2 berhasil membuktikan prinsip fundamental kontainerisasi, instalasi komponen Docker CE (v29.7.2), serta pengelolaan siklus hidup kontainer pada Ubuntu 26.04 LTS (WSL2). Kontainer terbukti jauh lebih ringan dan efisien dibandingkan VM karena memanfaatkan *shared kernel* melalui abstraksi *namespaces* dan *cgroups*. Pembangunan image kustom `pens-web:1.0` berbasis Alpine Linux mendemonstrasikan efisiensi arsitektur *layering* UnionFS dengan ukuran ringkas (~45 MB) dan build time singkat (4.8 detik). Dari aspek DevSecOps, praktikum menegaskan pentingnya pembatasan hak grup `docker`, penghindaran tag `latest`, pemahaman peran metadata `EXPOSE` vs runtime `-p`, serta pemilihan base image minimalis guna memperkecil *attack surface* di lingkungan produksi.
