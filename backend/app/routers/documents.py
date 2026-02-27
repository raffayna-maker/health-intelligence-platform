from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from app.database import get_db
from app.models.document import Document
from app.schemas.document import DocumentResponse
from app.services.document_service import document_service
from app.auth import get_current_user, UserPrincipal

router = APIRouter()


@router.get("")
async def list_documents(
    db: AsyncSession = Depends(get_db),
    current_user: UserPrincipal = Depends(get_current_user),
):
    query = select(Document).order_by(Document.uploaded_at.desc())

    allowed_ids = current_user.get_allowed_patient_ids()
    if allowed_ids is not None:
        # Show docs belonging to assigned patients + docs with no patient association
        query = query.where(
            or_(Document.patient_id.in_(allowed_ids), Document.patient_id.is_(None))
        )

    result = await db.execute(query)
    docs = result.scalars().all()
    return {"documents": [DocumentResponse.model_validate(d) for d in docs], "total": len(docs)}


@router.post("/upload", response_model=DocumentResponse)
async def upload_document(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: UserPrincipal = Depends(get_current_user),
):
    if not current_user.can_write:
        raise HTTPException(status_code=403, detail="Your role does not permit uploading documents")
    doc = await document_service.upload(file, db)
    return DocumentResponse.model_validate(doc)


@router.post("/{doc_id}/extract")
async def extract_document(
    doc_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserPrincipal = Depends(get_current_user),
):
    if not current_user.can_write:
        raise HTTPException(status_code=403, detail="Your role does not permit extracting documents")
    try:
        result = await document_service.extract(doc_id, db)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{doc_id}/classify")
async def classify_document(
    doc_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserPrincipal = Depends(get_current_user),
):
    if not current_user.can_write:
        raise HTTPException(status_code=403, detail="Your role does not permit classifying documents")
    try:
        result = await document_service.classify(doc_id, db)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{doc_id}/download")
async def download_document(
    doc_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserPrincipal = Depends(get_current_user),
):
    result = await db.execute(select(Document).where(Document.id == doc_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    # Check patient access if the document is linked to a patient
    if doc.patient_id and not current_user.has_access_to_patient(doc.patient_id):
        raise HTTPException(status_code=403, detail="Access denied: document belongs to a patient not in your assigned list")
    return FileResponse(doc.file_path, filename=doc.filename)


@router.delete("/{doc_id}")
async def delete_document(
    doc_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserPrincipal = Depends(get_current_user),
):
    if not current_user.can_write:
        raise HTTPException(status_code=403, detail="Your role does not permit deleting documents")

    result = await db.execute(select(Document).where(Document.id == doc_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    import os
    if os.path.exists(doc.file_path):
        os.remove(doc.file_path)

    await db.delete(doc)
    await db.flush()
    return {"deleted": True, "document_id": doc_id}
