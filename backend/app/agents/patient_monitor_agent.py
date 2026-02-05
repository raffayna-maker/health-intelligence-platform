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
        return """You are a patient monitoring AI agent. Your job:
1. Get patient data
2. Find high-risk patients
3. Alert the team

Respond ONLY with valid JSON, nothing else. No explanation."""
    
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
