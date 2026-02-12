from sqlalchemy import Column, Integer, String, Date, Text, DateTime, JSON
from sqlalchemy.sql import func
from app.database import Base


class Patient(Base):
    __tablename__ = "patients"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(String(10), unique=True, index=True, nullable=False)
    name = Column(String(200), nullable=False)
    date_of_birth = Column(Date, nullable=False)
    gender = Column(String(10), nullable=False)
    ssn = Column(String(11))
    phone = Column(String(20))
    email = Column(String(200))
    address = Column(Text)
    conditions = Column(JSON, default=list)
    medications = Column(JSON, default=list)
    allergies = Column(JSON, default=list)
    risk_score = Column(Integer, default=50)
    risk_factors = Column(JSON, default=list)
    last_visit = Column(Date)
    next_appointment = Column(Date)
    notes = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
