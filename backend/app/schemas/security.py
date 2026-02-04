from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class SecurityLogResponse(BaseModel):
    id: int
    timestamp: Optional[datetime] = None
    feature: str
    scan_type: str
    content_preview: Optional[str] = None
    hl_verdict: Optional[str] = None
    hl_reason: Optional[str] = None
    hl_scan_time_ms: Optional[int] = None
    aim_verdict: Optional[str] = None
    aim_reason: Optional[str] = None
    aim_scan_time_ms: Optional[int] = None
    final_verdict: str
    agent_run_id: Optional[int] = None

    class Config:
        from_attributes = True


class SecurityStats(BaseModel):
    total_scans: int
    hl_blocks: int
    aim_blocks: int
    both_blocked: int
    disagreements: int
    hl_avg_scan_time_ms: float
    aim_avg_scan_time_ms: float
    hl_only_blocks: int
    aim_only_blocks: int


class DualScanResult(BaseModel):
    hl_verdict: str
    hl_reason: Optional[str] = None
    hl_scan_time_ms: int
    aim_verdict: str
    aim_reason: Optional[str] = None
    aim_scan_time_ms: int
    final_verdict: str
    blocked: bool
