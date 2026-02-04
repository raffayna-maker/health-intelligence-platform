from pydantic import BaseModel
from datetime import datetime
from typing import Optional, Any


class AgentInfo(BaseModel):
    agent_type: str
    name: str
    description: str
    tools: list[str]
    last_run: Optional[datetime] = None
    last_status: Optional[str] = None


class AgentRunRequest(BaseModel):
    task: Optional[str] = None


class AgentChatRequest(BaseModel):
    message: str


class AgentStepResponse(BaseModel):
    id: int
    iteration: int
    step_type: str
    content: Optional[str] = None
    tool_name: Optional[str] = None
    tool_input: Optional[dict] = None
    tool_output: Optional[dict] = None
    security_scans: Optional[dict] = None
    timestamp: Optional[datetime] = None

    class Config:
        from_attributes = True


class AgentRunResponse(BaseModel):
    id: int
    agent_type: str
    task: str
    status: str
    iterations: int
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[dict] = None
    summary: Optional[str] = None
    steps: list[AgentStepResponse] = []

    class Config:
        from_attributes = True


class AgentRunListResponse(BaseModel):
    runs: list[AgentRunResponse]
    total: int
