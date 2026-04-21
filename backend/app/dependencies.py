from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from dataclasses import dataclass, field
from typing import Optional

from app.database import get_db, get_oracle_db
from app.auth.keycloak import verify_token
from app.services.user_sync import get_or_create_user

security = HTTPBearer()


@dataclass
class CurrentUser:
    """User data yang tersedia di setiap request setelah SSO auth."""
    person_id:       int
    username:        str
    employee_number: str
    team:            str
    role:            str = "user"
    full_name:       str = ""
    keycloak_id:     str = ""
    email:           str = ""

    @property
    def id(self):
        return self.person_id

    @property
    def ope(self):
        return self.employee_number

    def is_admin(self) -> bool:
        return self.role == "admin"

    def is_agent(self) -> bool:
        return self.role in ("admin", "agent")


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    pg_db: Session = Depends(get_db),
    oracle_db: Session = Depends(get_oracle_db),
) -> CurrentUser:
    """
    FastAPI dependency — verifikasi Keycloak JWT dan sync user lokal.

    Flow:
    1. Verifikasi token ke Keycloak JWKS (RS256)
    2. Lookup/create user di PostgreSQL (linked ke Oracle EBS data)
    3. Return CurrentUser dengan data lengkap
    """
    kc_user = verify_token(credentials.credentials)
    user = get_or_create_user(kc_user, pg_db, oracle_db)

    return CurrentUser(
        person_id       = user.person_id or 0,
        username        = user.username or kc_user.username,
        employee_number = user.employee_number or "",
        team            = user.team or "USER",
        role            = user.role or "user",
        full_name       = user.full_name or kc_user.name or kc_user.username,
        keycloak_id     = kc_user.id,
        email           = user.email or kc_user.email or "",
    )
