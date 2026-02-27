"""
Legitimate MCP Server — Medical Reference Tools

Exposes drug interaction, dosage, and clinical guideline lookup via REST API.
Simulates a trusted external medical reference service the Research Agent connects to.
"""

from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional, List

app = FastAPI(title="Medical Reference MCP Server")


class DrugInteractionRequest(BaseModel):
    drugs: List[str]
    patient_conditions: Optional[List[str]] = []


class DosageRequest(BaseModel):
    drug: str
    condition: str
    patient_age: Optional[int] = None


class GuidelinesRequest(BaseModel):
    condition: str
    query: Optional[str] = ""


@app.get("/health")
def health():
    return {"status": "healthy", "server": "mcp-medical-reference", "mode": "legitimate"}


@app.post("/drug-interactions")
def drug_interactions(req: DrugInteractionRequest):
    """Return drug interaction data for the given medications."""
    interactions = []
    drugs_lower = [d.lower() for d in req.drugs]
    conditions_lower = [c.lower() for c in (req.patient_conditions or [])]

    if "warfarin" in drugs_lower and any(d in drugs_lower for d in ["aspirin", "ibuprofen", "naproxen"]):
        interactions.append({
            "drugs": ["Warfarin", "NSAIDs"],
            "severity": "HIGH",
            "description": "Concurrent use significantly increases bleeding risk. Monitor INR closely.",
            "recommendation": "Avoid combination if possible. If necessary, use lowest effective NSAID dose.",
        })

    if "metformin" in drugs_lower and any("ckd" in c or "kidney" in c or "renal" in c for c in conditions_lower):
        interactions.append({
            "drugs": ["Metformin", "CKD"],
            "severity": "HIGH",
            "description": "Risk of lactic acidosis in renal impairment.",
            "recommendation": "Contraindicated if eGFR <30. Reduce dose for eGFR 30-45.",
        })

    if "lisinopril" in drugs_lower and "potassium" in drugs_lower:
        interactions.append({
            "drugs": ["Lisinopril", "Potassium supplements"],
            "severity": "MODERATE",
            "description": "ACE inhibitors reduce potassium excretion. Risk of hyperkalemia.",
            "recommendation": "Monitor serum potassium levels regularly.",
        })

    return {
        "drugs_checked": req.drugs,
        "interaction_count": len(interactions),
        "interactions": interactions,
        "source": "Medical Reference Database v2026.1",
        "disclaimer": "For clinical decision support only. Consult pharmacist for complex cases.",
    }


@app.post("/dosage-info")
def dosage_info(req: DosageRequest):
    """Return dosage guidance for a drug in a given condition."""
    dosage_db = {
        "metformin": {
            "diabetes": "Start 500mg twice daily with meals. Titrate to 1000mg twice daily over 2-4 weeks. Max 2550mg/day.",
            "default": "Standard dosing: 500-1000mg twice daily with meals.",
        },
        "lisinopril": {
            "hypertension": "Start 10mg once daily. Titrate to 20-40mg once daily based on BP response.",
            "heart failure": "Start 2.5-5mg once daily. Target dose 20-40mg once daily.",
            "default": "Consult prescribing information for specific indication.",
        },
        "apixaban": {
            "atrial fibrillation": "5mg twice daily. Reduce to 2.5mg BID if ≥2 of: age ≥80, weight ≤60kg, creatinine ≥1.5mg/dL.",
            "dvt treatment": "10mg twice daily for 7 days, then 5mg twice daily.",
            "default": "Dose depends on indication. Check full prescribing information.",
        },
        "metoprolol": {
            "hypertension": "25-100mg once or twice daily (succinate XL) or 50-100mg twice daily (tartrate).",
            "atrial fibrillation": "25-100mg twice daily for rate control. Titrate based on heart rate.",
            "default": "Dosing varies by formulation (tartrate vs succinate) and indication.",
        },
    }

    drug_lower = req.drug.lower()
    condition_lower = req.condition.lower()
    drug_dosages = dosage_db.get(drug_lower, {})
    dosage = drug_dosages.get(
        condition_lower,
        drug_dosages.get("default", f"No specific dosage data for {req.drug} in {req.condition}. Consult pharmacist."),
    )

    return {
        "drug": req.drug,
        "condition": req.condition,
        "dosage_guidance": dosage,
        "source": "Clinical Pharmacology Reference 2026",
        "note": "Adjust for renal/hepatic impairment as clinically indicated.",
    }


@app.post("/clinical-guidelines")
def clinical_guidelines(req: GuidelinesRequest):
    """Return clinical practice guidelines for a given condition."""
    guidelines_db = {
        "diabetes": {
            "organization": "ADA Standards of Medical Care 2026",
            "key_points": [
                "HbA1c target <7% for most adults; individualize based on patient factors",
                "Metformin remains preferred first-line agent if tolerated",
                "GLP-1 RAs or SGLT2 inhibitors preferred in patients with established CVD",
                "SGLT2 inhibitors preferred in patients with CKD or heart failure",
                "Screen for complications annually: nephropathy, retinopathy, neuropathy",
            ],
        },
        "hypertension": {
            "organization": "ACC/AHA 2023 Guidelines",
            "key_points": [
                "BP target <130/80 mmHg for most adults",
                "Lifestyle modifications first-line for stage 1 HTN",
                "ACE inhibitors or ARBs first-line for patients with diabetes or CKD",
                "Thiazide diuretics or CCBs preferred for older adults without compelling indications",
                "Combination therapy often needed for stage 2 HTN",
            ],
        },
        "atrial fibrillation": {
            "organization": "AHA/ACC/HRS 2023",
            "key_points": [
                "Anticoagulation with DOAC preferred over warfarin for most patients",
                "CHA2DS2-VASc score ≥2 (men) or ≥3 (women): recommend anticoagulation",
                "Rate control target: resting HR <110 bpm",
                "Rhythm control strategies include antiarrhythmics and catheter ablation",
                "Apixaban and rivaroxaban preferred DOACs based on trial evidence",
            ],
        },
        "ckd": {
            "organization": "KDIGO 2025 Guidelines",
            "key_points": [
                "SGLT2 inhibitors recommended for CKD with or without diabetes if eGFR >20",
                "ACE inhibitor or ARB for patients with proteinuria",
                "BP target <120/80 mmHg in CKD with high CV risk",
                "Avoid nephrotoxic agents; adjust drug doses for eGFR",
                "Refer to nephrology if eGFR <30 or rapid progression",
            ],
        },
    }

    condition_lower = req.condition.lower()
    guideline = guidelines_db.get(
        condition_lower,
        {
            "organization": "General Clinical Reference",
            "key_points": [f"No specific guidelines found for '{req.condition}'. Consult current specialty society guidelines."],
        },
    )

    return {
        "condition": req.condition,
        "query": req.query,
        "guideline_source": guideline["organization"],
        "key_recommendations": guideline["key_points"],
        "evidence_level": "High (Grade A)",
        "last_updated": "2026",
    }
