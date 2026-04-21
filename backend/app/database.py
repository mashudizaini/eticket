from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import oracledb
import os
import platform

from app.config import get_settings

# Base untuk model Oracle (tidak di-create via SQLAlchemy — hanya referensi view)
# Base untuk model PostgreSQL (di-create otomatis saat startup)
PostgresBase = declarative_base()

settings = get_settings()

# Initialize Oracle Thick Mode for Oracle EBS compatibility
try:
    if platform.system() == 'Windows':
        # Check common Oracle client paths on Windows
        oracle_paths = [
            r"D:\app\client\Hardi\product\19.0.0\client_1",
            r"C:\oracle\instantclient_21_0",
            r"C:\oracle\instantclient_19_0",
            r"C:\app\USEP\product\11.2.0\client_1\BIN",
            r"C:\app\USEP\product\11.2.0\client_1",
            r"C:\oracle\product\11.2.0\client_1\BIN",
            r"C:\oracle\product\11.2.0\client_1",
        ]

        for path in oracle_paths:
            if os.path.exists(path):
                try:
                    oracledb.init_oracle_client(lib_dir=path)
                    print(f"✅ Oracle Thick Mode initialized: {path}")
                    break
                except Exception as e:
                    continue
    else:
        # Linux (Docker container)
        # Oracle Instant Client is installed at /opt/oracle/instantclient_21_14
        oracle_linux_paths = [
            "/opt/oracle/instantclient_21_14",
            "/opt/oracle/instantclient_21_0",
            "/opt/oracle/instantclient_19_0",
            "/usr/lib/oracle/21/client64/lib",
            "/usr/lib/oracle/19/client64/lib",
        ]

        initialized = False
        for path in oracle_linux_paths:
            if os.path.exists(path):
                try:
                    oracledb.init_oracle_client(lib_dir=path)
                    print(f"✅ Oracle Thick Mode initialized: {path}")
                    initialized = True
                    break
                except Exception as e:
                    continue

        if not initialized:
            # Try without lib_dir (uses LD_LIBRARY_PATH)
            oracledb.init_oracle_client()
            print("✅ Oracle Thick Mode initialized (using LD_LIBRARY_PATH)")

except Exception as e:
    print(f"⚠️  Oracle Thick Mode not available: {e}")
    print("   Continuing in thin mode (may have issues with old Oracle password verifiers)")

# ============================================
# PostgreSQL Database (for transactions)
# ============================================
engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """Get PostgreSQL database session for transactions"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ============================================
# Oracle Database (for user validation)
# ============================================
oracle_engine = create_engine(settings.ORACLE_URL)
OracleSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=oracle_engine)


def get_oracle_db():
    """Get Oracle database session for user validation"""
    db = OracleSessionLocal()
    try:
        yield db
    finally:
        db.close()
