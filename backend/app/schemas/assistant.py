from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class AssistantQuery(BaseModel):
    question:   str
    patient_id: Optional[str] = None
    use_rag:    bool = True
    session_id: Optional[str] = None


class AssistantResponse(BaseModel):
    answer:         str
    sources:        list[dict] = []
    security_scan:  dict
    blocked:        bool = False
    blocked_by:     Optional[str] = None
    blocked_reason: Optional[str] = None
    session_id:     Optional[str] = None


class QueryHistoryItem(BaseModel):
    id:        int
    question:  str
    answer:    Optional[str] = None
    blocked:   bool
    timestamp: datetime


class SessionMessage(BaseModel):
    role:      str
    content:   str
    blocked:   bool
    timestamp: datetime

    class Config:
        from_attributes = True


class SessionDetail(BaseModel):
    session_id: str
    title:      Optional[str]
    created_at: datetime
    messages:   list[SessionMessage]
