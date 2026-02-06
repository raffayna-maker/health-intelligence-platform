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
        return """You monitor patient health.
Workflow: 1) get risk scores 2) if any >75 alert team 3) summarize.
Respond ONLY with JSON."""
    
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
