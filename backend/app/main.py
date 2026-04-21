from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
import os

from app.config import get_settings
from app.database import engine, PostgresBase
from app.routers import auth, tickets, dashboard

settings = get_settings()

# Import model agar PostgresBase mengenali tabel yang perlu dibuat
import app.models.user_local  # noqa: F401

os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

app = FastAPI(
    title=settings.APP_NAME,
    description="E-Ticket Management System API",
    version="2.0.0",
)

# CORS — izinkan frontend E-Ticket dan Dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost",
        "http://localhost:80",
        "http://localhost:5173",
        "http://localhost:3000",
        "http://172.21.2.60",
        "http://172.21.2.60:80",
        "http://dashboard-dev.ckd-otto.com",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")

app.include_router(auth.router)
app.include_router(tickets.router)
app.include_router(dashboard.router)


@app.on_event("startup")
def startup():
    # Buat tabel PostgreSQL baru jika belum ada (idempotent)
    PostgresBase.metadata.create_all(bind=engine, checkfirst=True)

    # Migration: tambah kolom SSO ke tabel users yang sudah ada
    with engine.connect() as conn:
        migrations = [
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS keycloak_id VARCHAR(255) UNIQUE",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS employee_number VARCHAR(50)",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS jabatan VARCHAR(100)",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS divisi VARCHAR(100)",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS team VARCHAR(50)",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS person_id INTEGER",
            "ALTER TABLE users ALTER COLUMN password DROP NOT NULL",
            "ALTER TABLE users ALTER COLUMN full_name DROP NOT NULL",
            "CREATE INDEX IF NOT EXISTS ix_users_keycloak_id ON users(keycloak_id)",
        ]
        for sql in migrations:
            try:
                conn.execute(text(sql))
            except Exception:
                pass
        conn.commit()
    print("[Startup] Database migration selesai.")


@app.get("/")
def root():
    return {"message": "E-Ticket API", "version": "2.0.0"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}
