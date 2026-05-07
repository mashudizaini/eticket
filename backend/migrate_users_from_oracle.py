#!/usr/bin/env python3
"""
Migration script: Pre-populate PostgreSQL users table dari Oracle VUSER_TICKET
Tujuan: Avoid slow Oracle lookup on first login untuk setiap user baru
"""
import sys
from sqlalchemy import text
from sqlalchemy.orm import Session

sys.path.insert(0, '/app')

from app.database import SessionLocal, get_oracle_db
from app.models.user_local import UserLocal
from app.config import get_settings

settings = get_settings()

def migrate_users():
    """Query semua user dari Oracle, insert ke PostgreSQL"""

    pg_db = SessionLocal()
    oracle_db = get_oracle_db().__next__()

    try:
        print("[MIGRATE] Starting user migration from Oracle to PostgreSQL...")

        # Query semua user dari Oracle
        result = oracle_db.execute(
            text("""
                SELECT PERSON_ID,
                       TRIM(EMPLOYEE_NUMBER) AS EMPLOYEE_NUMBER,
                       UPPER(TRIM(USER_NAME)) AS USER_NAME,
                       TRIM(LOCAL_NAME) AS LOCAL_NAME,
                       LOWER(TRIM(EMAIL_ADDRESS)) AS EMAIL_ADDRESS,
                       TRIM(JABATAN) AS JABATAN,
                       TRIM(DIVISI) AS DIVISI,
                       UPPER(TRIM(DEPT)) AS DEPT,
                       TRIM(TEAM) AS TEAM
                FROM VUSER_TICKET
                WHERE PERSON_ID IS NOT NULL
                  AND EMAIL_ADDRESS IS NOT NULL
                ORDER BY EMPLOYEE_NUMBER
            """)
        ).fetchall()

        print(f"[MIGRATE] Found {len(result)} users in Oracle VUSER_TICKET")

        # Insert or update each user in PostgreSQL
        inserted = 0
        updated = 0
        skipped = 0

        for row in result:
            person_id, emp_num, user_name, local_name, email, jabatan, divisi, dept, team = row

            # Skip jika email sudah ada di PostgreSQL
            existing = pg_db.query(UserLocal).filter(
                UserLocal.email == email
            ).first()

            if existing:
                # Update user yang sudah ada jika data kosong
                changed = False
                if not existing.employee_number and emp_num:
                    existing.employee_number = emp_num
                    changed = True
                if not existing.full_name and local_name:
                    existing.full_name = local_name
                    changed = True
                if not existing.team and team:
                    existing.team = team
                    changed = True
                if not existing.person_id and person_id:
                    existing.person_id = person_id
                    changed = True
                if not existing.department and dept:
                    existing.department = dept
                    changed = True
                if not existing.jabatan and jabatan:
                    existing.jabatan = jabatan
                    changed = True
                if not existing.divisi and divisi:
                    existing.divisi = divisi
                    changed = True

                if changed:
                    pg_db.commit()
                    updated += 1
                else:
                    skipped += 1
            else:
                # Create new user
                new_user = UserLocal(
                    username=email,  # Use email as username (consistent dengan Keycloak)
                    email=email,
                    full_name=local_name or user_name or email,
                    employee_number=emp_num,
                    person_id=person_id,
                    jabatan=jabatan,
                    divisi=divisi,
                    department=dept,
                    team=team or "USER",  # Default to USER jika team kosong
                )
                pg_db.add(new_user)
                pg_db.commit()
                inserted += 1

        print(f"\n[MIGRATE] Migration complete!")
        print(f"  - Inserted: {inserted}")
        print(f"  - Updated: {updated}")
        print(f"  - Skipped: {skipped}")
        print(f"  - Total in PostgreSQL: {pg_db.query(UserLocal).count()}")

        # Show summary by team
        print(f"\n[MIGRATE] Users by team:")
        team_summary = pg_db.execute(
            text("SELECT team, COUNT(*) FROM users GROUP BY team ORDER BY COUNT(*) DESC")
        ).fetchall()
        for team, count in team_summary:
            print(f"  - {team or 'NULL'}: {count}")

    except Exception as e:
        print(f"[MIGRATE] ERROR: {e}")
        import traceback
        traceback.print_exc()
    finally:
        pg_db.close()
        oracle_db.close()

if __name__ == "__main__":
    migrate_users()
