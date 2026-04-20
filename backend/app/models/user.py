from sqlalchemy import Column, Integer, String
from app.database import Base


class User(Base):
    """Mapping ke view VUSER_TICKET di Oracle"""
    __tablename__ = "VUSER_TICKET"

    person_id = Column("PERSON_ID", Integer, primary_key=True)
    username = Column("USER_NAME", String(100))
    password = Column("DECRYPTED_USER_PASSWORD", String(255))
    employee_number = Column("EMPLOYEE_NUMBER", String(50))
    full_name = Column("LOCAL_NAME", String(200))
    jabatan = Column("JABATAN", String(100))
    divisi = Column("DIVISI", String(100))
    department = Column("DEPT", String(50))
    team = Column("TEAM", String(50))

    @property
    def id(self):
        return self.person_id

    @property
    def role(self):
        return self.team or "USER"

    @property
    def is_active(self):
        return True
