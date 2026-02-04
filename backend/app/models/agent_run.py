from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base


class AgentRun(Base):
    __tablename__ = "agent_runs"

    id = Column(Integer, primary_key=True, index=True)
    agent_type = Column(String(50), nullable=False)
    task = Column(Text, nullable=False)
    status = Column(String(20), default="running")
    iterations = Column(Integer, default=0)
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True))
    result = Column(JSON)
    summary = Column(Text)
    steps = relationship("AgentStep", back_populates="agent_run", order_by="AgentStep.iteration")


class AgentStep(Base):
    __tablename__ = "agent_steps"

    id = Column(Integer, primary_key=True, index=True)
    agent_run_id = Column(Integer, ForeignKey("agent_runs.id"), nullable=False)
    iteration = Column(Integer, nullable=False)
    step_type = Column(String(30), nullable=False)
    content = Column(Text)
    tool_name = Column(String(100))
    tool_input = Column(JSON)
    tool_output = Column(JSON)
    security_scans = Column(JSON)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    agent_run = relationship("AgentRun", back_populates="steps")
