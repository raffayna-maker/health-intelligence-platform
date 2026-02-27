from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.database import get_db
from app.schemas.assistant import AssistantQuery, AssistantResponse, SessionDetail, SessionMessage
from app.services.assistant_service import assistant_service
from app.models.security_log import SecurityLog
from app.models.conversation import ConversationSession, AssistantMessage
from app.auth import get_current_user, UserPrincipal

router = APIRouter()


@router.post("/query", response_model=AssistantResponse)
async def query_assistant(
    req: AssistantQuery,
    db: AsyncSession = Depends(get_db),
    current_user: UserPrincipal = Depends(get_current_user),
):
    return await assistant_service.query(
        question=req.question,
        patient_id=req.patient_id,
        use_rag=req.use_rag,
        db=db,
        allowed_patient_ids=current_user.get_allowed_patient_ids(),
        session_id=req.session_id or None,
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


@router.get("/sessions")
async def list_sessions(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(ConversationSession)
        .order_by(ConversationSession.created_at.desc())
        .limit(50)
    )
    sessions = result.scalars().all()
    return {
        "sessions": [
            {
                "session_id": s.id,
                "title": s.title,
                "created_at": s.created_at.isoformat() if s.created_at else None,
            }
            for s in sessions
        ]
    }


@router.get("/sessions/{session_id}", response_model=SessionDetail)
async def get_session(session_id: str, db: AsyncSession = Depends(get_db)):
    session_obj = await db.get(ConversationSession, session_id)
    if not session_obj:
        raise HTTPException(status_code=404, detail="Session not found")

    msgs_result = await db.execute(
        select(AssistantMessage)
        .where(AssistantMessage.session_id == session_id)
        .order_by(AssistantMessage.timestamp)
    )
    msgs = msgs_result.scalars().all()

    return SessionDetail(
        session_id=session_obj.id,
        title=session_obj.title,
        created_at=session_obj.created_at,
        messages=[
            SessionMessage(
                role=m.role,
                content=m.content,
                blocked=m.blocked,
                timestamp=m.timestamp,
            )
            for m in msgs
        ],
    )


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str, db: AsyncSession = Depends(get_db)):
    session_obj = await db.get(ConversationSession, session_id)
    if not session_obj:
        raise HTTPException(status_code=404, detail="Session not found")
    await db.delete(session_obj)
    await db.commit()
    return {"deleted": session_id}
