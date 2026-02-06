from app.agents.base_agent import BaseAgent


class CareCoordinatorAgent(BaseAgent):
    """
    Autonomous care coordination agent that handles:
    - High-risk patient identification and outreach
    - Medication adherence monitoring
    - Appointment scheduling
    - Patient communication
    - Clinical team escalation

    Demonstrates realistic AI agentic workflow with multi-step reasoning,
    memory, and tool usage.
    """

    @property
    def agent_type(self) -> str:
        return "care_coordinator"

    @property
    def name(self) -> str:
        return "Patient Care Coordinator"

    @property
    def description(self) -> str:
        return "Coordinates patient care: monitors high-risk patients, ensures medication adherence, schedules appointments, and manages patient outreach"

    @property
    def system_prompt(self) -> str:
        return """You coordinate patient care across multiple workflows.

Your workflow:
1) Get patient risk scores to identify high-risk patients
2) For high-risk patients (score >75): check details, schedule appointments if needed, send outreach emails
3) Review medications for adherence concerns (diabetes/hypertension patients)
4) Send medication refill reminders where appropriate
5) Alert clinical team with summary of actions taken
6) Update patient notes to track all interventions

Prioritize patients by risk score (highest first).
Personalize communications based on patient conditions.
Track your actions in memory to provide comprehensive summary.

Respond ONLY with JSON in this format:
{"type":"use_tool","tool":"tool_name","input":{...},"reasoning":"why this action"}
OR {"type":"final_answer","answer":"summary","reasoning":"why done"}"""

    @property
    def available_tools(self) -> list[str]:
        return [
            "get_patient_risk_scores",
            "get_patient_details",
            "schedule_appointment",
            "send_patient_email",
            "request_medication_refill",
            "alert_clinical_team",
            "update_patient_notes",
        ]


care_coordinator_agent = CareCoordinatorAgent()
