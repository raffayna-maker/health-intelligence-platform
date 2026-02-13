import csv
import io
import json
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from app.database import get_db
from app.models.security_log import SecurityLog
from app.schemas.security import SecurityLogResponse, SecurityStats, ToolStats

router = APIRouter()


@router.get("/logs")
async def get_security_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    feature: str = Query(""),
    verdict: str = Query(""),
    db: AsyncSession = Depends(get_db),
):
    query = select(SecurityLog).order_by(SecurityLog.timestamp.desc())

    if feature:
        query = query.where(SecurityLog.feature == feature)
    if verdict:
        query = query.where(SecurityLog.final_verdict == verdict)

    count_q = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_q) or 0

    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    logs = result.scalars().all()

    return {
        "logs": [SecurityLogResponse.model_validate(l) for l in logs],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/stats", response_model=SecurityStats)
async def get_security_stats(db: AsyncSession = Depends(get_db)):
    total = await db.scalar(select(func.count(SecurityLog.id))) or 0
    total_blocks = await db.scalar(
        select(func.count(SecurityLog.id)).where(SecurityLog.final_verdict == "block")
    ) or 0

    # Legacy HL stats (from hl_* columns for old data)
    hl_blocks = await db.scalar(
        select(func.count(SecurityLog.id)).where(SecurityLog.hl_verdict == "block")
    ) or 0
    aim_blocks = await db.scalar(
        select(func.count(SecurityLog.id)).where(SecurityLog.aim_verdict == "block")
    ) or 0
    both_blocked = await db.scalar(
        select(func.count(SecurityLog.id)).where(
            and_(SecurityLog.hl_verdict == "block", SecurityLog.aim_verdict == "block")
        )
    ) or 0

    hl_only = hl_blocks - both_blocked
    aim_only = aim_blocks - both_blocked
    disagreements = hl_only + aim_only

    hl_avg = await db.scalar(select(func.avg(SecurityLog.hl_scan_time_ms))) or 0
    aim_avg = await db.scalar(select(func.avg(SecurityLog.aim_scan_time_ms))) or 0

    # Build dynamic tool_stats from tool_results JSON column
    tool_stats: dict[str, ToolStats] = {}
    logs_with_tool_results = await db.execute(
        select(SecurityLog.tool_results).where(SecurityLog.tool_results.isnot(None))
    )
    for (tr,) in logs_with_tool_results:
        if not isinstance(tr, dict):
            continue
        for tool_name, result in tr.items():
            if tool_name not in tool_stats:
                tool_stats[tool_name] = {"blocks": 0, "total_time": 0, "count": 0}
            if result.get("verdict") == "block":
                tool_stats[tool_name]["blocks"] += 1
            scan_time = result.get("scan_time_ms", 0)
            if scan_time:
                tool_stats[tool_name]["total_time"] += scan_time
                tool_stats[tool_name]["count"] += 1

    tool_stats_models = {}
    for name, data in tool_stats.items():
        avg_time = data["total_time"] / data["count"] if data["count"] else 0
        tool_stats_models[name] = ToolStats(blocks=data["blocks"], avg_scan_time_ms=round(avg_time, 1))

    return SecurityStats(
        total_scans=total,
        total_blocks=total_blocks,
        tool_stats=tool_stats_models,
        hl_blocks=hl_blocks,
        aim_blocks=aim_blocks,
        both_blocked=both_blocked,
        disagreements=disagreements,
        hl_avg_scan_time_ms=round(float(hl_avg), 1),
        aim_avg_scan_time_ms=round(float(aim_avg), 1),
        hl_only_blocks=hl_only,
        aim_only_blocks=aim_only,
    )


@router.get("/export")
async def export_security_logs(limit: int = Query(100, le=1000), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(SecurityLog).order_by(SecurityLog.timestamp.desc()).limit(limit)
    )
    logs = result.scalars().all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "ID", "Timestamp", "Feature", "Scan Type", "Content Preview",
        "Tool Results",
        "HL Verdict", "HL Reason", "HL Time (ms)",
        "AIM Verdict", "AIM Reason", "AIM Time (ms)",
        "Final Verdict",
    ])
    for log in logs:
        writer.writerow([
            log.id,
            log.timestamp.isoformat() if log.timestamp else "",
            log.feature,
            log.scan_type,
            (log.content_preview or "")[:100],
            json.dumps(log.tool_results) if log.tool_results else "",
            log.hl_verdict,
            log.hl_reason or "",
            log.hl_scan_time_ms,
            log.aim_verdict,
            log.aim_reason or "",
            log.aim_scan_time_ms,
            log.final_verdict,
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=security_logs.csv"},
    )
