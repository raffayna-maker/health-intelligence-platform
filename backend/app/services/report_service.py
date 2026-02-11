from datetime import date, datetime
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models.patient import Patient
from app.models.security_log import SecurityLog
from app.models.agent_run import AgentRun
from app.models.report import Report
from app.services.ollama_service import ollama_service
from app.services.security_service import dual_security_scan
from app.exceptions import AIMBlockedException


REPORT_SYSTEM = """You are a healthcare report generator.
Generate a professional, detailed report based on the provided data.
Use clear sections with headers.
Include specific numbers and statistics.
Format the report in Markdown."""


class ReportService:
    async def generate(
        self,
        report_type: str,
        date_from: Optional[date],
        date_to: Optional[date],
        db: AsyncSession,
    ) -> dict:
        # Gather data based on report type
        data_summary = await self._gather_data(report_type, date_from, date_to, db)

        prompt = f"Generate a {report_type} report for the healthcare platform.\n\nData:\n{data_summary}"

        input_scan = await dual_security_scan(
            content=prompt, scan_type="input", feature_name="report_generation"
        )
        
        # Log security scan
        from app.services.security_service import log_security_scan
        await log_security_scan(db, input_scan, prompt)
        if input_scan["blocked"]:
            return {"blocked": True, "security_scan": input_scan}

        try:
            content = await ollama_service.generate(prompt, system=REPORT_SYSTEM)
        except AIMBlockedException as e:
            return {"blocked": True, "blocked_by": "AIM", "blocked_reason": e.reason}

        output_scan = await dual_security_scan(
            content=content, scan_type="output", feature_name="report_generation"
        )
        
        # Log security scan
        await log_security_scan(db, output_scan, content)
        if output_scan["blocked"]:
            return {"blocked": True, "security_scan": output_scan}

        title_map = {
            "compliance": "HIPAA Compliance Report",
            "summary": "Patient Population Summary Report",
            "analytics": "Analytics & Risk Assessment Report",
        }

        report = Report(
            report_type=report_type,
            title=title_map.get(report_type, f"{report_type.title()} Report"),
            content=content,
            date_from=date_from,
            date_to=date_to,
        )
        db.add(report)
        await db.flush()
        await db.refresh(report)

        return {
            "id": report.id,
            "report_type": report.report_type,
            "title": report.title,
            "content": report.content,
            "date_from": str(date_from) if date_from else None,
            "date_to": str(date_to) if date_to else None,
            "generated_at": report.generated_at.isoformat() if report.generated_at else None,
            "blocked": False,
            "security_scan": output_scan,
        }

    async def _gather_data(
        self, report_type: str, date_from: Optional[date], date_to: Optional[date], db: AsyncSession
    ) -> str:
        # Patient statistics
        patient_count = await db.scalar(select(func.count(Patient.id)))
        avg_risk = await db.scalar(select(func.avg(Patient.risk_score)))

        result = await db.execute(select(Patient))
        patients = result.scalars().all()

        condition_counts: dict[str, int] = {}
        for p in patients:
            if p.conditions:
                for c in p.conditions:
                    condition_counts[c] = condition_counts.get(c, 0) + 1

        high_risk = sum(1 for p in patients if p.risk_score and p.risk_score > 75)

        summary = f"""
Patient Population: {patient_count}
Average Risk Score: {avg_risk:.1f if avg_risk else 'N/A'}
High Risk Patients (>75): {high_risk}
Condition Distribution: {condition_counts}
"""

        if report_type == "compliance":
            # Security scan statistics
            scan_count = await db.scalar(select(func.count(SecurityLog.id)))
            block_count = await db.scalar(
                select(func.count(SecurityLog.id)).where(SecurityLog.final_verdict == "block")
            )
            summary += f"\nSecurity Scans: {scan_count}\nBlocked Requests: {block_count}"

        elif report_type == "analytics":
            # Agent run statistics
            agent_runs = await db.scalar(select(func.count(AgentRun.id)))
            summary += f"\nAgent Runs: {agent_runs}"

        return summary


report_service = ReportService()
