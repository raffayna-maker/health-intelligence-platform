from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.sql import func
from app.database import Base


class SecurityLog(Base):
    __tablename__ = "security_logs"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    feature = Column(String(100), nullable=False)
    scan_type = Column(String(50), nullable=False)
    content_preview = Column(Text)
    hl_verdict = Column(String(20))
    hl_reason = Column(Text)
    hl_scan_time_ms = Column(Integer)
    aim_verdict = Column(String(20))
    aim_reason = Column(Text)
    aim_scan_time_ms = Column(Integer)
    final_verdict = Column(String(20), nullable=False)
    agent_run_id = Column(Integer, index=True)
