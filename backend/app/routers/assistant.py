from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.schemas.assistant import AssistantQuery, AssistantResponse
from app.services.assistant_service import assistant_service
from app.models.security_log import SecurityLog

router = APIRouter()


@router.post("/query", response_model=AssistantResponse)
async def query_assistant(req: AssistantQuery, db: AsyncSession = Depends(get_db)):
    return await assistant_service.query(
        question=req.question,
        patient_id=req.patient_id,
        use_rag=req.use_rag,
        db=db,
    )


@router.get("/history")
async def query_history(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(SecurityLog)
        .where(SecurityLog.feature == "clinical_assistant")
        .where(SecurityLog.scan_type == "input")
        .order_by(SecurityLog.timestamp.desc())
        .limit(10)
    )
    logs = result.scalars().all()
    return {
        "history": [
            {
                "id": log.id,
                "question": log.content_preview,
                "blocked": log.final_verdict == "block",
                "timestamp": log.timestamp.isoformat() if log.timestamp else None,
            }
            for log in logs
        ]
    }
