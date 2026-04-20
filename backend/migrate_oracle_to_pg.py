"""
Migration Script: Oracle (TICKETO, TICKET_ATT, TICKET_HISTORY) -> PostgreSQL
Run from backend directory: python migrate_oracle_to_pg.py

This script migrates all existing ticket data from Oracle to PostgreSQL.
It should be run ONCE before switching to the new application.
"""

import os
import sys
from datetime import datetime
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Load .env
from dotenv import load_dotenv
load_dotenv()

# =====================================================
# CONFIGURATION
# =====================================================

# PostgreSQL
PG_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/eticket")

# Oracle
ORA_HOST = os.getenv("ORACLE_HOST", "172.21.2.201")
ORA_PORT = os.getenv("ORACLE_PORT", "1521")
ORA_SERVICE = os.getenv("ORACLE_SERVICE", "PROD")
ORA_USER = os.getenv("ORACLE_USER", "apps")
ORA_PASS = os.getenv("ORACLE_PASSWORD", "")
ORA_URL = f"oracle+oracledb://{ORA_USER}:{ORA_PASS}@{ORA_HOST}:{ORA_PORT}/?service_name={ORA_SERVICE}"

# =====================================================
# MAPPING TABLES
# =====================================================

# Oracle STATUS (number) -> PostgreSQL status (string)
STATUS_MAP = {
    1:  "new",
    20: "assigned",
    30: "in_progress",
    40: "in_progress",
    50: "in_progress",
    60: "in_progress",
    70: "in_progress",
    80: "in_progress",
    85: "resolved",
    90: "closed",
    -1: "cancelled",
    -2: "cancelled",
}

# Oracle DEPT_TO (number) -> PostgreSQL department (string)
DEPT_MAP = {
    1: "IT",
    2: "ENG",
}

# Oracle PRIORITY -> PostgreSQL priority (lowercase)
PRIORITY_MAP = {
    "LOW":      "low",
    "MEDIUM":   "medium",
    "HIGH":     "high",
    "URGENT":   "critical",
    "CRITICAL": "critical",
}

# Oracle KET (action) -> PostgreSQL action
ACTION_MAP = {
    "CREATE":   "CREATE",
    "UPDATE":   "UPDATE",
    "CANCEL":   "CANCEL",
    "ACCEPTED": "ACCEPTED",
    "DECLINED": "DECLINED",
}


def map_status(oracle_status):
    """Map Oracle numeric status to PostgreSQL string status"""
    if oracle_status is None:
        return "new"
    status = int(oracle_status)
    if status in STATUS_MAP:
        return STATUS_MAP[status]
    # Range fallback
    if 20 <= status <= 84:
        return "in_progress"
    if status < 0:
        return "cancelled"
    return "new"


def map_priority(oracle_priority):
    """Map Oracle priority string to PostgreSQL priority"""
    if not oracle_priority:
        return "medium"
    p = oracle_priority.strip().upper()
    return PRIORITY_MAP.get(p, "medium")


def map_department(dept_to):
    """Map Oracle DEPT_TO number to PostgreSQL department string"""
    if dept_to is None:
        return "IT"
    return DEPT_MAP.get(int(dept_to), "IT")


def get_file_extension(filename):
    """Extract file extension from filename"""
    if not filename:
        return None
    parts = filename.rsplit(".", 1)
    if len(parts) > 1:
        return parts[1].lower()
    return None


def migrate():
    """Main migration function"""
    print("=" * 60)
    print("  Oracle -> PostgreSQL Migration")
    print("=" * 60)

    # Initialize Oracle thick mode
    try:
        import oracledb
        import platform
        if platform.system() == "Windows":
            oracle_paths = [
                r"D:\app\client\Hardi\product\19.0.0\client_1",
                r"C:\oracle\instantclient_21_0",
                r"C:\oracle\instantclient_19_0",
            ]
            for path in oracle_paths:
                if os.path.exists(path):
                    try:
                        oracledb.init_oracle_client(lib_dir=path)
                        print(f"  Oracle Thick Mode: {path}")
                        break
                    except:
                        continue
        else:
            oracle_paths = [
                "/opt/oracle/instantclient_21_14",
                "/opt/oracle/instantclient_21_0",
                "/opt/oracle/instantclient_19_0",
            ]
            for path in oracle_paths:
                if os.path.exists(path):
                    try:
                        oracledb.init_oracle_client(lib_dir=path)
                        print(f"  Oracle Thick Mode: {path}")
                        break
                    except:
                        continue
    except Exception as e:
        print(f"  Warning: Oracle thick mode: {e}")

    # Connect to databases
    print("\n[1/5] Connecting to databases...")
    try:
        ora_engine = create_engine(ORA_URL)
        OraSession = sessionmaker(bind=ora_engine)
        ora_db = OraSession()
        # Test connection
        ora_db.execute(text("SELECT 1 FROM DUAL"))
        print("  Oracle    : Connected")
    except Exception as e:
        print(f"  Oracle    : FAILED - {e}")
        sys.exit(1)

    try:
        pg_engine = create_engine(PG_URL)
        PgSession = sessionmaker(bind=pg_engine)
        pg_db = PgSession()
        # Test connection
        pg_db.execute(text("SELECT 1"))
        print("  PostgreSQL: Connected")
    except Exception as e:
        print(f"  PostgreSQL: FAILED - {e}")
        sys.exit(1)

    # =====================================================
    # STEP 2: Count records in Oracle
    # =====================================================
    print("\n[2/5] Counting Oracle records...")
    ticket_count = ora_db.execute(text("SELECT COUNT(*) FROM TICKETO")).scalar()
    att_count = ora_db.execute(text("SELECT COUNT(*) FROM TICKET_ATT")).scalar()
    hist_count = ora_db.execute(text("SELECT COUNT(*) FROM TICKET_HISTORY")).scalar()
    print(f"  TICKETO        : {ticket_count} rows")
    print(f"  TICKET_ATT     : {att_count} rows")
    print(f"  TICKET_HISTORY : {hist_count} rows")

    if ticket_count == 0:
        print("\n  No data to migrate. Exiting.")
        return

    # =====================================================
    # STEP 3: Migrate TICKETO -> tickets
    # =====================================================
    print(f"\n[3/5] Migrating TICKETO -> tickets ({ticket_count} rows)...")

    # Read all tickets from Oracle
    oracle_tickets = ora_db.execute(text("""
        SELECT TICKETID, DEPT_TO, DEPT_REQ, SUBJECT_NAME, DESCRIPTOR,
               STATUS, DATECREATED, OPE, PIC, PIC_DATE,
               FINAL_DATE, CANCEL_DATE, PRIORITY
        FROM TICKETO
        ORDER BY DATECREATED
    """)).fetchall()

    # Track TICKETID -> PostgreSQL id mapping
    ticket_id_map = {}
    migrated = 0
    skipped = 0

    for row in oracle_tickets:
        oracle_ticketid = row[0].strip() if row[0] else None
        if not oracle_ticketid:
            skipped += 1
            continue

        # Check if already migrated (by ticket_id)
        existing = pg_db.execute(
            text("SELECT id FROM tickets WHERE ticket_id = :tid"),
            {"tid": oracle_ticketid}
        ).fetchone()

        if existing:
            ticket_id_map[oracle_ticketid] = existing[0]
            skipped += 1
            continue

        dept_to = row[1]
        dept_req = row[2].strip() if row[2] else None
        subject = row[3].strip() if row[3] else "No Subject"
        descriptor = row[4].strip() if row[4] else None
        status = row[5]
        datecreated = row[6]
        ope = row[7].strip() if row[7] else None
        pic = row[8].strip() if row[8] else None
        pic_date = row[9]
        final_date = row[10]
        cancel_date = row[11]
        priority = row[12].strip() if row[12] else None

        pg_status = map_status(status)
        pg_dept = map_department(dept_to)
        pg_priority = map_priority(priority)

        # Determine resolution_status
        resolution_status = None
        if pg_status == "resolved":
            resolution_status = "accepted"
        elif pg_status == "closed":
            resolution_status = "accepted"

        # Determine closed_at
        closed_at = None
        if pg_status in ("resolved", "closed") and final_date:
            closed_at = final_date
        elif pg_status == "cancelled" and cancel_date:
            closed_at = cancel_date

        # Insert into PostgreSQL
        result = pg_db.execute(
            text("""
                INSERT INTO tickets (
                    ticket_id, title, description, department, category,
                    priority, status, requester_id, requester_name,
                    pic_id, pic_name, pic_assigned_at,
                    resolution, resolution_status,
                    cancel_reason, cancelled_at,
                    created_at, updated_at, closed_at
                ) VALUES (
                    :ticket_id, :title, :description, :department, :category,
                    :priority, :status, :requester_id, :requester_name,
                    :pic_id, :pic_name, :pic_assigned_at,
                    :resolution, :resolution_status,
                    :cancel_reason, :cancelled_at,
                    :created_at, :updated_at, :closed_at
                ) RETURNING id
            """),
            {
                "ticket_id": oracle_ticketid,
                "title": subject,
                "description": descriptor,
                "department": pg_dept,
                "category": None,
                "priority": pg_priority,
                "status": pg_status,
                "requester_id": None,
                "requester_name": ope,
                "pic_id": None,
                "pic_name": pic,
                "pic_assigned_at": pic_date,
                "resolution": None,
                "resolution_status": resolution_status,
                "cancel_reason": None,
                "cancelled_at": cancel_date,
                "created_at": datecreated,
                "updated_at": datecreated,
                "closed_at": closed_at,
            }
        )
        pg_id = result.fetchone()[0]
        ticket_id_map[oracle_ticketid] = pg_id
        migrated += 1

        if migrated % 50 == 0:
            print(f"    ... {migrated}/{ticket_count} tickets migrated")

    pg_db.commit()
    print(f"  Done: {migrated} migrated, {skipped} skipped (already exists)")

    # =====================================================
    # STEP 4: Migrate TICKET_ATT -> ticket_attachments
    # =====================================================
    print(f"\n[4/5] Migrating TICKET_ATT -> ticket_attachments ({att_count} rows)...")

    oracle_atts = ora_db.execute(text("""
        SELECT IDE, TICKETID,
               ATT1, ATT1_FILENAME,
               ATT2, ATT2_FILENAME,
               ATT3, ATT3_FILENAME,
               ATT4, ATT4_FILENAME,
               ATT5, ATT5_FILENAME
        FROM TICKET_ATT
        ORDER BY IDE
    """)).fetchall()

    att_migrated = 0
    att_skipped = 0

    for row in oracle_atts:
        oracle_ticketid = row[1].strip() if row[1] else None
        if not oracle_ticketid:
            att_skipped += 1
            continue

        pg_ticket_id = ticket_id_map.get(oracle_ticketid)
        if not pg_ticket_id:
            att_skipped += 1
            continue

        # Process each ATT slot (1-5)
        for i in range(5):
            att_idx = 2 + (i * 2)       # ATT column index
            fname_idx = 3 + (i * 2)     # FILENAME column index

            att_value = row[att_idx].strip() if row[att_idx] and str(row[att_idx]).strip() else None
            att_filename = row[fname_idx].strip() if row[fname_idx] and str(row[fname_idx]).strip() else None

            if not att_filename:
                continue

            file_num = i + 1
            file_ext = get_file_extension(att_filename)

            # Old file path: assets/att_file/FILE{n}/filename
            old_path = f"assets/att_file/FILE{file_num}/{att_filename}"

            # Check if already exists
            existing = pg_db.execute(
                text("""SELECT id FROM ticket_attachments
                       WHERE ticket_id = :tid AND file_name = :fname"""),
                {"tid": pg_ticket_id, "fname": att_filename}
            ).fetchone()

            if existing:
                continue

            pg_db.execute(
                text("""
                    INSERT INTO ticket_attachments (
                        ticket_id, file_name, file_path, file_type, file_size, created_at
                    ) VALUES (
                        :ticket_id, :file_name, :file_path, :file_type, :file_size, :created_at
                    )
                """),
                {
                    "ticket_id": pg_ticket_id,
                    "file_name": att_filename,
                    "file_path": old_path,
                    "file_type": file_ext,
                    "file_size": 0,
                    "created_at": datetime.now(),
                }
            )
            att_migrated += 1

    pg_db.commit()
    print(f"  Done: {att_migrated} attachments migrated, {att_skipped} skipped")

    # =====================================================
    # STEP 5: Migrate TICKET_HISTORY -> ticket_history
    # =====================================================
    print(f"\n[5/5] Migrating TICKET_HISTORY -> ticket_history ({hist_count} rows)...")

    oracle_hist = ora_db.execute(text("""
        SELECT IDE, TICKETID, DESCRIPTION, PIC, KET, STATUS, SUBJECT, HISTORY_DATE
        FROM TICKET_HISTORY
        ORDER BY IDE
    """)).fetchall()

    hist_migrated = 0
    hist_skipped = 0

    for row in oracle_hist:
        oracle_ticketid = row[1].strip() if row[1] else None
        if not oracle_ticketid:
            hist_skipped += 1
            continue

        pg_ticket_id = ticket_id_map.get(oracle_ticketid)
        if not pg_ticket_id:
            hist_skipped += 1
            continue

        description = row[2].strip() if row[2] else None
        pic = row[3].strip() if row[3] else None
        ket = row[4].strip() if row[4] else "UPDATE"
        status = row[5]
        subject = row[6].strip() if row[6] else None
        history_date = row[7]

        pg_action = ACTION_MAP.get(ket, ket)
        pg_new_status = map_status(status)

        # Build description
        hist_desc = description or subject or f"Action: {pg_action}"

        pg_db.execute(
            text("""
                INSERT INTO ticket_history (
                    ticket_id, action, description,
                    old_status, new_status,
                    actor_id, actor_name, created_at
                ) VALUES (
                    :ticket_id, :action, :description,
                    :old_status, :new_status,
                    :actor_id, :actor_name, :created_at
                )
            """),
            {
                "ticket_id": pg_ticket_id,
                "action": pg_action,
                "description": hist_desc,
                "old_status": None,
                "new_status": pg_new_status,
                "actor_id": None,
                "actor_name": pic,
                "created_at": history_date or datetime.now(),
            }
        )
        hist_migrated += 1

        if hist_migrated % 100 == 0:
            print(f"    ... {hist_migrated}/{hist_count} history migrated")

    pg_db.commit()
    print(f"  Done: {hist_migrated} history migrated, {hist_skipped} skipped")

    # =====================================================
    # SUMMARY
    # =====================================================
    print("\n" + "=" * 60)
    print("  MIGRATION SUMMARY")
    print("=" * 60)
    print(f"  Tickets      : {migrated} migrated, {skipped} skipped")
    print(f"  Attachments  : {att_migrated} migrated, {att_skipped} skipped")
    print(f"  History      : {hist_migrated} migrated, {hist_skipped} skipped")
    print("=" * 60)

    # Verify
    pg_total = pg_db.execute(text("SELECT COUNT(*) FROM tickets")).scalar()
    pg_att_total = pg_db.execute(text("SELECT COUNT(*) FROM ticket_attachments")).scalar()
    pg_hist_total = pg_db.execute(text("SELECT COUNT(*) FROM ticket_history")).scalar()
    print(f"\n  PostgreSQL totals:")
    print(f"    tickets            : {pg_total}")
    print(f"    ticket_attachments : {pg_att_total}")
    print(f"    ticket_history     : {pg_hist_total}")

    # Close connections
    ora_db.close()
    pg_db.close()
    print("\n  Migration complete!")


if __name__ == "__main__":
    # Confirm before running
    print("\nThis will migrate data from Oracle to PostgreSQL.")
    print("Make sure PostgreSQL tables are created (01-schema.sql).")
    confirm = input("\nProceed? (yes/no): ").strip().lower()
    if confirm == "yes":
        migrate()
    else:
        print("Migration cancelled.")
