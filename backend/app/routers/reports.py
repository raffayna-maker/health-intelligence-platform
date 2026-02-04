from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.database import get_db
from app.models.report import Report
from app.schemas.report import ReportGenerateRequest, ReportResponse
from app.services.report_service import report_service

router = APIRouter()


@router.post("/generate")
async def generate_report(req: ReportGenerateRequest, db: AsyncSession = Depends(get_db)):
    result = await report_service.generate(
        report_type=req.report_type,
        date_from=req.date_from,
        date_to=req.date_to,
        db=db,
    )
    return result


@router.get("")
async def list_reports(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Report).order_by(Report.generated_at.desc()).limit(20))
    reports = result.scalars().all()
    total = await db.scalar(select(func.count(Report.id))) or 0
    return {
        "reports": [ReportResponse.model_validate(r) for r in reports],
        "total": total,
    }


@router.get("/{report_id}")
async def get_report(report_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Report).where(Report.id == report_id))
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return ReportResponse.model_validate(report)


@router.delete("/{report_id}")
async def delete_report(report_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Report).where(Report.id == report_id))
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    await db.delete(report)
    await db.flush()
    return {"deleted": True, "report_id": report_id}
