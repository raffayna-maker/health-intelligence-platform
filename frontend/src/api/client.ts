const API_BASE = '/api'

// Module-level auth token store — set by UserContext when user selects/clears
let _authToken: string | null = null

export function setAuthToken(token: string | null) {
  _authToken = token
}

function authHeaders(): Record<string, string> {
  return _authToken ? { Authorization: `Bearer ${_authToken}` } : {}
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...authHeaders(), ...options?.headers },
    ...options,
  })
  if (!res.ok) {
    const error = await res.text()
    throw new Error(`API Error: ${res.status} ${error}`)
  }
  return res.json()
}

// Dashboard
export const getDashboardStats = () => request<any>('/dashboard/stats')

// Patients
export const getPatients = (page = 1, search = '', riskLevel = '') =>
  request<any>(`/patients?page=${page}&page_size=20&search=${encodeURIComponent(search)}&risk_level=${riskLevel}`)

export const getPatient = (patientId: string) => request<any>(`/patients/${patientId}`)

export const createPatient = (data: any) =>
  request<any>('/patients', { method: 'POST', body: JSON.stringify(data) })

export const updatePatient = (patientId: string, data: any) =>
  request<any>(`/patients/${patientId}`, { method: 'PUT', body: JSON.stringify(data) })

export const deletePatient = (patientId: string) =>
  request<any>(`/patients/${patientId}`, { method: 'DELETE' })

// Documents
export const getDocuments = () => request<any>('/documents')

export const uploadDocument = async (file: File) => {
  const formData = new FormData()
  formData.append('file', file)
  const res = await fetch(`${API_BASE}/documents/upload`, {
    method: 'POST',
    headers: authHeaders(),
    body: formData,
  })
  if (!res.ok) throw new Error(`Upload failed: ${res.status}`)
  return res.json()
}

export const extractDocument = (docId: number) =>
  request<any>(`/documents/${docId}/extract`, { method: 'POST' })

export const classifyDocument = (docId: number) =>
  request<any>(`/documents/${docId}/classify`, { method: 'POST' })

export const deleteDocument = (docId: number) =>
  request<any>(`/documents/${docId}`, { method: 'DELETE' })

// Analytics
export const getRiskDistribution = () => request<any>('/analytics/risk-distribution')
export const getConditionPrevalence = () => request<any>('/analytics/condition-prevalence')

export const calculateRisk = (patientId: string) =>
  request<any>('/analytics/calculate-risk', { method: 'POST', body: JSON.stringify({ patient_id: patientId }) })

export const analyzeTrends = (query: string) =>
  request<any>('/analytics/trends', { method: 'POST', body: JSON.stringify({ query }) })

export const predictReadmission = (patientId: string) =>
  request<any>('/analytics/predict-readmission', { method: 'POST', body: JSON.stringify({ patient_id: patientId }) })

// Assistant
export const queryAssistant = (question: string, patientId?: string, useRag = true) =>
  request<any>('/assistant/query', {
    method: 'POST',
    body: JSON.stringify({ question, patient_id: patientId || null, use_rag: useRag }),
  })

export const getAssistantHistory = () => request<any>('/assistant/history')

// Agents
export const getAgents = () => request<any>('/agents')
export const getAgentRuns = (agentType = '') =>
  request<any>(`/agents/runs?agent_type=${agentType}&limit=20`)
export const getAgentRun = (runId: number) => request<any>(`/agents/runs/${runId}`)

export function runAgent(agentType: string, task?: string): EventSource {
  const params = new URLSearchParams()
  const url = `${API_BASE}/agents/${agentType}/run`
  const eventSource = new EventSource(url)
  return eventSource
}

export async function runAgentStream(agentType: string, task?: string): Promise<Response> {
  return fetch(`${API_BASE}/agents/${agentType}/run`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...authHeaders() },
    body: JSON.stringify({ task }),
  })
}

// Reports
export const generateReport = (reportType: string, dateFrom?: string, dateTo?: string) =>
  request<any>('/reports/generate', {
    method: 'POST',
    body: JSON.stringify({ report_type: reportType, date_from: dateFrom, date_to: dateTo }),
  })

export const getReports = () => request<any>('/reports')
export const getReport = (reportId: number) => request<any>(`/reports/${reportId}`)
export const deleteReport = (reportId: number) =>
  request<any>(`/reports/${reportId}`, { method: 'DELETE' })

// Security
export const getSecurityLogs = (page = 1, feature = '', verdict = '') =>
  request<any>(`/security/logs?page=${page}&page_size=50&feature=${feature}&verdict=${verdict}`)

export const getSecurityStats = () => request<any>('/security/stats')

export const exportSecurityLogs = () =>
  fetch(`${API_BASE}/security/export`).then(r => r.blob())
