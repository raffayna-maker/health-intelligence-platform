from pydantic import BaseModel
from typing import Optional


class RiskDistribution(BaseModel):
    high: int
    medium: int
    low: int
    high_patients: list[dict]


class ConditionPrevalence(BaseModel):
    conditions: dict[str, int]


class RiskCalculationRequest(BaseModel):
    patient_id: str


class RiskCalculationResponse(BaseModel):
    patient_id: str
    risk_score: int
    risk_factors: list[str]
    recommendation: str
    security_scan: dict


class TrendRequest(BaseModel):
    query: str


class TrendResponse(BaseModel):
    query: str
    analysis: str
    security_scan: dict


class ReadmissionRequest(BaseModel):
    patient_id: str


class ReadmissionResponse(BaseModel):
    patient_id: str
    readmission_risk: float
    factors: list[str]
    recommendation: str
    security_scan: dict
