from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class ConversationSession(Base):
    __tablename__ = "conversation_sessions"

    id         = Column(String(36), primary_key=True)   # UUID string
    title      = Column(String(200), nullable=True)      # first question, truncated
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    messages = relationship(
        "AssistantMessage",
        back_populates="session",
        order_by="AssistantMessage.timestamp",
        cascade="all, delete-orphan",
    )


class AssistantMessage(Base):
    __tablename__ = "assistant_messages"

    id         = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(36), ForeignKey("conversation_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    role       = Column(String(20), nullable=False)   # "user" | "assistant"
    content    = Column(Text, nullable=False)
    blocked    = Column(Boolean, default=False)
    timestamp  = Column(DateTime(timezone=True), server_default=func.now())

    session = relationship("ConversationSession", back_populates="messages")
