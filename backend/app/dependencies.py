from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
import jwt
from jwt.exceptions import PyJWTError
from dataclasses import dataclass
from typing import Optional

from app.database import get_db
from app.config import get_settings

security = HTTPBearer()
settings = get_settings()


@dataclass
class CurrentUser:
    """User data from JWT token"""
    person_id: int
    username: str
    employee_number: str
    team: str

    @property
    def id(self):
        return self.person_id

    @property
    def role(self):
        return self.team or "USER"

    @property
    def ope(self):
        return self.employee_number


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> CurrentUser:
    token = credentials.credentials
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        person_id = payload.get("sub")
        username = payload.get("username")
        employee_number = payload.get("employee_number")
        team = payload.get("team")

        if person_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
            )

        return CurrentUser(
            person_id=int(person_id),
            username=username,
            employee_number=employee_number,
            team=team or "USER",
        )

    except PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )
