from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class AssistantQuery(BaseModel):
    question: str
    patient_id: Optional[str] = None
    use_rag: bool = True


class AssistantResponse(BaseModel):
    answer: str
    sources: list[dict] = []
    security_scan: dict
    blocked: bool = False
    blocked_by: Optional[str] = None
    blocked_reason: Optional[str] = None


class QueryHistoryItem(BaseModel):
    id: int
    question: str
    answer: Optional[str] = None
    blocked: bool
    timestamp: datetime
