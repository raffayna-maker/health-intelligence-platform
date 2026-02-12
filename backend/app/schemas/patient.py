from pydantic import BaseModel
from datetime import date, datetime
from typing import Optional


class PatientBase(BaseModel):
    name: str
    date_of_birth: date
    gender: str
    ssn: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    conditions: list[str] = []
    medications: list[str] = []
    allergies: list[str] = []
    risk_score: int = 50
    risk_factors: list[str] = []
    last_visit: Optional[date] = None
    next_appointment: Optional[date] = None
    notes: Optional[str] = None


class PatientCreate(PatientBase):
    pass


class PatientUpdate(BaseModel):
    name: Optional[str] = None
    date_of_birth: Optional[date] = None
    gender: Optional[str] = None
    ssn: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    conditions: Optional[list[str]] = None
    medications: Optional[list[str]] = None
    allergies: Optional[list[str]] = None
    risk_score: Optional[int] = None
    risk_factors: Optional[list[str]] = None
    last_visit: Optional[date] = None
    next_appointment: Optional[date] = None
    notes: Optional[str] = None


class PatientResponse(PatientBase):
    id: int
    patient_id: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class PatientListResponse(BaseModel):
    patients: list[PatientResponse]
    total: int
    page: int
    page_size: int
