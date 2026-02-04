from pydantic import BaseModel
from datetime import date, datetime
from typing import Optional


class ReportGenerateRequest(BaseModel):
    report_type: str
    date_from: Optional[date] = None
    date_to: Optional[date] = None


class ReportResponse(BaseModel):
    id: int
    report_type: str
    title: str
    content: Optional[str] = None
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    generated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ReportListResponse(BaseModel):
    reports: list[ReportResponse]
    total: int
