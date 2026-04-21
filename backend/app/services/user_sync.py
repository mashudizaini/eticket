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
    """Ambil data karyawan dari Oracle VUSER_TICKET berdasarkan username."""
    try:
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
            {"username": username.upper().strip()},
        ).fetchone()

        if result:
            return {
                "person_id":       result[0],
                "employee_number": result[1],
                "full_name":       result[2],
                "jabatan":         result[3],
                "divisi":          result[4],
                "department":      result[5],
                "team":            result[6],
            }
    except Exception as e:
        print(f"[WARN] Oracle lookup gagal untuk {username}: {e}")

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
    user = pg_db.query(UserLocal).filter(
        UserLocal.keycloak_id == kc_user.id
    ).first()

    new_role = _map_role(kc_user.roles)

    if user is None:
        # User baru — ambil data Oracle
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
        print(f"[SSO] User baru dibuat: {kc_user.username} (person_id={user.person_id})")
    else:
        # Update role jika berubah di Keycloak
        if user.role != new_role:
            user.role = new_role
            pg_db.commit()

    return user
