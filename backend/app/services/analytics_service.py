import json
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models.patient import Patient
from app.services.ollama_service import ollama_service
from app.services.security_service import dual_security_scan
from app.exceptions import AIMBlockedException


RISK_SYSTEM = """You are a clinical risk assessment AI.
Given a patient's data, calculate an updated risk score (0-100) and provide:
- risk_score: integer 0-100
- risk_factors: array of identified risk factors
- recommendation: brief clinical recommendation
Return as JSON."""

TREND_SYSTEM = """You are a healthcare analytics AI.
Given a query about patient trends and the provided patient data summary, provide insightful analysis.
Be specific with numbers and percentages when possible.
Base your analysis only on the data provided."""

READMISSION_SYSTEM = """You are a readmission prediction AI.
Given a patient's data, predict readmission risk:
- readmission_risk: float 0.0-1.0
- factors: array of contributing factors
- recommendation: preventive measures
Return as JSON."""


class AnalyticsService:
    async def get_risk_distribution(self, db: AsyncSession) -> dict:
        result = await db.execute(select(Patient))
        patients = result.scalars().all()

        high = [p for p in patients if p.risk_score and p.risk_score > 75]
        medium = [p for p in patients if p.risk_score and 50 <= p.risk_score <= 75]
        low = [p for p in patients if p.risk_score is None or p.risk_score < 50]

        return {
            "high": len(high),
            "medium": len(medium),
            "low": len(low),
            "high_patients": [
                {
                    "patient_id": p.patient_id,
                    "name": p.name,
                    "risk_score": p.risk_score,
                    "conditions": p.conditions,
                }
                for p in sorted(high, key=lambda x: x.risk_score or 0, reverse=True)[:20]
            ],
        }

    async def get_condition_prevalence(self, db: AsyncSession) -> dict:
        result = await db.execute(select(Patient.conditions))
        rows = result.all()

        condition_counts: dict[str, int] = {}
        for (conditions,) in rows:
            if conditions:
                for c in conditions:
                    condition_counts[c] = condition_counts.get(c, 0) + 1

        return {"conditions": dict(sorted(condition_counts.items(), key=lambda x: x[1], reverse=True))}

    async def calculate_risk(self, patient_id: str, db: AsyncSession) -> dict:
        result = await db.execute(select(Patient).where(Patient.patient_id == patient_id))
        patient = result.scalar_one_or_none()
        if not patient:
            raise ValueError(f"Patient {patient_id} not found")

        patient_info = (
            f"Patient: {patient.name}, Age-related DOB: {patient.date_of_birth}, "
            f"Gender: {patient.gender}, Conditions: {patient.conditions}, "
            f"Medications: {patient.medications}, Risk Factors: {patient.risk_factors}, "
            f"Current Risk Score: {patient.risk_score}"
        )

        input_scan = await dual_security_scan(
            content=patient_info, scan_type="input", feature_name="risk_calculation"
        )
        if input_scan["blocked"]:
            return {"patient_id": patient_id, "blocked": True, "security_scan": input_scan}

        try:
            ai_result = await ollama_service.generate_structured(
                f"Assess risk for this patient:\n{patient_info}", system=RISK_SYSTEM
            )
        except AIMBlockedException as e:
            return {"patient_id": patient_id, "blocked": True, "blocked_by": "AIM", "blocked_reason": e.reason}

        output_scan = await dual_security_scan(
            content=json.dumps(ai_result), scan_type="output", feature_name="risk_calculation"
        )

        new_score = ai_result.get("risk_score", patient.risk_score)
        if isinstance(new_score, int) and 0 <= new_score <= 100:
            patient.risk_score = new_score
            await db.flush()

        return {
            "patient_id": patient_id,
            "risk_score": new_score,
            "risk_factors": ai_result.get("risk_factors", []),
            "recommendation": ai_result.get("recommendation", ""),
            "blocked": False,
            "security_scan": output_scan,
        }

    async def analyze_trends(self, query: str, db: AsyncSession) -> dict:
        # Get summary statistics
        result = await db.execute(select(Patient))
        patients = result.scalars().all()

        summary = f"Total patients: {len(patients)}. "
        condition_counts: dict[str, int] = {}
        for p in patients:
            if p.conditions:
                for c in p.conditions:
                    condition_counts[c] = condition_counts.get(c, 0) + 1
        summary += f"Conditions: {condition_counts}. "
        avg_risk = sum(p.risk_score or 0 for p in patients) / max(len(patients), 1)
        summary += f"Average risk score: {avg_risk:.1f}"

        input_scan = await dual_security_scan(
            content=query, scan_type="input", feature_name="trend_analysis"
        )
        if input_scan["blocked"]:
            return {"query": query, "blocked": True, "security_scan": input_scan}

        try:
            prompt = f"Data Summary:\n{summary}\n\nAnalysis Query: {query}"
            analysis = await ollama_service.generate(prompt, system=TREND_SYSTEM)
        except AIMBlockedException as e:
            return {"query": query, "blocked": True, "blocked_by": "AIM", "blocked_reason": e.reason}

        output_scan = await dual_security_scan(
            content=analysis, scan_type="output", feature_name="trend_analysis"
        )
        if output_scan["blocked"]:
            return {"query": query, "blocked": True, "security_scan": output_scan}

        return {
            "query": query,
            "analysis": analysis,
            "blocked": False,
            "security_scan": output_scan,
        }

    async def predict_readmission(self, patient_id: str, db: AsyncSession) -> dict:
        result = await db.execute(select(Patient).where(Patient.patient_id == patient_id))
        patient = result.scalar_one_or_none()
        if not patient:
            raise ValueError(f"Patient {patient_id} not found")

        patient_info = (
            f"Patient: {patient.name}, DOB: {patient.date_of_birth}, "
            f"Conditions: {patient.conditions}, Medications: {patient.medications}, "
            f"Risk Score: {patient.risk_score}, Last Visit: {patient.last_visit}"
        )

        input_scan = await dual_security_scan(
            content=patient_info, scan_type="input", feature_name="readmission_prediction"
        )
        if input_scan["blocked"]:
            return {"patient_id": patient_id, "blocked": True, "security_scan": input_scan}

        try:
            ai_result = await ollama_service.generate_structured(
                f"Predict readmission risk:\n{patient_info}", system=READMISSION_SYSTEM
            )
        except AIMBlockedException as e:
            return {"patient_id": patient_id, "blocked": True, "blocked_by": "AIM", "blocked_reason": e.reason}

        return {
            "patient_id": patient_id,
            "readmission_risk": ai_result.get("readmission_risk", 0.5),
            "factors": ai_result.get("factors", []),
            "recommendation": ai_result.get("recommendation", ""),
            "blocked": False,
            "security_scan": input_scan,
        }


analytics_service = AnalyticsService()
