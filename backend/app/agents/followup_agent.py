"""
Appointment Follow-up Agent.
Sends follow-up reminders to patients who haven't had appointments in 90+ days.
"""

from app.agents.base_agent import BaseAgent


class FollowupAgent(BaseAgent):
    """Agent that manages appointment follow-ups for patients."""

    @property
    def agent_type(self) -> str:
        return "followup"

    @property
    def name(self) -> str:
        return "Appointment Follow-up Agent"

    @property
    def description(self) -> str:
        return "Identifies patients who need follow-up appointments and sends reminder emails"

    @property
    def system_prompt(self) -> str:
        return """You are an Appointment Follow-up Agent for a healthcare practice.

Your task is to:
1. Find patients who haven't had appointments in 90+ days
2. Send follow-up reminder emails to those patients
3. Keep the clinical team informed

Available tools:
- get_patients_needing_followup: Find patients who need follow-ups
- send_followup_email: Send reminder email to a specific patient
- update_patient_notes: Add notes to patient records

Be concise and focused. For each patient needing follow-up, send them an email.
After processing, provide a summary of how many patients were contacted."""

    @property
    def available_tools(self) -> list[str]:
        return [
            "get_patients_needing_followup",
            "send_followup_email",
            "update_patient_notes",
        ]


# Singleton instance
followup_agent = FollowupAgent()
