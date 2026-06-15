"""
SQLite-backed user store, replacing the hardcoded `fake_users` dict.

Requires: sqlalchemy, passlib[bcrypt]
"""
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import declarative_base, sessionmaker
from passlib.context import CryptContext

DB_URL = "sqlite:///users.db"
engine = create_engine(DB_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(String, nullable=False)  # "intern" | "manager" | "admin"


def init_users_db():
    Base.metadata.create_all(bind=engine)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def get_user(username: str) -> User | None:
    with SessionLocal() as db:
        return db.query(User).filter(User.username == username).first()


def create_user(username: str, password: str, role: str) -> User:
    with SessionLocal() as db:
        user = User(username=username, hashed_password=hash_password(password), role=role)
        db.add(user)
        db.commit()
        db.refresh(user)
        return user
    


def create_default_users():
    """Seed default intern/manager/admin accounts if the table is empty."""
    with SessionLocal() as db:
        if db.query(User).count() > 0:
            return

    create_user("intern", "intern123", "intern")
    create_user("manager", "manager123", "manager")
    create_user("admin", "admin123", "admin")
    
def update_user_role(username: str, new_role: str) -> bool:
    with SessionLocal() as db:
        user = db.query(User).filter(User.username == username).first()
        if not user:
            return False
        user.role = new_role
        db.commit()
        return True

def update_user_password(username: str, new_password: str) -> bool:
    with SessionLocal() as db:
        user = db.query(User).filter(User.username == username).first()
        if not user:
            return False
        user.hashed_password = hash_password(new_password)
        db.commit()
        return True