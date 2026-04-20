# Panduan Setup Development Server Linux untuk E-Ticket

## Overview Arsitektur
```
[Local Windows] ──git push──→ [GitHub: mashudizaini/eticket]
                                        │
                               git pull (manual)
                                        │
                              [Dev Server: 172.21.2.60]
                              Ubuntu 22.04 + Docker
                                        │
                              ┌─────────┴─────────┐
                         PostgreSQL           Oracle EBS
                          (container)       172.21.2.201
```

---

## BAGIAN 1 — Persiapan di Local (Windows)

### 1.1 Buat `.gitignore`

Buat file `.gitignore` di root folder project:

```gitignore
# Environment & Secrets
.env
backend/.env
*.env.local

# Python
__pycache__/
*.pyc
*.pyo
.venv/
venv/
*.egg-info/

# Node / React
frontend/node_modules/
frontend/build/
frontend/.env.local

# Docker data volumes
data/

# Upload files
backend/uploads/*
data/uploads/*
!backend/uploads/.gitkeep
!data/uploads/.gitkeep

# OS
.DS_Store
Thumbs.db

# IDE
.vscode/
.idea/
```

### 1.2 Buat `.gitkeep` untuk folder uploads

```bash
mkdir -p backend/uploads
echo "" > backend/uploads/.gitkeep
```

### 1.3 Buat GitHub Repository

1. Buka [github.com](https://github.com) → login sebagai **mashudizaini**
2. Klik **New repository**
3. Isi:
   - Repository name: `eticket`
   - Visibility: **Public**
   - Jangan centang "Add README" (project sudah ada)
4. Klik **Create repository**

### 1.4 Push Project ke GitHub

Jalankan di terminal lokal dari folder project:

```bash
git init
git add .
git commit -m "initial commit: eticket application"
git branch -M main
git remote add origin https://github.com/mashudizaini/eticket.git
git push -u origin main
```

> **Verifikasi:** buka `https://github.com/mashudizaini/eticket` — pastikan `.env` **tidak** ikut ter-upload.

---

## BAGIAN 2 — Setup Server Linux (172.21.2.60)

SSH ke server:
```bash
ssh itdev@172.21.2.60
```

### 2.1 Update System

```bash
sudo apt update && sudo apt upgrade -y
```

### 2.2 Install Docker

```bash
# Install dependencies
sudo apt install -y ca-certificates curl gnupg lsb-release

# Tambah Docker GPG key
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | \
  sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

# Tambah Docker repository
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
  https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```

### 2.3 Izinkan User `itdev` Jalankan Docker (tanpa sudo)

```bash
sudo usermod -aG docker itdev

# PENTING: logout lalu login ulang agar group aktif
exit
```

SSH masuk lagi, lalu verifikasi:
```bash
ssh itdev@172.21.2.60
docker --version
docker compose version
```

---

## BAGIAN 3 — Deploy Aplikasi di Server

### 3.1 Clone Repository

```bash
cd /home/itdev
git clone https://github.com/mashudizaini/eticket.git
cd eticket
```

### 3.2 Buat File `.env` di Server

```bash
nano .env
```

Isi dengan:
```env
# Oracle Database (untuk user validation)
ORACLE_PASSWORD=apps

# PostgreSQL
POSTGRES_PASSWORD=postgres

# JWT Secret Key — ganti dengan string random yang panjang
SECRET_KEY=dev-secret-key-eticket-2024-ganti-ini

# Timezone
TZ=Asia/Jakarta
```

Simpan: `Ctrl+X` → `Y` → `Enter`

Amankan permission file:
```bash
chmod 600 .env
```

### 3.3 Jalankan Aplikasi

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

### 3.4 Cek Status Container

```bash
docker compose -f docker-compose.prod.yml ps
```

Output yang diharapkan:
```
NAME                STATUS
eticket-db          Up (healthy)
eticket-backend     Up
eticket-frontend    Up
```

### 3.5 Cek Log (jika ada masalah)

```bash
# Semua container
docker compose -f docker-compose.prod.yml logs -f

# Backend saja
docker compose -f docker-compose.prod.yml logs -f backend
```

### 3.6 Test Koneksi Oracle dari Container

```bash
curl http://localhost:8000/auth/test-oracle
```

Response sukses: `{"status":"ok","database":"oracle","result":1}`

---

## BAGIAN 4 — Akses Aplikasi

Buka browser:

| URL                                          | Keterangan                |
|----------------------------------------------|---------------------------|
| `http://172.21.2.60`                         | Frontend (React)          |
| `http://172.21.2.60:8000/docs`               | Backend API Documentation |
| `http://172.21.2.60:8000/auth/test-oracle`   | Test koneksi Oracle       |
| `http://172.21.2.60:8000/auth/test-postgres` | Test koneksi PostgreSQL   |

---

## BAGIAN 5 — Cara Update Aplikasi (Setelah Push dari Lokal)

Setiap kali ada perubahan code, lakukan di server:

```bash
cd /home/itdev/eticket

# Pull perubahan terbaru
git pull origin main

# Rebuild dan restart
docker compose -f docker-compose.prod.yml up -d --build

# Cek status
docker compose -f docker-compose.prod.yml ps
```

---

## BAGIAN 6 — Perintah Berguna

```bash
# Stop semua container
docker compose -f docker-compose.prod.yml down

# Restart container tertentu
docker compose -f docker-compose.prod.yml restart backend

# Lihat log real-time
docker compose -f docker-compose.prod.yml logs -f backend

# Masuk ke dalam container backend
docker exec -it eticket-backend bash

# Cek penggunaan resource
docker stats
```

---

## Catatan Penting

+---------------------------+-----------------------------------------------------------------------------------------------+
| Hal                       | Keterangan                                                                                    |
|---------------------------|-----------------------------------------------------------------------------------------------|
| Oracle connectivity       | Server `172.21.2.60` dan Oracle `172.21.2.201` satu subnet — tidak perlu konfigurasi tambahan |
| File `.env`               | **Jangan pernah di-commit ke GitHub**, selalu buat manual di server                           |
| `docker-compose.prod.yml` | File yang dipakai di server Linux (bukan `docker-compose.yml`)                                |
| Port yang terbuka         | `80` (frontend), `8000` (backend API)                                                         |
+---------------------------+-----------------------------------------------------------------------------------------------+
