from sqlalchemy import Column, Integer, String, Boolean, DateTime
from datetime import datetime
from app.database import PostgresBase


class UserLocal(PostgresBase):
    """User lokal PostgreSQL — mapping antara Keycloak identity dan data Oracle EBS."""
    __tablename__ = "users"

    id              = Column(Integer, primary_key=True, autoincrement=True)
    keycloak_id     = Column(String(255), unique=True, index=True)
    username        = Column(String(100), unique=True)
    email           = Column(String(255))
    full_name       = Column(String(200))
    role            = Column(String(20), default="user")   # admin | agent | user
    is_active       = Column(Boolean, default=True)
    # Data Oracle EBS (di-sync saat first login)
    person_id       = Column(Integer)
    employee_number = Column(String(50))
    jabatan         = Column(String(100))
    divisi          = Column(String(100))
    department      = Column(String(50))
    team            = Column(String(50))
    created_at      = Column(DateTime, default=datetime.utcnow)
    updated_at      = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
