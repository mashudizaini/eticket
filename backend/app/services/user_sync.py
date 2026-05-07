"""
User sync service: mapping Keycloak identity → Oracle EBS data → PostgreSQL local user.

Flow saat user pertama kali login via SSO:
1. Cari di PostgreSQL berdasarkan keycloak_id
2. Jika tidak ada, query Oracle VUSER_TICKET dengan preferred_username
3. Buat user baru di PostgreSQL dengan data gabungan Keycloak + Oracle
4. Request berikutnya: langsung dari PostgreSQL (fast path)
"""

from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional

from app.auth.keycloak import KeycloakUser
from app.models.user_local import UserLocal


def _map_role(kc_roles: list) -> str:
    if "ticket-admin" in kc_roles:
        return "admin"
    if "ticket-agent" in kc_roles:
        return "agent"
    return "user"


def _query_oracle_user(oracle_db: Session, username: str) -> Optional[dict]:
    """Ambil data karyawan dari Oracle VUSER_TICKET berdasarkan username atau email."""
    print(f"\n[ORACLE_SYNC] Starting Oracle lookup for: '{username}'")
    try:
        # Try lookup by USER_NAME dulu
        search_username = username.upper().strip()
        print(f"[ORACLE_SYNC] Attempt 1: BY USER_NAME = '{search_username}'")

        result = oracle_db.execute(
            text("""
                SELECT PERSON_ID,
                       TRIM(EMPLOYEE_NUMBER) AS EMPLOYEE_NUMBER,
                       TRIM(LOCAL_NAME)      AS LOCAL_NAME,
                       TRIM(JABATAN)         AS JABATAN,
                       TRIM(DIVISI)          AS DIVISI,
                       UPPER(TRIM(DEPT))     AS DEPT,
                       TRIM(TEAM)            AS TEAM
                FROM VUSER_TICKET
                WHERE UPPER(TRIM(USER_NAME)) = :username
                  AND PERSON_ID IS NOT NULL
                  AND ROWNUM = 1
            """),
            {"username": search_username},
        ).fetchone()

        if result:
            print(f"[ORACLE_SYNC] ✅ SUCCESS by USER_NAME!")
            print(f"[ORACLE_SYNC]    PERSON_ID={result[0]}, EMPLOYEE={result[1]}, TEAM={result[6]}")
            return {
                "person_id":       result[0],
                "employee_number": result[1],
                "full_name":       result[2],
                "jabatan":         result[3],
                "divisi":          result[4],
                "department":      result[5],
                "team":            result[6],
            }

        # Jika tidak ketemu, coba lookup by email (untuk Keycloak dengan email sebagai preferred_username)
        if "@" in username:
            search_email = username.lower().strip()
            print(f"[ORACLE_SYNC] Attempt 2: BY EMAIL_ADDRESS = '{search_email}'")

            result = oracle_db.execute(
                text("""
                    SELECT PERSON_ID,
                           TRIM(EMPLOYEE_NUMBER) AS EMPLOYEE_NUMBER,
                           TRIM(LOCAL_NAME)      AS LOCAL_NAME,
                           TRIM(JABATAN)         AS JABATAN,
                           TRIM(DIVISI)          AS DIVISI,
                           UPPER(TRIM(DEPT))     AS DEPT,
                           TRIM(TEAM)            AS TEAM
                    FROM VUSER_TICKET
                    WHERE LOWER(TRIM(EMAIL_ADDRESS)) = :email
                      AND PERSON_ID IS NOT NULL
                      AND ROWNUM = 1
                """),
                {"email": search_email},
            ).fetchone()

            if result:
                print(f"[ORACLE_SYNC] ✅ SUCCESS by EMAIL_ADDRESS!")
                print(f"[ORACLE_SYNC]    PERSON_ID={result[0]}, EMPLOYEE={result[1]}, TEAM={result[6]}")
                return {
                    "person_id":       result[0],
                    "employee_number": result[1],
                    "full_name":       result[2],
                    "jabatan":         result[3],
                    "divisi":          result[4],
                    "department":      result[5],
                    "team":            result[6],
                }
            else:
                print(f"[ORACLE_SYNC] ❌ Email lookup FAILED - no match")
        else:
            print(f"[ORACLE_SYNC] ❌ No email (@) in username, skipping email lookup")

    except Exception as e:
        print(f"[ORACLE_SYNC] ❌ EXCEPTION: {e}")
        import traceback
        traceback.print_exc()

    print(f"[ORACLE_SYNC] Final result: NULL (lookup failed)\n")
    return None


def get_or_create_user(
    kc_user: KeycloakUser,
    pg_db: Session,
    oracle_db: Session,
) -> UserLocal:
    """
    Ambil atau buat UserLocal dari Keycloak + Oracle data.
    Dipanggil setiap request; fast path jika user sudah ada di PostgreSQL.
    """
    # Try lookup by keycloak_id first
    user = pg_db.query(UserLocal).filter(
        UserLocal.keycloak_id == kc_user.id
    ).first()

    # Fallback: jika tidak ketemu by keycloak_id, cari by username
    # (untuk handle user yang sudah ada tapi belum ter-link ke keycloak_id)
    if not user:
        user = pg_db.query(UserLocal).filter(
            UserLocal.username == kc_user.username
        ).first()

    new_role = _map_role(kc_user.roles)

    if user is None:
        # User baru — ambil data Oracle
        print(f"[SSO] Creating new user: {kc_user.username}")
        oracle_data = _query_oracle_user(oracle_db, kc_user.username) or {}

        user = UserLocal(
            keycloak_id     = kc_user.id,
            username        = kc_user.username,
            email           = kc_user.email,
            full_name       = oracle_data.get("full_name") or kc_user.name or kc_user.username,
            role            = new_role,
            person_id       = oracle_data.get("person_id"),
            employee_number = oracle_data.get("employee_number"),
            jabatan         = oracle_data.get("jabatan"),
            divisi          = oracle_data.get("divisi"),
            department      = oracle_data.get("department"),
            team            = oracle_data.get("team"),
        )
        pg_db.add(user)
        pg_db.commit()
        pg_db.refresh(user)
        print(f"[SSO] User baru dibuat: {kc_user.username} (employee_number={user.employee_number}, team={user.team})")
    else:
        # User sudah ada, update role & Oracle data jika masih kosong
        updated = False

        # Link keycloak_id jika masih kosong (user yang dibuat sebelumnya)
        if not user.keycloak_id:
            user.keycloak_id = kc_user.id
            print(f"[SSO] Linked keycloak_id for existing user: {kc_user.username}")
            updated = True

        if user.role != new_role:
            user.role = new_role
            updated = True

        # Jika employee_number masih kosong, coba fetch dari Oracle lagi
        if not user.employee_number:
            print(f"[SSO] User {kc_user.username} exists but employee_number is empty, trying Oracle lookup again")
            oracle_data = _query_oracle_user(oracle_db, kc_user.username) or {}
            if oracle_data:
                user.person_id = oracle_data.get("person_id")
                user.employee_number = oracle_data.get("employee_number")
                user.jabatan = oracle_data.get("jabatan")
                user.divisi = oracle_data.get("divisi")
                user.department = oracle_data.get("department")
                user.team = oracle_data.get("team")
                print(f"[SSO] Successfully synced Oracle data for {kc_user.username} (employee_number={user.employee_number}, team={user.team})")
                updated = True

        if updated:
            pg_db.commit()
            pg_db.refresh(user)

    return user
