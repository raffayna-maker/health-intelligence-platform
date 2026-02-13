from pydantic import BaseModel
from datetime import datetime
from typing import Optional, Dict, Any


class ToolResult(BaseModel):
    verdict: str
    reason: Optional[str] = None
    scan_time_ms: int = 0
    details: Optional[Dict[str, Any]] = None


class ScanResult(BaseModel):
    tool_results: Dict[str, ToolResult] = {}
    final_verdict: str
    blocked: bool


# Backward compatibility alias
DualScanResult = ScanResult


class SecurityLogResponse(BaseModel):
    id: int
    timestamp: Optional[datetime] = None
    feature: str
    scan_type: str
    content_preview: Optional[str] = None
    tool_results: Optional[Dict[str, Any]] = None
    # Legacy columns (kept for backward compat with existing data)
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


class ToolStats(BaseModel):
    blocks: int = 0
    avg_scan_time_ms: float = 0.0


class SecurityStats(BaseModel):
    total_scans: int
    total_blocks: int
    tool_stats: Dict[str, ToolStats] = {}
    # Legacy fields (kept for backward compat)
    hl_blocks: int = 0
    aim_blocks: int = 0
    both_blocked: int = 0
    disagreements: int = 0
    hl_avg_scan_time_ms: float = 0.0
    aim_avg_scan_time_ms: float = 0.0
    hl_only_blocks: int = 0
    aim_only_blocks: int = 0
