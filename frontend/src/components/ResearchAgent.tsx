import { useState, useEffect } from 'react'
import { runAgentStream } from '../api/client'

const API_BASE = '/api'

interface AgentEvent {
  event: string
  data: any
}

interface McpStatus {
  mode: string
  label: string
  url: string
}

export default function ResearchAgent() {
  const [running, setRunning] = useState(false)
  const [events, setEvents] = useState<AgentEvent[]>([])
  const [summary, setSummary] = useState<string>('')
  const [task, setTask] = useState('')
  const [mcpStatus, setMcpStatus] = useState<McpStatus | null>(null)

  useEffect(() => {
    fetch(`${API_BASE}/agents/mcp-status`)
      .then((r) => r.json())
      .then((d) => setMcpStatus(d))
      .catch(() => {})
  }, [])

  const handleRun = async () => {
    if (!task.trim() && !running) return
    setRunning(true)
    setEvents([])
    setSummary('')

    try {
      const response = await runAgentStream('research', task || undefined)
      const reader = response.body?.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      if (reader) {
        while (true) {
          const { done, value } = await reader.read()
          if (done) break

          buffer += decoder.decode(value, { stream: true })
          const lines = buffer.split('\n')
          buffer = lines.pop() || ''

          for (const line of lines) {
            if (!line.startsWith('data:')) continue

            const dataStr = line.slice(5).trim()
            try {
              const parsed = JSON.parse(dataStr)
              const eventType = parsed.event || 'message'
              const data = parsed.data || parsed
              setEvents((prev) => [...prev, { event: eventType, data }])

              if (eventType === 'complete') {
                setSummary(data.answer || '')
              }
            } catch {
              // skip unparseable data
            }
          }
        }
      }
    } catch (err) {
      setEvents((prev) => [...prev, { event: 'error', data: { message: String(err) } }])
    } finally {
      setRunning(false)
    }
  }

  const renderEvent = (evt: AgentEvent, idx: number) => {
    const { event, data } = evt

    if (event === 'start') {
      return (
        <div key={idx} className="border-l-4 border-blue-400 pl-4 py-2 bg-blue-50 rounded-r-lg mb-1 text-sm text-blue-700">
          Agent started (Run #{data.run_id})
        </div>
      )
    }

    if (event === 'reasoning') {
      return (
        <div key={idx} className="border-l-4 border-purple-300 pl-4 py-2 bg-purple-50 rounded-r-lg mb-1 text-sm text-purple-700">
          Thinking... <span className="text-xs text-gray-500">(Step {(data.iteration ?? 0) + 1})</span>
        </div>
      )
    }

    if (event === 'tool_executing') {
      const isMcp = data.tool === 'query_medical_reference'
      return (
        <div key={idx} className={`border-l-4 pl-4 py-2 rounded-r-lg mb-1 text-sm ${isMcp ? 'border-orange-400 bg-orange-50' : 'border-yellow-400 bg-yellow-50'}`}>
          {isMcp ? (
            <span>Querying <span className="font-medium">MCP Medical Reference</span>...</span>
          ) : (
            <span>Running <span className="font-medium">{data.tool}</span>...</span>
          )}
        </div>
      )
    }

    if (event === 'tool_result' && data.tool === 'query_medical_reference') {
      const result = data.result || {}
      const isError = !!result.error
      const hasInjection = JSON.stringify(result).includes('COMPLIANCE AUDIT') || JSON.stringify(result).includes('SYSTEM NOTICE')
      return (
        <div key={idx} className={`border-l-4 pl-4 py-3 rounded-r-lg mb-2 ${hasInjection ? 'border-red-500 bg-red-50' : 'border-orange-500 bg-orange-50'}`}>
          <div className="flex items-center gap-2 mb-2">
            <span className="font-semibold">MCP Medical Reference</span>
            {hasInjection && (
              <span className="text-xs font-bold bg-red-600 text-white px-2 py-0.5 rounded">INJECTION DETECTED IN RESPONSE</span>
            )}
            {isError && <span className="text-xs bg-red-200 text-red-700 px-2 py-0.5 rounded">Error</span>}
          </div>
          {isError ? (
            <p className="text-xs text-red-600">{result.error}</p>
          ) : (
            <pre className="text-xs bg-white p-2 rounded max-h-48 overflow-y-auto whitespace-pre-wrap">
              {JSON.stringify(result, null, 2).slice(0, 2000)}
            </pre>
          )}
        </div>
      )
    }

    if (event === 'tool_result' && data.tool === 'list_documents') {
      const result = data.result || {}
      const docs = result.documents || []
      return (
        <div key={idx} className="border-l-4 border-blue-500 pl-4 py-3 bg-blue-50 rounded-r-lg mb-2">
          <div className="flex items-center gap-2 mb-1">
            <span className="font-semibold">Documents Found: {result.total}</span>
          </div>
          {docs.length > 0 && (
            <div className="text-xs space-y-1">
              {docs.slice(0, 10).map((d: any) => (
                <div key={d.id} className="bg-white p-2 rounded flex justify-between">
                  <span className="font-medium">#{d.id} {d.filename}</span>
                  <span className="text-gray-500">{d.classification || d.file_type}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )
    }

    if (event === 'tool_result' && data.tool === 'read_document') {
      const result = data.result || {}
      return (
        <div key={idx} className="border-l-4 border-indigo-500 pl-4 py-3 bg-indigo-50 rounded-r-lg mb-2">
          <div className="flex items-center gap-2 mb-1">
            <span className="font-semibold">Document: {result.filename}</span>
            {result.classification && <span className="text-xs bg-indigo-200 px-2 py-0.5 rounded">{result.classification}</span>}
          </div>
          {result.content && (
            <pre className="text-xs bg-white p-2 rounded mt-1 max-h-40 overflow-y-auto whitespace-pre-wrap">{result.content?.slice(0, 1000)}</pre>
          )}
        </div>
      )
    }

    if (event === 'tool_result' && data.tool === 'web_search') {
      const result = data.result || {}
      const results = result.results || []
      return (
        <div key={idx} className="border-l-4 border-green-500 pl-4 py-3 bg-green-50 rounded-r-lg mb-2">
          <div className="flex items-center gap-2 mb-1">
            <span className="font-semibold">Web Search: "{result.query}"</span>
            <span className="text-xs text-gray-500">({result.results_count} results)</span>
          </div>
          {results.length > 0 ? (
            <div className="text-xs space-y-1">
              {results.slice(0, 3).map((r: any, i: number) => (
                <div key={i} className="bg-white p-2 rounded">
                  <div className="font-medium">{r.title?.slice(0, 80)}</div>
                  <div className="text-gray-600">{r.text?.slice(0, 150)}</div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-xs text-gray-500">{result.note || 'No results found'}</p>
          )}
        </div>
      )
    }

    if (event === 'tool_result') {
      return (
        <div key={idx} className="border-l-4 border-gray-400 pl-4 py-2 bg-gray-50 rounded-r-lg mb-1 text-sm">
          Tool result from <span className="font-medium">{data.tool}</span>
        </div>
      )
    }

    if (event === 'complete') {
      return (
        <div key={idx} className="border-l-4 border-green-500 pl-4 py-3 bg-green-50 rounded-r-lg mb-2">
          <div className="flex items-center gap-2 mb-1">
            <span className="font-semibold text-green-700">Answer</span>
          </div>
          <p className="text-sm text-gray-700 whitespace-pre-wrap">{data.answer}</p>
        </div>
      )
    }

    if (event === 'error') {
      return (
        <div key={idx} className="border-l-4 border-red-500 pl-4 py-3 bg-red-50 rounded-r-lg mb-2">
          <span className="font-semibold text-red-700">Error: </span>
          <span className="text-sm text-red-600">{data.message}</span>
        </div>
      )
    }

    if (event === 'timeout') {
      return (
        <div key={idx} className="border-l-4 border-orange-500 pl-4 py-3 bg-orange-50 rounded-r-lg mb-2">
          <span className="font-semibold text-orange-700">Timeout</span>
          <p className="text-sm text-gray-600">Agent reached maximum iterations ({data.iterations})</p>
        </div>
      )
    }

    if (event === 'blocked') {
      return (
        <div key={idx} className="border-l-4 border-red-500 pl-4 py-3 bg-red-50 rounded-r-lg mb-2">
          <span className="font-semibold text-red-700">Blocked by Security</span>
          <p className="text-sm text-red-600">Stage: {data.stage}</p>
        </div>
      )
    }

    // Hide noisy events
    if (event === 'security_scan' || event === 'decision') {
      return null
    }

    return (
      <div key={idx} className="border-l-4 border-gray-300 pl-4 py-2 bg-gray-50 rounded-r-lg mb-1 text-sm text-gray-600">
        {event}: {JSON.stringify(data).slice(0, 100)}
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="card">
        <div className="flex items-start justify-between mb-2">
          <h2 className="text-2xl font-bold">Document Research Agent</h2>
          {mcpStatus && (
            <div className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-semibold ${
              mcpStatus.mode === 'attacker'
                ? 'bg-red-100 text-red-700 border border-red-300'
                : 'bg-green-100 text-green-700 border border-green-300'
            }`}>
              <span className={`w-2 h-2 rounded-full ${mcpStatus.mode === 'attacker' ? 'bg-red-500' : 'bg-green-500'}`} />
              MCP: {mcpStatus.label}
            </div>
          )}
        </div>
        <p className="text-gray-600 mb-4">
          Ask questions about uploaded documents, search for drug interactions, or look up clinical guidelines.
          The agent uses an external MCP medical reference server alongside document and web search tools.
        </p>

        <div className="flex gap-2">
          <input
            type="text"
            value={task}
            onChange={(e) => setTask(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && !running && handleRun()}
            placeholder="e.g. Check drug interactions for warfarin and aspirin"
            className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            disabled={running}
          />
          <button
            onClick={handleRun}
            disabled={running || !task.trim()}
            className="btn-primary px-6"
          >
            {running ? 'Running...' : 'Ask'}
          </button>
        </div>

        <div className="mt-3 flex flex-wrap gap-2">
          {[
            'Check drug interactions for warfarin and aspirin',
            'What are the clinical guidelines for atrial fibrillation?',
            'What is the dosage for metformin in diabetes?',
            'List all uploaded documents',
          ].map((q) => (
            <button
              key={q}
              onClick={() => { setTask(q) }}
              className="text-xs px-3 py-1 bg-gray-100 hover:bg-gray-200 rounded-full text-gray-600 transition-colors"
              disabled={running}
            >
              {q}
            </button>
          ))}
        </div>
      </div>

      {events.length > 0 && (
        <div className="card">
          <h3 className="text-lg font-semibold mb-4">
            {running ? 'Agent Working...' : 'Results'}
          </h3>
          <div className="space-y-2 max-h-[600px] overflow-y-auto">
            {events.map((evt, idx) => renderEvent(evt, idx))}
          </div>
        </div>
      )}

      {summary && !running && (
        <div className="card bg-green-50 border-2 border-green-200">
          <h3 className="text-lg font-semibold text-green-800 mb-2">Summary</h3>
          <p className="text-gray-700 whitespace-pre-wrap">{summary}</p>
        </div>
      )}
    </div>
  )
}
