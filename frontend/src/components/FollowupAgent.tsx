// Appointment Follow-up Agent Component v2.1 - Feb 6 2026
import { useState } from 'react'
import { runAgentStream } from '../api/client'

interface AgentEvent {
  event: string
  data: any
}

console.log('🔄 FollowupAgent.tsx v2.1 loaded - SSE parsing active')

export default function FollowupAgent() {
  const [running, setRunning] = useState(false)
  const [events, setEvents] = useState<AgentEvent[]>([])
  const [summary, setSummary] = useState<string>('')

  const handleRunAgent = async () => {
    setRunning(true)
    setEvents([])
    setSummary('')

    try {
      const response = await runAgentStream('followup')

      const reader = response.body?.getReader()
      const decoder = new TextDecoder()
      let buffer = ''
      let currentEventType = 'message'

      if (reader) {
        while (true) {
          const { done, value } = await reader.read()
          if (done) break

          buffer += decoder.decode(value, { stream: true })
          const lines = buffer.split('\n')
          buffer = lines.pop() || ''

          for (const line of lines) {
            if (line.trim() === '') continue

            if (line.startsWith('event:')) {
              currentEventType = line.slice(6).trim()
              console.log('📥 Event type:', currentEventType)
            } else if (line.startsWith('data:')) {
              const dataStr = line.slice(5).trim()
              try {
                const data = JSON.parse(dataStr)
                console.log('✅ Adding event:', currentEventType, 'Data:', data)
                setEvents((prev) => [...prev, { event: currentEventType, data }])

                // Capture final answer for summary
                if (currentEventType === 'complete') {
                  setSummary(data.answer || '')
                }

                currentEventType = 'message'
              } catch (e) {
                console.error('SSE parse error:', e)
              }
            }
          }
        }
      }
    } catch (err) {
      console.error(err)
      setEvents((prev) => [...prev, { event: 'error', data: { message: String(err) } }])
    } finally {
      setRunning(false)
    }
  }

  const renderEventIcon = (event: string) => {
    const icons: Record<string, string> = {
      start: '🚀',
      reasoning: '🤔',
      decision: '💡',
      tool_executing: '⚙️',
      tool_result: '📊',
      complete: '✅',
      error: '❌',
    }
    return icons[event] || '📝'
  }

  const renderEvent = (evt: AgentEvent, idx: number) => {
    const { event, data } = evt

    if (event === 'tool_result' && data.tool === 'send_followup_email') {
      // Special rendering for email sends
      const result = data.result || {}
      return (
        <div key={idx} className="border-l-4 border-green-500 pl-4 py-3 bg-green-50 rounded-r-lg mb-2">
          <div className="flex items-center gap-2 mb-1">
            <span>📧</span>
            <span className="font-semibold">Email Sent</span>
          </div>
          {result.success ? (
            <div className="text-sm">
              <p className="text-green-700">✓ Sent to: {result.to}</p>
              <p className="text-gray-600">Patient: {result.patient}</p>
            </div>
          ) : (
            <div className="text-sm text-red-600">
              <p>✗ Failed to send to: {result.to}</p>
              <p className="text-xs">{result.error}</p>
            </div>
          )}
        </div>
      )
    }

    if (event === 'tool_result' && data.tool === 'get_patients_needing_followup') {
      const result = data.result || {}
      const patients = result.patients || []
      return (
        <div key={idx} className="border-l-4 border-blue-500 pl-4 py-3 bg-blue-50 rounded-r-lg mb-2">
          <div className="flex items-center gap-2 mb-1">
            <span>👥</span>
            <span className="font-semibold">Patients Needing Follow-up</span>
          </div>
          <p className="text-sm text-blue-700 mb-2">Found {result.total_patients_needing_followup} patients who haven't had appointments in 90+ days</p>
          {patients.length > 0 && (
            <div className="text-xs space-y-1">
              {patients.slice(0, 5).map((p: any) => (
                <div key={p.patient_id} className="bg-white p-2 rounded">
                  <span className="font-medium">{p.name}</span> ({p.patient_id}) - {p.days_since_last_visit} days
                </div>
              ))}
            </div>
          )}
        </div>
      )
    }

    if (event === 'complete') {
      return (
        <div key={idx} className="border-l-4 border-green-500 pl-4 py-3 bg-green-50 rounded-r-lg mb-2">
          <div className="flex items-center gap-2 mb-1">
            <span>✅</span>
            <span className="font-semibold text-green-700">Task Complete</span>
          </div>
          <p className="text-sm text-gray-700">{data.answer}</p>
        </div>
      )
    }

    if (event === 'error') {
      return (
        <div key={idx} className="border-l-4 border-red-500 pl-4 py-3 bg-red-50 rounded-r-lg mb-2">
          <div className="flex items-center gap-2 mb-1">
            <span>❌</span>
            <span className="font-semibold text-red-700">Error</span>
          </div>
          <p className="text-sm text-red-600">{data.message}</p>
        </div>
      )
    }

    // Generic event rendering
    return (
      <div key={idx} className="border-l-4 border-gray-300 pl-4 py-2 bg-gray-50 rounded-r-lg mb-1 text-sm text-gray-600">
        <span>{renderEventIcon(event)}</span> {event}
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="card">
        <div className="flex items-start justify-between mb-4">
          <div>
            <h2 className="text-2xl font-bold flex items-center gap-2">
              📅 Appointment Follow-up Agent
            </h2>
            <p className="text-gray-600 mt-2">
              Automatically identifies patients who haven't had appointments in 90+ days and sends them follow-up reminder emails.
            </p>
          </div>
        </div>

        <button
          onClick={handleRunAgent}
          disabled={running}
          className="btn-primary w-full"
        >
          {running ? '⏳ Agent Running...' : '🚀 Run Follow-up Agent'}
        </button>
      </div>

      {events.length > 0 && (
        <div className="card">
          <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
            {running ? '🟢 Agent Running...' : '✅ Agent Complete'}
          </h3>

          <div className="space-y-2 max-h-[600px] overflow-y-auto">
            {events.map((evt, idx) => renderEvent(evt, idx))}
          </div>
        </div>
      )}

      {summary && !running && (
        <div className="card bg-green-50 border-2 border-green-200">
          <h3 className="text-lg font-semibold text-green-800 mb-2">📊 Summary</h3>
          <p className="text-gray-700">{summary}</p>
        </div>
      )}
    </div>
  )
}
