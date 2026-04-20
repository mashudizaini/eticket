from pydantic import BaseModel
from typing import Optional


class UserResponse(BaseModel):
    person_id: int
    username: Optional[str] = None
    employee_number: Optional[str] = None
    full_name: Optional[str] = None
    jabatan: Optional[str] = None
    divisi: Optional[str] = None
    department: Optional[str] = None
    team: Optional[str] = None

    @property
    def id(self):
        return self.person_id

    @property
    def role(self):
        return self.team or "USER"

    class Config:
        from_attributes = True


class UserLogin(BaseModel):
    username: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse
