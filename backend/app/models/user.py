from sqlalchemy import Column, Integer, String, JSON
from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    display_name = Column(String(200), nullable=False)
    role = Column(String(20), nullable=False)  # "admin" | "doctor" | "nurse"
    assigned_patients = Column(JSON, default=list)
    # No password — demo lab accepts any known username for token issuance
