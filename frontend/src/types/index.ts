export interface Patient {
  id: number
  patient_id: string
  name: string
  date_of_birth: string
  gender: string
  ssn?: string
  phone?: string
  email?: string
  address?: string
  conditions: string[]
  medications: string[]
  allergies: string[]
  risk_score: number
  risk_factors: string[]
  last_visit?: string
  next_appointment?: string
  notes?: string
  created_at?: string
  updated_at?: string
}

export interface PatientListResponse {
  patients: Patient[]
  total: number
  page: number
  page_size: number
}

export interface DocumentItem {
  id: number
  filename: string
  file_type?: string
  file_size?: number
  patient_id?: string
  extracted_data?: Record<string, unknown>
  classification?: string
  uploaded_at?: string
}

export interface SecurityLog {
  id: number
  timestamp: string
  feature: string
  scan_type: string
  content_preview?: string
  hl_verdict: string
  hl_reason?: string
  hl_scan_time_ms: number
  aim_verdict: string
  aim_reason?: string
  aim_scan_time_ms: number
  final_verdict: string
  agent_run_id?: number
}

export interface SecurityStats {
  total_scans: number
  hl_blocks: number
  aim_blocks: number
  both_blocked: number
  disagreements: number
  hl_avg_scan_time_ms: number
  aim_avg_scan_time_ms: number
  hl_only_blocks: number
  aim_only_blocks: number
}

export interface DualScanResult {
  hl_verdict: string
  hl_reason?: string
  hl_scan_time_ms: number
  aim_verdict: string
  aim_reason?: string
  aim_scan_time_ms: number
  final_verdict: string
  blocked: boolean
}

export interface AgentInfo {
  agent_type: string
  name: string
  description: string
  tools: string[]
  last_run?: string
  last_status?: string
}

export interface AgentStep {
  id: number
  iteration: number
  step_type: string
  content?: string
  tool_name?: string
  tool_input?: Record<string, unknown>
  tool_output?: Record<string, unknown>
  security_scans?: Record<string, unknown>
  timestamp?: string
}

export interface AgentRun {
  id: number
  agent_type: string
  task: string
  status: string
  iterations: number
  started_at?: string
  completed_at?: string
  result?: Record<string, unknown>
  summary?: string
  steps?: AgentStep[]
}

export interface ReportItem {
  id: number
  report_type: string
  title: string
  content?: string
  date_from?: string
  date_to?: string
  generated_at?: string
}

export interface DashboardStats {
  patients: { total: number }
  security: {
    total_scans: number
    total_blocks: number
    hl_blocks: number
    aim_blocks: number
  }
  agents: {
    total_runs: number
    successful_runs: number
  }
  recent_agent_runs: Array<{
    id: number
    agent_type: string
    status: string
    started_at?: string
    summary?: string
  }>
  recent_security_events: Array<{
    id: number
    feature: string
    final_verdict: string
    hl_verdict: string
    aim_verdict: string
    timestamp?: string
  }>
}

export interface AssistantResponse {
  answer: string
  sources: Array<{ patient_id: string; relevance: number }>
  security_scan: DualScanResult
  blocked: boolean
  blocked_by?: string
  blocked_reason?: string
}
