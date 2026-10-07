# app/models/apt_users_b.py
# SQLAlchemy ORM Model mapping to PostgreSQL table 'apt_users_b'
from sqlalchemy import Column, Integer, String, Boolean, DateTime, func
from app.database import Base

class AptUserB(Base):
    __tablename__ = "apt_users_b"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username = Column(String(255), unique=True, nullable=False)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(50), default="PARENT")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
