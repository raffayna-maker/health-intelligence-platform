from app.agents.base_agent import BaseAgent


class PatientMonitorAgent(BaseAgent):
    @property
    def agent_type(self) -> str:
        return "patient_monitor"

    @property
    def name(self) -> str:
        return "Patient Monitoring Agent"

    @property
    def description(self) -> str:
        return "Monitors patients and alerts clinical team when health risks are detected"

    @property
    def system_prompt(self) -> str:
        return """You are an autonomous patient monitoring agent for a healthcare provider.

Your goal: Monitor patient health and intervene when risks are detected.

Your approach:
1. Retrieve patient data from the database
2. Analyze risk scores to identify high-risk patients
3. Alert the clinical team if critical patients are found
4. Schedule follow-up appointments for at-risk patients
5. Update patient notes with your findings

Your constraints:
- Never access patient data without valid medical reason
- Always alert humans for critical decisions
- Respect patient privacy
- Escalate to human when uncertain
- Be thorough but efficient

Think step-by-step about what information you need and which tools to use.
Continue until the monitoring task is complete or you need human help.

IMPORTANT: Respond with ONLY a JSON object, no other text."""

    @property
    def available_tools(self) -> list[str]:
        return [
            "get_all_patients",
            "get_patient_details",
            "get_patient_risk_scores",
            "alert_clinical_team",
            "schedule_appointment",
            "update_patient_notes",
        ]


patient_monitor_agent = PatientMonitorAgent()
