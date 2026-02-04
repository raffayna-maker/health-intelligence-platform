from sqlalchemy import Column, Integer, String, Text, DateTime, JSON
from sqlalchemy.sql import func
from app.database import Base


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(500), nullable=False)
    file_path = Column(String(1000), nullable=False)
    file_type = Column(String(50))
    file_size = Column(Integer)
    patient_id = Column(String(10), index=True)
    extracted_data = Column(JSON)
    classification = Column(String(100))
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())
