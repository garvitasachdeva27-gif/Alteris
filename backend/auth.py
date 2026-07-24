import os
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext
from jose import JWTError, jwt
from dotenv import load_dotenv

from database import get_db_connection
from models import UserCreate, UserLogin, Token, UserOut

load_dotenv()

router = APIRouter()

# ---------- Configuration ----------
SECRET_KEY = os.getenv("JWT_SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours

if not SECRET_KEY:
    raise RuntimeError(
        "JWT_SECRET_KEY is not set. Add it to backend/.env before starting the server."
    )

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


# ---------- Helper functions ----------

def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(token: str = Depends(oauth2_scheme)) -> UserOut:
    """
    Dependency that any protected route can use.
    FastAPI will run this first, extract the token from the
    Authorization header, and inject the resulting user object.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: int = payload.get("user_id")
        email: str = payload.get("sub")
        if user_id is None or email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    return UserOut(id=user_id, email=email)


# ---------- Routes ----------

@router.post("/signup", response_model=Token)
def signup(user: UserCreate):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE email = ?", (user.email,))
        if cursor.fetchone():
            raise HTTPException(status_code=400, detail="Email already registered")

        hashed = hash_password(user.password)
        cursor.execute(
            "INSERT INTO users (email, password_hash) VALUES (?, ?)",
            (user.email, hashed),
        )
        conn.commit()
        new_user_id = cursor.lastrowid

    access_token = create_access_token({"sub": user.email, "user_id": new_user_id})
    return Token(access_token=access_token)


@router.post("/login", response_model=Token)
def login(credentials: UserLogin):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email = ?", (credentials.email,))
        row = cursor.fetchone()

    if not row or not verify_password(credentials.password, row["password_hash"]):
        raise HTTPException(status_code=401, detail="Incorrect email or password")

    access_token = create_access_token({"sub": row["email"], "user_id": row["id"]})
    return Token(access_token=access_token)
