from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.database import get_db
from app.models.patient import Patient
from app.models.security_log import SecurityLog
from app.models.agent_run import AgentRun

router = APIRouter()


@router.get("/stats")
async def get_dashboard_stats(db: AsyncSession = Depends(get_db)):
    patient_count = await db.scalar(select(func.count(Patient.id))) or 0
    total_scans = await db.scalar(select(func.count(SecurityLog.id))) or 0
    total_blocks = await db.scalar(
        select(func.count(SecurityLog.id)).where(SecurityLog.final_verdict == "block")
    ) or 0
    agent_runs = await db.scalar(select(func.count(AgentRun.id))) or 0
    successful_runs = await db.scalar(
        select(func.count(AgentRun.id)).where(AgentRun.status == "completed")
    ) or 0

    # Recent agent runs
    recent_runs_result = await db.execute(
        select(AgentRun).order_by(AgentRun.started_at.desc()).limit(5)
    )
    recent_runs = recent_runs_result.scalars().all()

    # Recent security events
    recent_security_result = await db.execute(
        select(SecurityLog).order_by(SecurityLog.timestamp.desc()).limit(10)
    )
    recent_security = recent_security_result.scalars().all()

    return {
        "patients": {"total": patient_count},
        "security": {
            "total_scans": total_scans,
            "total_blocks": total_blocks,
        },
        "agents": {
            "total_runs": agent_runs,
            "successful_runs": successful_runs,
        },
        "recent_agent_runs": [
            {
                "id": r.id,
                "agent_type": r.agent_type,
                "status": r.status,
                "started_at": r.started_at.isoformat() if r.started_at else None,
                "summary": r.summary,
            }
            for r in recent_runs
        ],
        "recent_security_events": [
            {
                "id": s.id,
                "feature": s.feature,
                "final_verdict": s.final_verdict,
                "tool_results": s.tool_results,
                # Legacy fields for old data
                "hl_verdict": s.hl_verdict,
                "aim_verdict": s.aim_verdict,
                "timestamp": s.timestamp.isoformat() if s.timestamp else None,
            }
            for s in recent_security
        ],
    }
