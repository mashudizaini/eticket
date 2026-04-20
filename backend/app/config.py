from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # PostgreSQL Database (for transactions)
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/eticket"

    # Oracle Database (for user validation)
    ORACLE_HOST: str = "172.21.2.201"
    ORACLE_PORT: int = 1521
    ORACLE_SERVICE: str = "PROD"
    ORACLE_USER: str = "apps"
    ORACLE_PASSWORD: str = ""  # Set in .env

    # JWT
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # App
    APP_NAME: str = "E-Ticket API"
    DEBUG: bool = True

    # File Upload
    UPLOAD_DIR: str = "uploads"
    MAX_FILE_SIZE: int = 2 * 1024 * 1024  # 2MB
    ALLOWED_EXTENSIONS: list = ["jpg", "jpeg", "png", "pdf", "doc", "docx", "xls", "xlsx"]

    @property
    def ORACLE_URL(self) -> str:
        """Oracle connection URL for user validation"""
        return f"oracle+oracledb://{self.ORACLE_USER}:{self.ORACLE_PASSWORD}@{self.ORACLE_HOST}:{self.ORACLE_PORT}/?service_name={self.ORACLE_SERVICE}"

    class Config:
        env_file = ".env"


@lru_cache()
def get_settings():
    return Settings()
