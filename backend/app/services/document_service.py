import json
import os
import aiofiles
from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.config import get_settings
from app.models.document import Document
from app.services.ollama_service import ollama_service
from app.services.security_service import security_scan, get_block_reason
from app.exceptions import AIMBlockedException

settings = get_settings()

EXTRACTION_SYSTEM = """You are a medical document data extractor.
Extract structured data from the provided document text.
Return a JSON object with these fields (if found):
- patient_name
- date_of_birth
- diagnosis
- medications (array)
- procedures (array)
- notes
Only include fields that are present in the document."""

CLASSIFICATION_SYSTEM = """You are a medical document classifier.
Classify the document into one of these categories:
- lab_result
- discharge_summary
- prescription
- radiology_report
- progress_note
- insurance_form
- consent_form
- other
Return a JSON object with: {"classification": "category", "confidence": 0.0-1.0}"""


class DocumentService:
    async def upload(self, file: UploadFile, db: AsyncSession) -> Document:
        os.makedirs(settings.upload_dir, exist_ok=True)
        file_path = os.path.join(settings.upload_dir, file.filename)

        async with aiofiles.open(file_path, "wb") as f:
            content = await file.read()
            await f.write(content)

        doc = Document(
            filename=file.filename,
            file_path=file_path,
            file_type=file.content_type or self._guess_type(file.filename),
            file_size=len(content),
        )
        db.add(doc)
        await db.flush()
        await db.refresh(doc)
        return doc

    async def extract(self, doc_id: int, db: AsyncSession) -> dict:
        result = await db.execute(select(Document).where(Document.id == doc_id))
        doc = result.scalar_one_or_none()
        if not doc:
            raise ValueError(f"Document {doc_id} not found")

        # Read file content
        text = await self._read_file(doc.file_path)

        # Scan document content for prompt injection
        input_scan = await security_scan(
            content=text,
            scan_type="input",
            feature_name="document_extraction",
        )
        if input_scan["blocked"]:
            return {
                "document_id": doc_id,
                "blocked": True,
                "blocked_by": ", ".join(input_scan["blocked_by"]),
                "blocked_reason": get_block_reason(input_scan),
                "security_scan": input_scan,
            }

        # AI extraction
        prompt = f"Extract structured data from this medical document:\n\n{text}"
        try:
            extracted = await ollama_service.generate_structured(prompt, system=EXTRACTION_SYSTEM)
        except AIMBlockedException as e:
            return {
                "document_id": doc_id,
                "blocked": True,
                "blocked_by": "AIM",
                "blocked_reason": e.reason,
            }

        # Scan output
        output_scan = await security_scan(
            content=json.dumps(extracted),
            scan_type="output",
            feature_name="document_extraction",
        )
        if output_scan["blocked"]:
            return {
                "document_id": doc_id,
                "blocked": True,
                "blocked_by": ", ".join(output_scan["blocked_by"]),
                "blocked_reason": get_block_reason(output_scan),
                "security_scan": output_scan,
            }

        doc.extracted_data = extracted
        await db.flush()

        return {
            "document_id": doc_id,
            "extracted_data": extracted,
            "blocked": False,
            "security_scan": output_scan,
        }

    async def classify(self, doc_id: int, db: AsyncSession) -> dict:
        result = await db.execute(select(Document).where(Document.id == doc_id))
        doc = result.scalar_one_or_none()
        if not doc:
            raise ValueError(f"Document {doc_id} not found")

        text = await self._read_file(doc.file_path)

        input_scan = await security_scan(
            content=text,
            scan_type="input",
            feature_name="document_classification",
        )
        if input_scan["blocked"]:
            return {
                "document_id": doc_id,
                "blocked": True,
                "security_scan": input_scan,
            }

        prompt = f"Classify this medical document:\n\n{text[:2000]}"
        try:
            classification = await ollama_service.generate_structured(prompt, system=CLASSIFICATION_SYSTEM)
        except AIMBlockedException as e:
            return {
                "document_id": doc_id,
                "blocked": True,
                "blocked_by": "AIM",
                "blocked_reason": e.reason,
            }

        doc.classification = classification.get("classification", "other")
        await db.flush()

        return {
            "document_id": doc_id,
            "classification": doc.classification,
            "confidence": classification.get("confidence", 0.5),
            "blocked": False,
            "security_scan": input_scan,
        }

    async def _read_file(self, file_path: str) -> str:
        try:
            async with aiofiles.open(file_path, "r", encoding="utf-8", errors="replace") as f:
                return await f.read()
        except Exception:
            return "(Unable to read file content)"

    def _guess_type(self, filename: str) -> str:
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        type_map = {"pdf": "pdf", "txt": "text", "png": "image", "jpg": "image", "jpeg": "image"}
        return type_map.get(ext, "unknown")


document_service = DocumentService()
