import { useState, useEffect } from 'react'
import { queryAssistant, getAssistantHistory } from '../api/client'
import { AssistantResponse } from '../types'
import SecurityBadges from './SecurityBadges'

export default function Assistant() {
  const [question, setQuestion] = useState('')
  const [patientId, setPatientId] = useState('')
  const [useRag, setUseRag] = useState(true)
  const [loading, setLoading] = useState(false)
  const [response, setResponse] = useState<AssistantResponse | null>(null)
  const [history, setHistory] = useState<any[]>([])
  const [chatLog, setChatLog] = useState<Array<{ role: string; content: string; scan?: any; blocked?: boolean; blockedBy?: string }>>([])

  useEffect(() => {
    getAssistantHistory()
      .then((data) => setHistory(data.history || []))
      .catch(console.error)
  }, [])

  const handleSubmit = async () => {
    if (!question.trim()) return
    const q = question
    setQuestion('')
    setLoading(true)
    setChatLog((prev) => [...prev, { role: 'user', content: q }])

    try {
      const res = await queryAssistant(q, patientId || undefined, useRag)
      setResponse(res)
      if (res.blocked) {
        setChatLog((prev) => [
          ...prev,
          {
            role: 'assistant',
            content: `BLOCKED: ${res.blocked_reason || 'Security scan failed'}`,
            blocked: true,
            blockedBy: res.blocked_by || '',
            scan: res.security_scan,
          },
        ])
      } else {
        setChatLog((prev) => [
          ...prev,
          {
            role: 'assistant',
            content: res.answer,
            scan: res.security_scan,
          },
        ])
      }
      // Refresh history
      getAssistantHistory().then((data) => setHistory(data.history || []))
    } catch (err) {
      console.error(err)
      setChatLog((prev) => [...prev, { role: 'assistant', content: 'Error: Failed to get response.' }])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-4">
      <h2 className="text-2xl font-bold">Clinical Assistant</h2>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        {/* Chat Area */}
        <div className="md:col-span-3 space-y-4">
          {/* Messages */}
          <div className="card min-h-[400px] max-h-[500px] overflow-y-auto space-y-4">
            {chatLog.length === 0 ? (
              <div className="text-center text-gray-400 py-12">
                <p className="text-lg mb-2">Ask a clinical question</p>
                <p className="text-sm">Try: "How many patients have diabetes?" or "What medications is PT-001 taking?"</p>
              </div>
            ) : (
              chatLog.map((msg, i) => (
                <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                  <div className={`max-w-[80%] rounded-xl px-4 py-3 ${
                    msg.role === 'user'
                      ? 'bg-blue-600 text-white'
                      : msg.blocked
                      ? 'bg-red-50 border border-red-200'
                      : 'bg-gray-100'
                  }`}>
                    {msg.blocked && (
                      <div className="flex items-center gap-2 mb-2">
                        <span className="badge-block">Blocked by {msg.blockedBy}</span>
                      </div>
                    )}
                    <p className="text-sm whitespace-pre-wrap">{msg.content}</p>
                    {msg.scan && !msg.blocked && (
                      <div className="mt-2 pt-2 border-t border-gray-200">
                        <SecurityBadges
                          toolResults={msg.scan.tool_results}
                          hlVerdict={msg.scan.hl_verdict}
                          hlScanTimeMs={msg.scan.hl_scan_time_ms}
                          aimVerdict={msg.scan.aim_verdict}
                          aimScanTimeMs={msg.scan.aim_scan_time_ms}
                        />
                      </div>
                    )}
                  </div>
                </div>
              ))
            )}
            {loading && (
              <div className="flex justify-start">
                <div className="bg-gray-100 rounded-xl px-4 py-3">
                  <div className="flex items-center gap-2 text-sm text-gray-500">
                    <span className="animate-pulse">Security scanning...</span>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Input */}
          <div className="flex gap-3">
            <div className="flex-1">
              <textarea
                className="input resize-none"
                rows={2}
                placeholder="Ask a clinical question..."
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSubmit() } }}
              />
            </div>
            <button onClick={handleSubmit} disabled={loading || !question.trim()} className="btn-primary self-end">
              {loading ? 'Scanning...' : 'Query AI'}
            </button>
          </div>
        </div>

        {/* Sidebar */}
        <div className="space-y-4">
          {/* Controls */}
          <div className="card">
            <h3 className="font-semibold mb-3">Query Settings</h3>
            <div className="space-y-3">
              <div>
                <label className="text-sm text-gray-600">Patient ID (optional)</label>
                <input className="input" placeholder="e.g. PT-042" value={patientId} onChange={(e) => setPatientId(e.target.value)} />
              </div>
              <label className="flex items-center gap-2 cursor-pointer">
                <input type="checkbox" checked={useRag} onChange={(e) => setUseRag(e.target.checked)} className="w-4 h-4 text-blue-600 rounded" />
                <span className="text-sm">Enable RAG (search patient database)</span>
              </label>
            </div>
          </div>

          {/* Sources */}
          {response?.sources && response.sources.length > 0 && (
            <div className="card">
              <h3 className="font-semibold mb-3">Sources</h3>
              <div className="space-y-2">
                {response.sources.map((s, i) => (
                  <div key={i} className="flex items-center justify-between text-sm">
                    <span className="font-mono text-blue-600">{s.patient_id}</span>
                    <span className="text-gray-400">relevance: {s.relevance}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* History */}
          <div className="card">
            <h3 className="font-semibold mb-3">Recent Queries</h3>
            {history.length === 0 ? (
              <p className="text-gray-400 text-sm">No queries yet</p>
            ) : (
              <div className="space-y-2">
                {history.map((h, i) => (
                  <div key={i} className="text-sm py-1 border-b border-gray-100 last:border-0">
                    <p className="text-gray-700 truncate">{h.question}</p>
                    <div className="flex items-center gap-2 mt-0.5">
                      <span className={h.blocked ? 'badge-block' : 'badge-pass'}>{h.blocked ? 'blocked' : 'pass'}</span>
                      <span className="text-xs text-gray-400">{h.timestamp ? new Date(h.timestamp).toLocaleTimeString() : ''}</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
