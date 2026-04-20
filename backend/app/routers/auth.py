from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime, timedelta
import jwt

from app.database import get_db, get_oracle_db
from app.config import get_settings
from app.schemas.user import UserLogin, Token, UserResponse

router = APIRouter(prefix="/auth", tags=["Authentication"])
settings = get_settings()


def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


@router.post("/login", response_model=Token)
def login(credentials: UserLogin, db: Session = Depends(get_oracle_db)):
    username = credentials.username.upper().strip()
    password = credentials.password.strip()

    print(f"[DEBUG] Login attempt: username={username}")

    try:
        # Query VUSER_TICKET view for authentication
        query = text("""
            SELECT PERSON_ID, UPPER(TRIM(USER_NAME)) AS USER_NAME,
                   DECRYPTED_USER_PASSWORD AS PASSWORD,
                   TRIM(EMPLOYEE_NUMBER) AS EMPLOYEE_NUMBER,
                   TRIM(LOCAL_NAME) AS LOCAL_NAME,
                   TRIM(JABATAN) AS JABATAN,
                   TRIM(DIVISI) AS DIVISI,
                   UPPER(TRIM(DEPT)) AS DEPT,
                   TRIM(TEAM) AS TEAM
            FROM VUSER_TICKET
            WHERE PERSON_ID IS NOT NULL
              AND UPPER(TRIM(USER_NAME)) = :username
              AND TRIM(DECRYPTED_USER_PASSWORD) = :password
        """)

        result = db.execute(query, {"username": username, "password": password}).fetchone()
        print(f"[DEBUG] Query result: {result}")

    except Exception as e:
        print(f"[ERROR] Database error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}",
        )

    if not result:
        print(f"[DEBUG] No user found for username={username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    user_data = UserResponse(
        person_id=result[0],
        username=result[1],
        employee_number=result[3],
        full_name=result[4],
        jabatan=result[5],
        divisi=result[6],
        department=result[7],
        team=result[8],
    )

    access_token = create_access_token(data={
        "sub": str(result[0]),  # person_id
        "username": result[1],
        "employee_number": result[3],
        "team": result[8],
    })

    print(f"[DEBUG] Login success for {username}")

    return Token(
        access_token=access_token,
        token_type="bearer",
        user=user_data,
    )


@router.get("/test-oracle")
def test_oracle(db: Session = Depends(get_oracle_db)):
    """Test Oracle database connection"""
    try:
        result = db.execute(text("SELECT 1 FROM DUAL")).fetchone()
        return {"status": "ok", "database": "oracle", "result": result[0]}
    except Exception as e:
        return {"status": "error", "database": "oracle", "message": str(e)}


@router.get("/test-postgres")
def test_postgres(db: Session = Depends(get_db)):
    """Test PostgreSQL database connection"""
    try:
        result = db.execute(text("SELECT 1")).fetchone()
        return {"status": "ok", "database": "postgresql", "result": result[0]}
    except Exception as e:
        return {"status": "error", "database": "postgresql", "message": str(e)}
