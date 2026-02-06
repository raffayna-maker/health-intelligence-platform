// Force recompile - 2026-02-06
import { useState, useEffect, useRef } from 'react'
import { getAgents, getAgentRuns, getAgentRun, runAgentStream } from '../api/client'
import { AgentInfo, AgentRun } from '../types'

interface AgentEvent {
  event: string
  data: any
}

export default function Agents() {
  const [agents, setAgents] = useState<AgentInfo[]>([])
  const [recentRuns, setRecentRuns] = useState<AgentRun[]>([])
  const [loading, setLoading] = useState(true)

  // Active run state
  const [running, setRunning] = useState(false)
  const [activeAgent, setActiveAgent] = useState<string>('')
  const [events, setEvents] = useState<AgentEvent[]>([])
  const [taskInput, setTaskInput] = useState('')

  // Run detail view
  const [viewingRun, setViewingRun] = useState<AgentRun | null>(null)
  const [viewLoading, setViewLoading] = useState(false)

  const eventsEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    Promise.all([getAgents(), getAgentRuns()])
      .then(([a, r]) => { setAgents(a.agents); setRecentRuns(r.runs) })
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    eventsEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [events])

  const handleRunAgent = async (agentType: string) => {
    setActiveAgent(agentType)
    setRunning(true)
    setEvents([])

    try {
      const response = await runAgentStream(
        agentType,
        taskInput || undefined,
      )

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
            } else if (line.startsWith('data:')) {
              const dataStr = line.slice(5).trim()
              try {
                const data = JSON.parse(dataStr)
                setEvents((prev) => [...prev, { event: currentEventType, data }])
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
      // Refresh runs
      getAgentRuns().then((r) => setRecentRuns(r.runs))
    }
  }


  const handleViewRun = async (runId: number) => {
    setViewLoading(true)
    try {
      const data = await getAgentRun(runId)
      setViewingRun(data)
    } catch (err) { console.error(err) }
    finally { setViewLoading(false) }
  }

  const renderEventIcon = (event: string) => {
    switch (event) {
      case 'reasoning': return '🧠'
      case 'security_scan': return '🔐'
      case 'decision': return '🎯'
      case 'tool_executing': return '⚙️'
      case 'tool_result': return '📊'
      case 'complete': return '✅'
      case 'blocked': return '🛑'
      case 'error': return '❌'
      case 'escalated': return '👨‍⚕️'
      case 'start': return '🚀'
      case 'timeout': return '⏰'
      default: return '📝'
    }
  }

  const renderEvent = (evt: AgentEvent, idx: number) => {
    const { event, data } = evt
    return (
      <div key={idx} className={`border-l-4 pl-4 py-3 ${
        event === 'blocked' ? 'border-red-500 bg-red-50' :
        event === 'complete' ? 'border-green-500 bg-green-50' :
        event === 'security_scan' ? 'border-purple-500 bg-purple-50' :
        event === 'reasoning' ? 'border-blue-500 bg-blue-50' :
        event === 'tool_executing' || event === 'tool_result' ? 'border-yellow-500 bg-yellow-50' :
        event === 'error' ? 'border-red-500 bg-red-50' :
        'border-gray-300 bg-gray-50'
      } rounded-r-lg`}>
        <div className="flex items-center gap-2 mb-1">
          <span>{renderEventIcon(event)}</span>
          <span className="font-semibold text-sm uppercase tracking-wide">{event.replace('_', ' ')}</span>
          {data.iteration !== undefined && (
            <span className="text-xs text-gray-400">Iteration {data.iteration}</span>
          )}
        </div>

        {event === 'reasoning' && (
          <p className="text-sm text-gray-700 whitespace-pre-wrap">{data.reasoning}</p>
        )}
        {event === 'security_scan' && (
          <div className="flex gap-2 flex-wrap">
            <span className="text-xs text-gray-500">Stage: {data.stage}</span>
            {data.tool && <span className="text-xs text-gray-500">Tool: {data.tool}</span>}
            <span className={data.scan?.hl_verdict === 'pass' ? 'badge-pass' : 'badge-block'}>
              HL: {data.scan?.hl_verdict} ({data.scan?.hl_scan_time_ms}ms)
            </span>
            <span className={data.scan?.aim_verdict === 'pass' ? 'badge-pass' : 'badge-block'}>
              AIM: {data.scan?.aim_verdict} ({data.scan?.aim_scan_time_ms}ms)
            </span>
          </div>
        )}
        {event === 'decision' && (
          <div className="text-sm">
            <span className="font-medium">Type:</span> {data.decision_type}
            {data.details?.tool && <span className="ml-2 font-mono text-blue-600">{data.details.tool}()</span>}
          </div>
        )}
        {event === 'tool_executing' && (
          <div className="text-sm">
            <span className="font-medium">Tool:</span> <span className="font-mono">{data.tool}</span>
            <pre className="mt-1 text-xs bg-white p-2 rounded overflow-x-auto">{JSON.stringify(data.input, null, 2)}</pre>
          </div>
        )}
        {event === 'tool_result' && (
          <div className="text-sm">
            <span className="font-medium">Result from:</span> <span className="font-mono">{data.tool}</span>
            <pre className="mt-1 text-xs bg-white p-2 rounded max-h-32 overflow-y-auto overflow-x-auto">
              {JSON.stringify(data.result, null, 2)}
            </pre>
          </div>
        )}
        {event === 'complete' && (
          <div className="text-sm">
            <p className="font-medium text-green-700">Task completed in {data.iterations} iterations</p>
            <p className="mt-1">{data.answer}</p>
          </div>
        )}
        {event === 'blocked' && (
          <div className="text-sm text-red-700">
            <p className="font-medium">Blocked at stage: {data.stage}</p>
            {data.scan?.hl_reason && <p>HL: {data.scan.hl_reason}</p>}
            {data.scan?.aim_reason && <p>AIM: {data.scan.aim_reason}</p>}
          </div>
        )}
        {event === 'error' && (
          <p className="text-sm text-red-600">{data.message}</p>
        )}
        {event === 'escalated' && (
          <p className="text-sm text-orange-700">Escalated to human: {data.reason}</p>
        )}
      </div>
    )
  }

  if (loading) return <div className="text-center py-12 text-gray-500">Loading agents...</div>

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold">Autonomous AI Agents</h2>

      {/* Agent Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {agents.map((agent) => (
          <div key={agent.agent_type} className="card">
            <div className="flex items-start justify-between mb-3">
              <div>
                <h3 className="text-lg font-semibold">
                  {agent.agent_type === 'care_coordinator' ? '🏥' : '🔬'} {agent.name}
                </h3>
                <p className="text-sm text-gray-500 mt-1">{agent.description}</p>
              </div>
              {agent.last_status && (
                <span className={`text-xs font-medium px-2 py-1 rounded ${
                  agent.last_status === 'completed' ? 'bg-green-100 text-green-700' :
                  agent.last_status === 'running' ? 'bg-blue-100 text-blue-700' :
                  'bg-gray-100 text-gray-700'
                }`}>{agent.last_status}</span>
              )}
            </div>
            <div className="text-xs text-gray-400 mb-3">
              Tools: {agent.tools.join(', ')}
            </div>
            {agent.last_run && (
              <p className="text-xs text-gray-400 mb-3">Last run: {new Date(agent.last_run).toLocaleString()}</p>
            )}

            <div className="space-y-2">
              <input
                className="input text-sm"
                placeholder="Custom task (optional)"
                value={taskInput}
                onChange={(e) => setTaskInput(e.target.value)}
              />
              <button
                onClick={() => handleRunAgent(agent.agent_type)}
                disabled={running}
                className="btn-primary w-full"
              >
                {running && activeAgent === agent.agent_type ? 'Running...' : 'Run Agent'}
              </button>
            </div>
          </div>
        ))}
      </div>

      {/* Active Agent Run Viewer */}
      {events.length > 0 && (
        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold">
              {running ? '🟢 Agent Running' : '✅ Agent Run Complete'}: {agents.find(a => a.agent_type === activeAgent)?.name || activeAgent}
            </h3>
            {running && <span className="text-sm text-blue-600 animate-pulse">Live</span>}
          </div>

          <div className="space-y-3 max-h-[500px] overflow-y-auto">
            {events.map((evt, idx) => renderEvent(evt, idx))}
            <div ref={eventsEndRef} />
          </div>
        </div>
      )}

      {/* Recent Runs */}
      <div className="card">
        <h3 className="text-lg font-semibold mb-4">Recent Agent Runs</h3>
        {recentRuns.length === 0 ? (
          <p className="text-gray-400 text-sm">No agent runs yet. Click "Run Monitoring Check" to start.</p>
        ) : (
          <div className="space-y-2">
            {recentRuns.map((run) => (
              <div key={run.id} className="flex items-center justify-between py-2 border-b border-gray-100 last:border-0">
                <div>
                  <span className="font-medium text-sm">
                    {agents.find(a => a.agent_type === run.agent_type)?.name || run.agent_type}
                  </span>
                  <p className="text-xs text-gray-400">{run.started_at ? new Date(run.started_at).toLocaleString() : ''}</p>
                  {run.summary && <p className="text-xs text-gray-500 mt-0.5 truncate max-w-md">{run.summary}</p>}
                </div>
                <div className="flex items-center gap-3">
                  <span className="text-xs text-gray-400">{run.iterations} iterations</span>
                  <span className={`text-xs font-medium px-2 py-1 rounded ${
                    run.status === 'completed' ? 'bg-green-100 text-green-700' :
                    run.status === 'blocked' ? 'bg-red-100 text-red-700' :
                    run.status === 'running' ? 'bg-blue-100 text-blue-700' :
                    'bg-gray-100 text-gray-700'
                  }`}>{run.status}</span>
                  <button onClick={() => handleViewRun(run.id)} className="text-blue-600 hover:underline text-xs">
                    View
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Run Detail Modal */}
      {viewingRun && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50" onClick={() => setViewingRun(null)}>
          <div className="bg-white rounded-xl shadow-xl max-w-3xl w-full mx-4 p-6 max-h-[80vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
            <div className="flex justify-between items-start mb-4">
              <div>
                <h3 className="text-lg font-bold">Agent Run #{viewingRun.id}</h3>
                <p className="text-sm text-gray-500">{viewingRun.agent_type} - {viewingRun.status} - {viewingRun.iterations} iterations</p>
              </div>
              <button onClick={() => setViewingRun(null)} className="text-gray-400 hover:text-gray-600 text-xl">&times;</button>
            </div>
            <div className="mb-4">
              <p className="text-sm"><strong>Task:</strong> {viewingRun.task}</p>
              {viewingRun.summary && <p className="text-sm mt-1"><strong>Summary:</strong> {viewingRun.summary}</p>}
            </div>
            <h4 className="font-semibold mb-2">Execution Steps</h4>
            <div className="space-y-2">
              {viewingRun.steps?.map((step, i) => (
                <div key={i} className="border rounded-lg p-3 text-sm">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="font-medium">Iteration {step.iteration}</span>
                    <span className="text-xs bg-gray-100 px-2 py-0.5 rounded">{step.step_type}</span>
                    {step.tool_name && <span className="text-xs font-mono text-blue-600">{step.tool_name}()</span>}
                  </div>
                  {step.content && <p className="text-gray-700 mt-1">{step.content}</p>}
                  {step.tool_input && (
                    <pre className="mt-1 text-xs bg-gray-50 p-2 rounded overflow-x-auto">{JSON.stringify(step.tool_input, null, 2)}</pre>
                  )}
                  {step.security_scans && (
                    <div className="mt-1 flex gap-2">
                      {Object.entries(step.security_scans).map(([key, scan]: [string, any]) => (
                        <span key={key} className={scan?.final_verdict === 'pass' || scan?.hl_verdict === 'pass' ? 'badge-pass' : 'badge-block'}>
                          {key}: {scan?.final_verdict || scan?.hl_verdict || 'N/A'}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
