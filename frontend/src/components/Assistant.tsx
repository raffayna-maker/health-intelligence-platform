import { useState, useEffect, useRef } from 'react'
import { queryAssistant, getAssistantSessions, getAssistantSession, deleteAssistantSession } from '../api/client'
import { AssistantResponse } from '../types'
import SecurityBadges from './SecurityBadges'

const SESSION_KEY = 'assistant_session_id'

function initSessionId(): string {
  return sessionStorage.getItem(SESSION_KEY) || crypto.randomUUID()
}

export default function Assistant() {
  const [question, setQuestion] = useState('')
  const [patientId, setPatientId] = useState('')
  const [useRag, setUseRag] = useState(true)
  const [loading, setLoading] = useState(false)
  const [response, setResponse] = useState<AssistantResponse | null>(null)
  const [sessions, setSessions] = useState<any[]>([])
  const [chatLog, setChatLog] = useState<Array<{ role: string; content: string; scan?: any; blocked?: boolean; blockedBy?: string }>>([])
  const [sessionId, setSessionId] = useState<string>(initSessionId)
  const bottomRef = useRef<HTMLDivElement>(null)

  // Restore existing session on mount if one was in sessionStorage
  useEffect(() => {
    const stored = sessionStorage.getItem(SESSION_KEY)
    if (stored) {
      getAssistantSession(stored)
        .then((data: any) => {
          const restored = (data.messages || []).map((m: any) => ({
            role: m.role,
            content: m.blocked ? `BLOCKED: ${m.content}` : m.content,
            blocked: m.blocked,
          }))
          setChatLog(restored)
        })
        .catch(() => {
          // Session not found on backend — start fresh
          sessionStorage.removeItem(SESSION_KEY)
          setSessionId(crypto.randomUUID())
        })
    }
    loadSessions()
  }, [])

  // Scroll to bottom when new messages arrive
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [chatLog, loading])

  const loadSessions = () => {
    getAssistantSessions()
      .then((data: any) => setSessions(data.sessions || []))
      .catch(console.error)
  }

  const handleNewSession = () => {
    sessionStorage.removeItem(SESSION_KEY)
    const newId = crypto.randomUUID()
    setSessionId(newId)
    setChatLog([])
    setResponse(null)
    loadSessions()
  }

  const handleLoadSession = async (sid: string) => {
    try {
      const data: any = await getAssistantSession(sid)
      const restored = (data.messages || []).map((m: any) => ({
        role: m.role,
        content: m.blocked ? `BLOCKED: ${m.content}` : m.content,
        blocked: m.blocked,
      }))
      sessionStorage.setItem(SESSION_KEY, sid)
      setSessionId(sid)
      setChatLog(restored)
      setResponse(null)
    } catch (err) {
      console.error(err)
    }
  }

  const handleDeleteSession = async (sid: string, e: React.MouseEvent) => {
    e.stopPropagation()
    try {
      await deleteAssistantSession(sid)
      if (sid === sessionId) {
        handleNewSession()
      } else {
        loadSessions()
      }
    } catch (err) {
      console.error(err)
    }
  }

  const handleSubmit = async () => {
    if (!question.trim()) return
    const q = question
    setQuestion('')
    setLoading(true)
    setChatLog((prev) => [...prev, { role: 'user', content: q }])

    try {
      const res = await queryAssistant(q, patientId || undefined, useRag, sessionId)
      setResponse(res)

      // Persist session_id from first response (or if backend echoes one)
      if (res.session_id) {
        sessionStorage.setItem(SESSION_KEY, res.session_id)
        if (res.session_id !== sessionId) setSessionId(res.session_id)
      }

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
      loadSessions()
    } catch (err) {
      console.error(err)
      setChatLog((prev) => [...prev, { role: 'assistant', content: 'Error: Failed to get response.' }])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold">Clinical Assistant</h2>
        <button onClick={handleNewSession} className="btn-secondary text-sm">
          + New Session
        </button>
      </div>

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
            <div ref={bottomRef} />
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

          {/* Sessions */}
          <div className="card">
            <h3 className="font-semibold mb-3">Sessions</h3>
            {sessions.length === 0 ? (
              <p className="text-gray-400 text-sm">No sessions yet</p>
            ) : (
              <div className="space-y-1">
                {sessions.map((s) => (
                  <div
                    key={s.session_id}
                    onClick={() => handleLoadSession(s.session_id)}
                    className={`group flex items-start justify-between gap-1 text-sm py-2 px-2 rounded cursor-pointer hover:bg-gray-50 border-b border-gray-100 last:border-0 ${
                      s.session_id === sessionId ? 'bg-blue-50 border-l-2 border-l-blue-400' : ''
                    }`}
                  >
                    <div className="flex-1 min-w-0">
                      <p className="text-gray-700 truncate">{s.title || '(untitled)'}</p>
                      <p className="text-xs text-gray-400 mt-0.5">
                        {s.created_at ? new Date(s.created_at).toLocaleDateString() : ''}
                      </p>
                    </div>
                    <button
                      onClick={(e) => handleDeleteSession(s.session_id, e)}
                      className="opacity-0 group-hover:opacity-100 text-gray-400 hover:text-red-500 text-xs px-1 shrink-0"
                      title="Delete session"
                    >
                      ✕
                    </button>
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
