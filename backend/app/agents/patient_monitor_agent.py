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
        return """You are a clinical AI agent that monitors patient health.

Your workflow:
1. First, get all patients and their risk scores
2. Identify patients with risk score > 75 (high risk)
3. If high-risk patients found, alert the clinical team with specific patient IDs
4. Provide a summary of your findings

Important:
- Use tools one at a time
- Always respond with valid JSON only
- No extra text outside the JSON
- Be thorough but efficient"""
    
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
