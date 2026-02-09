"""
Agent tool definitions.
Each tool is an async function that an agent can invoke during its reasoning loop.
"""

import json
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models.patient import Patient


async def get_all_patients(db: AsyncSession, **kwargs) -> dict:
    """Retrieve all patients with basic info."""
    result = await db.execute(select(Patient))
    patients = result.scalars().all()
    return {
        "total": len(patients),
        "patients": [
            {
                "patient_id": p.patient_id,
                "name": p.name,
                "conditions": p.conditions or [],
                "risk_score": p.risk_score,
            }
            for p in patients
        ],
    }


async def get_patient_details(db: AsyncSession, patient_id: str = "", **kwargs) -> dict:
    """Get detailed info for a specific patient."""
    result = await db.execute(select(Patient).where(Patient.patient_id == patient_id))
    p = result.scalar_one_or_none()
    if not p:
        return {"error": f"Patient {patient_id} not found"}
    return {
        "patient_id": p.patient_id,
        "name": p.name,
        "date_of_birth": str(p.date_of_birth),
        "gender": p.gender,
        "conditions": p.conditions or [],
        "medications": p.medications or [],
        "allergies": p.allergies or [],
        "risk_score": p.risk_score,
        "risk_factors": p.risk_factors or [],
        "last_visit": str(p.last_visit) if p.last_visit else None,
        "notes": p.notes,
    }


async def get_patient_risk_scores(db: AsyncSession, **kwargs) -> dict:
    """Get risk scores for all patients, grouped by severity."""
    result = await db.execute(select(Patient))
    patients = result.scalars().all()

    high = [{"patient_id": p.patient_id, "risk_score": p.risk_score, "conditions": p.conditions}
            for p in patients if p.risk_score and p.risk_score > 75]
    medium = [{"patient_id": p.patient_id, "risk_score": p.risk_score}
              for p in patients if p.risk_score and 50 <= p.risk_score <= 75]
    low_count = sum(1 for p in patients if p.risk_score is None or p.risk_score < 50)

    return {
        "total": len(patients),
        "high_risk": {"count": len(high), "patients": sorted(high, key=lambda x: x["risk_score"], reverse=True)},
        "medium_risk": {"count": len(medium)},
        "low_risk": {"count": low_count},
    }


async def alert_clinical_team(db: AsyncSession, priority: str = "normal", message: str = "", patient_ids: list = None, **kwargs) -> dict:
    """Send alert to clinical team (simulated)."""
    return {
        "alert_sent": True,
        "alert_id": f"ALERT-{__import__('datetime').datetime.now().strftime('%Y%m%d-%H%M%S')}",
        "priority": priority,
        "message": message,
        "patient_ids": patient_ids or [],
        "recipients": ["Dr. Smith", "Dr. Johnson", "Nurse Williams"],
        "status": "delivered",
        "expected_response": "within 2 hours" if priority == "high" else "within 24 hours",
    }


async def schedule_appointment(db: AsyncSession, patient_id: str = "", reason: str = "", urgency: str = "routine", **kwargs) -> dict:
    """Schedule appointment for a patient (simulated)."""
    from datetime import datetime, timedelta
    days = {"urgent": 1, "soon": 3, "routine": 7}
    appt_date = datetime.now() + timedelta(days=days.get(urgency, 7))
    return {
        "scheduled": True,
        "patient_id": patient_id,
        "appointment_date": appt_date.strftime("%Y-%m-%d"),
        "reason": reason,
        "urgency": urgency,
    }


async def update_patient_notes(db: AsyncSession, patient_id: str = "", note: str = "", **kwargs) -> dict:
    """Add a note to a patient's record."""
    result = await db.execute(select(Patient).where(Patient.patient_id == patient_id))
    patient = result.scalar_one_or_none()
    if not patient:
        return {"error": f"Patient {patient_id} not found"}

    from datetime import datetime
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    new_note = f"\n[{timestamp}] [Agent] {note}"
    patient.notes = (patient.notes or "") + new_note
    await db.flush()
    return {"updated": True, "patient_id": patient_id}


async def search_medical_literature(db: AsyncSession, query: str = "", **kwargs) -> dict:
    """Search medical literature (simulated with realistic results)."""
    literature_db = {
        "diabetes": [
            {"title": "ADA Standards of Care 2026", "source": "American Diabetes Association", "finding": "Metformin remains first-line for T2DM. GLP-1 RAs recommended for patients with CVD."},
            {"title": "SGLT2 Inhibitors in CKD", "source": "NEJM 2025", "finding": "Empagliflozin reduces kidney disease progression in T2DM with eGFR 20-45."},
        ],
        "hypertension": [
            {"title": "JNC 9 Guidelines", "source": "JAMA", "finding": "Target BP <130/80 for most adults. ACE inhibitors first-line with diabetes."},
        ],
        "copd": [
            {"title": "GOLD 2026 Report", "source": "Global Initiative for COPD", "finding": "Triple therapy (ICS/LABA/LAMA) for patients with frequent exacerbations."},
        ],
        "ckd": [
            {"title": "KDIGO 2025 Guidelines", "source": "Kidney Disease: Improving Global Outcomes", "finding": "SGLT2 inhibitors recommended for CKD with or without diabetes if eGFR >20."},
            {"title": "Metformin Safety in CKD", "source": "Cochrane Review 2025", "finding": "Metformin contraindicated if eGFR <30. Dose reduction recommended for eGFR 30-45."},
        ],
        "elderly": [
            {"title": "Geriatric Pharmacology Review", "source": "Journal of Geriatric Medicine", "finding": "Deprescribing recommended for polypharmacy. Avoid sulfonylureas due to hypoglycemia risk."},
        ],
    }

    results = []
    for keyword, articles in literature_db.items():
        if keyword in query.lower():
            results.extend(articles)

    if not results:
        results = [{"title": "General Medical Reference", "source": "UpToDate", "finding": f"General information available for: {query}"}]

    return {"query": query, "results_count": len(results), "results": results}


async def check_drug_interactions(db: AsyncSession, medications: list = None, conditions: list = None, **kwargs) -> dict:
    """Check drug interactions (simulated)."""
    interactions = []
    meds = medications or []
    conds = conditions or []

    med_lower = [m.lower() for m in meds]
    cond_lower = [c.lower() for c in conds]

    if "metformin" in " ".join(med_lower) and any("ckd" in c or "kidney" in c for c in cond_lower):
        interactions.append({
            "severity": "high",
            "drug": "Metformin",
            "condition": "CKD",
            "warning": "Contraindicated if eGFR <30. Risk of lactic acidosis.",
        })

    if any("sulfonylurea" in m or "glipizide" in m or "glyburide" in m for m in med_lower):
        if any("elderly" in c or "age" in c for c in cond_lower):
            interactions.append({
                "severity": "moderate",
                "drug": "Sulfonylurea",
                "condition": "Elderly patient",
                "warning": "Increased hypoglycemia risk in elderly. Consider DPP-4 inhibitor instead.",
            })

    return {"medications": meds, "conditions": conds, "interactions": interactions, "interaction_count": len(interactions)}


async def query_patient_cases(db: AsyncSession, conditions: list = None, min_age: int = 0, max_age: int = 200, **kwargs) -> dict:
    """Query patient database for similar cases."""
    from datetime import date

    result = await db.execute(select(Patient))
    patients = result.scalars().all()

    matches = []
    for p in patients:
        age = (date.today() - p.date_of_birth).days // 365 if p.date_of_birth else 0
        if min_age <= age <= max_age:
            if conditions:
                patient_conds = [c.lower() for c in (p.conditions or [])]
                if any(c.lower() in " ".join(patient_conds) for c in conditions):
                    matches.append({
                        "patient_id": p.patient_id,
                        "age": age,
                        "conditions": p.conditions,
                        "medications": p.medications,
                        "risk_score": p.risk_score,
                    })
            else:
                matches.append({"patient_id": p.patient_id, "age": age, "conditions": p.conditions})

    return {"query": {"conditions": conditions, "age_range": [min_age, max_age]}, "matches": len(matches), "patients": matches[:20]}


async def send_patient_email(db: AsyncSession, patient_id: str = "", subject: str = "", message: str = "", priority: str = "normal", **kwargs) -> dict:
    """Send email to patient (simulated - logs to patient notes)."""
    result = await db.execute(select(Patient).where(Patient.patient_id == patient_id))
    patient = result.scalar_one_or_none()

    if not patient:
        return {"error": f"Patient {patient_id} not found"}

    from datetime import datetime
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    email_address = f"{patient_id}@patients.healthcare.local"

    # Log email to patient notes for demo purposes
    email_note = f"[EMAIL SENT] To: {email_address}\nSubject: {subject}\nMessage: {message[:200]}..."
    patient.notes = (patient.notes or "") + f"\n[{timestamp}] {email_note}"
    await db.flush()

    return {
        "sent": True,
        "patient_id": patient_id,
        "patient_name": patient.name,
        "email": email_address,
        "subject": subject,
        "priority": priority,
        "timestamp": timestamp,
        "delivery_status": "delivered (logged to patient notes)",
    }


async def request_medication_refill(db: AsyncSession, patient_id: str = "", medication: str = "", **kwargs) -> dict:
    """Request medication refill (simulated)."""
    result = await db.execute(select(Patient).where(Patient.patient_id == patient_id))
    patient = result.scalar_one_or_none()

    if not patient:
        return {"error": f"Patient {patient_id} not found"}

    from datetime import datetime, timedelta
    timestamp = datetime.now()
    refill_id = f"RX-{timestamp.strftime('%Y%m%d-%H%M%S')}"

    # Log refill request to patient notes
    refill_note = f"[REFILL REQUESTED] Medication: {medication}, Refill ID: {refill_id}"
    patient.notes = (patient.notes or "") + f"\n[{timestamp.strftime('%Y-%m-%d %H:%M')}] {refill_note}"
    await db.flush()

    return {
        "refill_requested": True,
        "patient_id": patient_id,
        "patient_name": patient.name,
        "medication": medication,
        "refill_id": refill_id,
        "pharmacy": "CVS Pharmacy #1234",
        "estimated_ready": (timestamp + timedelta(days=1)).strftime("%Y-%m-%d"),
        "status": "pending_pharmacy_approval",
    }


async def get_patients_needing_followup(db: AsyncSession, days_threshold: int = 90, **kwargs) -> dict:
    """Find patients who haven't had appointments in the specified number of days."""
    from datetime import date, timedelta

    result = await db.execute(select(Patient))
    patients = result.scalars().all()

    threshold_date = date.today() - timedelta(days=days_threshold)
    patients_needing_followup = []

    for p in patients:
        if p.last_visit:
            if p.last_visit < threshold_date:
                days_since = (date.today() - p.last_visit).days
                # Generate test email from patient_id
                test_email = f"{p.patient_id.lower().replace('-', '')}@test.com"
                patients_needing_followup.append({
                    "patient_id": p.patient_id,
                    "name": p.name,
                    "last_visit": str(p.last_visit),
                    "days_since_last_visit": days_since,
                    "email": test_email,
                    "conditions": p.conditions or [],
                })

    return {
        "threshold_days": days_threshold,
        "total_patients_needing_followup": len(patients_needing_followup),
        "patients": sorted(patients_needing_followup, key=lambda x: x["days_since_last_visit"], reverse=True),
    }


async def send_followup_email(db: AsyncSession, patient_id: str = "", **kwargs) -> dict:
    """Send actual follow-up appointment reminder email via Gmail SMTP."""
    from datetime import date
    from app.services.email_service import email_service

    result = await db.execute(select(Patient).where(Patient.patient_id == patient_id))
    patient = result.scalar_one_or_none()

    if not patient:
        return {"error": f"Patient {patient_id} not found"}

    if not patient.last_visit:
        return {"error": f"Patient {patient_id} has no last_visit date on record"}

    days_since = (date.today() - patient.last_visit).days

    # Generate test email
    test_email = f"{patient_id.lower().replace('-', '')}@test.com"

    # Send email via SMTP in a thread to avoid blocking the async event loop
    import asyncio
    email_result = await asyncio.to_thread(
        email_service.send_appointment_reminder,
        to_email=test_email,
        patient_name=patient.name,
        days_since_last_appointment=days_since,
    )

    # Log to patient notes
    if email_result["success"]:
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        note = f"[FOLLOW-UP EMAIL SENT] To: {test_email}, Days since last visit: {days_since}"
        patient.notes = (patient.notes or "") + f"\n[{timestamp}] {note}"
        await db.flush()

    return email_result


async def list_documents(db: AsyncSession, **kwargs) -> dict:
    """List all uploaded documents."""
    from app.models.document import Document

    result = await db.execute(select(Document).order_by(Document.id))
    docs = result.scalars().all()

    return {
        "total": len(docs),
        "documents": [
            {
                "id": d.id,
                "filename": d.filename,
                "file_type": d.file_type,
                "file_size": d.file_size,
                "classification": d.classification,
                "has_extracted_data": d.extracted_data is not None,
                "uploaded_at": str(d.uploaded_at) if d.uploaded_at else None,
            }
            for d in docs
        ],
    }


async def read_document(db: AsyncSession, document_id: int = 0, **kwargs) -> dict:
    """Read the content of an uploaded document."""
    import aiofiles
    from app.models.document import Document

    result = await db.execute(select(Document).where(Document.id == document_id))
    doc = result.scalar_one_or_none()

    if not doc:
        return {"error": f"Document {document_id} not found"}

    # Read raw file content
    raw_text = ""
    try:
        async with aiofiles.open(doc.file_path, "r", encoding="utf-8", errors="replace") as f:
            raw_text = await f.read()
    except Exception as e:
        raw_text = f"(Unable to read file: {e})"

    return {
        "id": doc.id,
        "filename": doc.filename,
        "file_type": doc.file_type,
        "classification": doc.classification,
        "extracted_data": doc.extracted_data,
        "content": raw_text[:5000],
        "content_length": len(raw_text),
    }


async def web_search(db: AsyncSession, query: str = "", **kwargs) -> dict:
    """Search the web using DuckDuckGo Instant Answer API."""
    import httpx

    if not query:
        return {"error": "No search query provided"}

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                "https://api.duckduckgo.com/",
                params={"q": query, "format": "json", "no_html": "1", "skip_disambig": "1"},
            )
            data = response.json()

        results = []

        # Main abstract
        if data.get("Abstract"):
            results.append({
                "title": data.get("Heading", ""),
                "source": data.get("AbstractSource", ""),
                "url": data.get("AbstractURL", ""),
                "text": data["Abstract"],
            })

        # Related topics
        for topic in (data.get("RelatedTopics") or [])[:5]:
            if isinstance(topic, dict) and topic.get("Text"):
                results.append({
                    "title": topic.get("Text", "")[:100],
                    "url": topic.get("FirstURL", ""),
                    "text": topic.get("Text", ""),
                })

        if not results:
            return {"query": query, "results_count": 0, "results": [], "note": "No instant answer available. Try a more specific query."}

        return {"query": query, "results_count": len(results), "results": results}

    except Exception as e:
        return {"query": query, "error": f"Search failed: {str(e)}", "results": []}


# Tool registry used by agents
TOOL_REGISTRY = {
    "get_all_patients": {
        "fn": get_all_patients,
        "description": "Get all patients with basic info (ID, name, conditions, risk score)",
        "parameters": {},
    },
    "get_patient_details": {
        "fn": get_patient_details,
        "description": "Get detailed information for a specific patient",
        "parameters": {"patient_id": "string - The patient ID (e.g. PT-001)"},
    },
    "get_patient_risk_scores": {
        "fn": get_patient_risk_scores,
        "description": "Get risk scores for all patients, grouped by severity (high/medium/low)",
        "parameters": {},
    },
    "alert_clinical_team": {
        "fn": alert_clinical_team,
        "description": "Send an alert to the clinical team",
        "parameters": {"priority": "string - high/normal/low", "message": "string - Alert message", "patient_ids": "array - List of patient IDs"},
    },
    "schedule_appointment": {
        "fn": schedule_appointment,
        "description": "Schedule an appointment for a patient",
        "parameters": {"patient_id": "string", "reason": "string", "urgency": "string - urgent/soon/routine"},
    },
    "update_patient_notes": {
        "fn": update_patient_notes,
        "description": "Add a note to a patient's record",
        "parameters": {"patient_id": "string", "note": "string"},
    },
    "search_medical_literature": {
        "fn": search_medical_literature,
        "description": "Search medical literature for evidence-based information",
        "parameters": {"query": "string - Search query"},
    },
    "check_drug_interactions": {
        "fn": check_drug_interactions,
        "description": "Check for drug interactions given medications and conditions",
        "parameters": {"medications": "array of strings", "conditions": "array of strings"},
    },
    "query_patient_cases": {
        "fn": query_patient_cases,
        "description": "Query patient database for similar cases by conditions and age",
        "parameters": {"conditions": "array of strings", "min_age": "int", "max_age": "int"},
    },
    "send_patient_email": {
        "fn": send_patient_email,
        "description": "Send email to a patient (simulated - logs to patient notes)",
        "parameters": {"patient_id": "string", "subject": "string", "message": "string", "priority": "string - high/normal/low"},
    },
    "request_medication_refill": {
        "fn": request_medication_refill,
        "description": "Request medication refill for a patient (simulated)",
        "parameters": {"patient_id": "string", "medication": "string"},
    },
    "get_patients_needing_followup": {
        "fn": get_patients_needing_followup,
        "description": "Find patients who haven't had appointments in the specified number of days (default 90)",
        "parameters": {"days_threshold": "int - Number of days since last visit (default 90)"},
    },
    "send_followup_email": {
        "fn": send_followup_email,
        "description": "Send follow-up appointment reminder email to a patient via Gmail SMTP",
        "parameters": {"patient_id": "string - The patient ID (e.g. PT-001)"},
    },
    "list_documents": {
        "fn": list_documents,
        "description": "List all uploaded documents with their ID, filename, type, and classification",
        "parameters": {},
    },
    "read_document": {
        "fn": read_document,
        "description": "Read the content of an uploaded document by its ID",
        "parameters": {"document_id": "int - The document ID number"},
    },
    "web_search": {
        "fn": web_search,
        "description": "Search the web for information using DuckDuckGo",
        "parameters": {"query": "string - The search query"},
    },
}
