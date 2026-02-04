from pydantic import BaseModel
from datetime import datetime
from typing import Optional, Any


class DocumentResponse(BaseModel):
    id: int
    filename: str
    file_type: Optional[str] = None
    file_size: Optional[int] = None
    patient_id: Optional[str] = None
    extracted_data: Optional[dict] = None
    classification: Optional[str] = None
    uploaded_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ExtractionResult(BaseModel):
    document_id: int
    extracted_data: dict[str, Any]
    security_scan: dict


class ClassificationResult(BaseModel):
    document_id: int
    classification: str
    confidence: float
    security_scan: dict
