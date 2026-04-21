# Panduan Deploy E-Ticket ke Production (helpdesk.ckd-otto.com)

## Overview
```
[GitHub: mashudizaini/eticket]
          │
     git clone
          │
[Production Server: helpdesk.ckd-otto.com]
Ubuntu + Docker
          │
    ┌─────┴──────┐
PostgreSQL    Oracle EBS
(container)  172.21.2.201
          │
   Keycloak SSO
dashboard-dev.ckd-otto.com/auth
```

> **PENTING:** Lakukan semua langkah secara berurutan.
> Jangan skip langkah backup — production sedang aktif dipakai user.

---

## FASE 0 — Persiapan Keycloak (Lakukan Sekarang, Sebelum ke Server)

Login ke `http://dashboard-dev.ckd-otto.com/auth/admin` → realm `ckdo`

**Clients → ckdo-eticket → Settings:**

| Field | Tambahkan |
|---|---|
| Valid Redirect URIs | `http://helpdesk.ckd-otto.com/*` |
| Web Origins | `http://helpdesk.ckd-otto.com` |

Klik **Save**.

---

## FASE 1 — Backup Production (WAJIB Sebelum Deployment)

SSH ke server production:
```bash
ssh itdev@helpdesk.ckd-otto.com
```

### 1.1 Cek Setup Production Saat Ini

```bash
# Cek service yang berjalan
sudo systemctl list-units --type=service --state=running | grep -E "nginx|uvicorn|gunicorn|eticket|postgres"

# Cek port yang aktif
sudo ss -tlnp | grep -E "80|8000|5432"

# Cek lokasi aplikasi
ls -la /home/ /var/www/ /opt/ 2>/dev/null | head -30

# Cek PostgreSQL database yang ada
sudo -u postgres psql -c "\l" 2>/dev/null || psql -U postgres -c "\l" 2>/dev/null
```

### 1.2 Backup Database PostgreSQL

```bash
# Buat folder backup dengan timestamp
BACKUP_DIR="/home/itdev/backup_$(date +%Y%m%d_%H%M%S)"
mkdir -p $BACKUP_DIR

# Dump database (sesuaikan nama DB jika berbeda dari 'eticket')
sudo -u postgres pg_dump eticket > $BACKUP_DIR/eticket_db.sql
# ATAU jika pakai user/password:
# pg_dump -U postgres -h localhost eticket > $BACKUP_DIR/eticket_db.sql

echo "✅ Database backup: $BACKUP_DIR/eticket_db.sql"
ls -lh $BACKUP_DIR/eticket_db.sql
```

### 1.3 Backup File Upload

```bash
# Cari folder uploads (sesuaikan path jika berbeda)
# Kemungkinan di: /var/www/eticket/uploads, /opt/eticket/uploads, dll
find / -name "uploads" -type d 2>/dev/null | grep -v node_modules | grep -v proc

# Backup uploads (ganti PATH_UPLOADS dengan path yang ditemukan)
tar -czf $BACKUP_DIR/uploads.tar.gz PATH_UPLOADS/
echo "✅ Uploads backup: $BACKUP_DIR/uploads.tar.gz"
```

### 1.4 Backup Konfigurasi Nginx

```bash
sudo cp -r /etc/nginx/sites-enabled/ $BACKUP_DIR/nginx_sites/
sudo cp -r /etc/nginx/conf.d/ $BACKUP_DIR/nginx_conf/
echo "✅ Nginx config backup selesai"
```

### 1.5 Verifikasi Backup

```bash
ls -lh $BACKUP_DIR/
# Pastikan file .sql ada dan ukurannya masuk akal (bukan 0 bytes)
```

---

## FASE 2 — Install Docker di Production Server

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
sudo apt install -y ca-certificates curl gnupg lsb-release
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | \
  sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
  https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Izinkan itdev jalankan Docker tanpa sudo
sudo usermod -aG docker itdev

# PENTING: logout & login ulang
exit
```

SSH masuk lagi dan verifikasi:
```bash
ssh itdev@helpdesk.ckd-otto.com
docker --version
docker compose version
```

---

## FASE 3 — Stop Aplikasi Production Lama

> **Hati-hati:** Langkah ini akan membuat aplikasi tidak bisa diakses sementara.
> Lakukan di luar jam kerja atau saat maintenance window.

```bash
# Stop service lama (pilih yang sesuai)
sudo systemctl stop nginx
sudo systemctl stop uvicorn   # atau nama service yang ada
sudo systemctl stop gunicorn  # atau nama service yang ada

# Verifikasi port 80 sudah bebas
sudo ss -tlnp | grep :80
# Hasilnya harus kosong
```

---

## FASE 4 — Clone Repository & Konfigurasi

```bash
cd /home/itdev
git clone https://github.com/mashudizaini/eticket.git
cd eticket
```

### 4.1 Buat File `.env` Production

```bash
nano .env
```

Isi:
```env
# Oracle Database
ORACLE_PASSWORD=apps

# PostgreSQL
POSTGRES_PASSWORD=postgres_prod_2024

# JWT Secret (buat random string panjang)
SECRET_KEY=prod-secret-key-helpdesk-ckdotto-2024-change-this

# Keycloak SSO
KEYCLOAK_URL=http://dashboard-dev.ckd-otto.com/auth
KEYCLOAK_REALM=ckdo
KEYCLOAK_CLIENT_ID=ckdo-eticket

# Timezone
TZ=Asia/Jakarta
```

Simpan (`Ctrl+X` → `Y`) dan amankan:
```bash
chmod 600 .env
```

---

## FASE 5 — Migrasi Data dari Database Lama

> Skip fase ini jika production belum punya data (fresh install).

### 5.1 Jalankan Hanya Database Container Dulu

```bash
docker compose -f docker-compose.prod.yml up -d db
# Tunggu sampai healthy
docker compose -f docker-compose.prod.yml ps
```

### 5.2 Import Data Lama ke Docker PostgreSQL

```bash
# Copy backup ke dalam container
docker cp $BACKUP_DIR/eticket_db.sql eticket-db:/tmp/backup.sql

# Import ke PostgreSQL dalam container
docker exec -it eticket-db psql -U postgres -d eticket -f /tmp/backup.sql

echo "✅ Data berhasil diimport"

# Verifikasi data ada
docker exec -it eticket-db psql -U postgres -d eticket -c "SELECT COUNT(*) FROM tickets;"
```

### 5.3 Restore File Upload

```bash
# Copy uploads ke folder data Docker
mkdir -p /home/itdev/eticket/data/uploads
tar -xzf $BACKUP_DIR/uploads.tar.gz -C /tmp/uploads_restore/
cp -r /tmp/uploads_restore/* /home/itdev/eticket/data/uploads/
echo "✅ Uploads berhasil di-restore"
```

---

## FASE 6 — Deploy Aplikasi

```bash
cd /home/itdev/eticket

# Build dan jalankan semua container
docker compose -f docker-compose.prod.yml up -d --build

# Monitor proses startup
docker compose -f docker-compose.prod.yml logs -f
```

Tunggu sampai semua container healthy:
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

---

## FASE 7 — Konfigurasi Nginx Production

Jika server menggunakan domain `helpdesk.ckd-otto.com` (bukan akses langsung via IP):

```bash
sudo nano /etc/nginx/sites-available/helpdesk-eticket
```

Isi:
```nginx
server {
    listen 80;
    server_name helpdesk.ckd-otto.com;

    location / {
        proxy_pass http://127.0.0.1:80;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/helpdesk-eticket /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl start nginx
```

> **Catatan:** Jika Docker sudah expose port 80, Nginx tidak diperlukan.
> Cek apakah `http://helpdesk.ckd-otto.com` sudah bisa diakses langsung.

---

## FASE 8 — Verifikasi & Testing

```bash
# Test backend health
curl http://localhost:8000/health

# Test koneksi Oracle
curl http://localhost:8000/auth/test-oracle

# Test koneksi PostgreSQL
curl http://localhost:8000/auth/test-postgres
```

Buka browser ke `http://helpdesk.ckd-otto.com`:
- Harusnya redirect ke Keycloak login
- Login dengan akun yang sudah punya role `ticket-admin` / `ticket-agent` / `ticket-user`
- Masuk ke dashboard
- Cek data tiket lama masih ada

---

## FASE 9 — Update Untuk Production Berikutnya (Rutin)

Setelah initial deployment, update selanjutnya cukup:

```bash
cd /home/itdev/eticket
git pull origin main
docker compose -f docker-compose.prod.yml up -d --build
```

---

## Rollback Jika Gagal

Jika ada masalah serius dan perlu kembali ke versi lama:

```bash
# Stop Docker containers
docker compose -f docker-compose.prod.yml down

# Restore database dari backup
sudo systemctl start postgresql
sudo -u postgres psql -c "DROP DATABASE eticket;"
sudo -u postgres psql -c "CREATE DATABASE eticket;"
sudo -u postgres psql eticket < $BACKUP_DIR/eticket_db.sql

# Start service lama
sudo systemctl start nginx
sudo systemctl start uvicorn  # atau service lama yang sesuai

echo "✅ Rollback selesai"
```

---

## Checklist Deployment

```
FASE 0 - Keycloak
  □ Tambah http://helpdesk.ckd-otto.com/* ke Valid Redirect URIs
  □ Tambah http://helpdesk.ckd-otto.com ke Web Origins

FASE 1 - Backup
  □ Database ter-backup (cek ukuran file .sql > 0)
  □ Uploads ter-backup
  □ Nginx config ter-backup
  □ Catat $BACKUP_DIR path untuk rollback

FASE 2 - Docker
  □ Docker terinstall
  □ User itdev di group docker

FASE 3 - Stop Lama
  □ Service lama berhenti
  □ Port 80 bebas

FASE 4 - Deploy
  □ Repo ter-clone
  □ .env terkonfigurasi (chmod 600)

FASE 5 - Migrasi Data
  □ Data tiket lama ter-import
  □ Uploads ter-restore
  □ Jumlah tiket verified

FASE 6 - Aplikasi Jalan
  □ Semua container Up
  □ /health endpoint OK
  □ Oracle connection OK

FASE 7 - Testing
  □ Login via Keycloak berhasil
  □ Data tiket lama tampil
  □ Buat tiket baru berhasil
```

---

## Catatan Penting

| Hal | Keterangan |
|---|---|
| Downtime | ~15-30 menit saat switch dari app lama ke Docker |
| Waktu deploy | Lakukan di luar jam kerja (malam/weekend) |
| Backup | Simpan backup minimal 30 hari sebelum hapus |
| Rollback time | ~10 menit jika backup tersedia |
| User existing | Semua user Oracle EBS bisa login via Keycloak (auto-sync) |
