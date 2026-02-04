from sqlalchemy import Column, Integer, String, Text, Date, DateTime, JSON
from sqlalchemy.sql import func
from app.database import Base


class Report(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, index=True)
    report_type = Column(String(50), nullable=False)
    title = Column(String(500), nullable=False)
    content = Column(Text)
    date_from = Column(Date)
    date_to = Column(Date)
    generated_at = Column(DateTime(timezone=True), server_default=func.now())
    metadata_ = Column("metadata", JSON, default=dict)
