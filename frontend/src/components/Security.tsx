import { useState, useEffect } from 'react'
import { getSecurityLogs, getSecurityStats, exportSecurityLogs } from '../api/client'
import { SecurityLog, SecurityStats } from '../types'

export default function Security() {
  const [stats, setStats] = useState<SecurityStats | null>(null)
  const [logs, setLogs] = useState<SecurityLog[]>([])
  const [totalLogs, setTotalLogs] = useState(0)
  const [page, setPage] = useState(1)
  const [featureFilter, setFeatureFilter] = useState('')
  const [verdictFilter, setVerdictFilter] = useState('')
  const [loading, setLoading] = useState(true)
  const [selectedLog, setSelectedLog] = useState<SecurityLog | null>(null)

  const load = () => {
    setLoading(true)
    Promise.all([
      getSecurityStats(),
      getSecurityLogs(page, featureFilter, verdictFilter),
    ])
      .then(([s, l]) => {
        setStats(s)
        setLogs(l.logs)
        setTotalLogs(l.total)
      })
      .catch(console.error)
      .finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [page, featureFilter, verdictFilter])

  const handleExport = async () => {
    try {
      const blob = await exportSecurityLogs()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = 'security_logs.csv'
      a.click()
      URL.revokeObjectURL(url)
    } catch (err) { console.error(err) }
  }

  if (loading && !stats) return <div className="text-center py-12 text-gray-500">Loading security data...</div>

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold">Security Monitoring</h2>
        <button onClick={handleExport} className="btn-secondary text-sm">Export CSV</button>
      </div>

      {/* Comparison Dashboard */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="card text-center">
          <div className="text-sm text-gray-500 mb-1">Total Scans</div>
          <div className="text-3xl font-bold">{stats?.total_scans || 0}</div>
        </div>
        <div className="card text-center">
          <div className="text-sm text-gray-500 mb-1">Hidden Layer Blocks</div>
          <div className="text-3xl font-bold text-blue-600">{stats?.hl_blocks || 0}</div>
          <div className="text-xs text-gray-400 mt-1">Avg: {stats?.hl_avg_scan_time_ms || 0}ms</div>
        </div>
        <div className="card text-center">
          <div className="text-sm text-gray-500 mb-1">AIM Blocks</div>
          <div className="text-3xl font-bold text-purple-600">{stats?.aim_blocks || 0}</div>
          <div className="text-xs text-gray-400 mt-1">Avg: {stats?.aim_avg_scan_time_ms || 0}ms</div>
        </div>
      </div>

      {/* Agreement Analysis */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="card">
          <h3 className="text-lg font-semibold mb-4">Agreement Analysis</h3>
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-sm">Both Agreed (Allow)</span>
              <span className="font-bold text-green-600">
                {(stats?.total_scans || 0) - (stats?.hl_blocks || 0) - (stats?.aim_blocks || 0) + (stats?.both_blocked || 0)}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm">Both Agreed (Block)</span>
              <span className="font-bold text-red-600">{stats?.both_blocked || 0}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm">Disagreements</span>
              <span className="font-bold text-yellow-600">{stats?.disagreements || 0}</span>
            </div>
            <hr />
            <div className="flex items-center justify-between text-sm text-gray-500">
              <span>HL blocked, AIM allowed</span>
              <span>{stats?.hl_only_blocks || 0}</span>
            </div>
            <div className="flex items-center justify-between text-sm text-gray-500">
              <span>AIM blocked, HL allowed</span>
              <span>{stats?.aim_only_blocks || 0}</span>
            </div>
          </div>
        </div>

        <div className="card">
          <h3 className="text-lg font-semibold mb-4">Performance Comparison</h3>
          <div className="space-y-4">
            <div>
              <div className="flex justify-between text-sm mb-1">
                <span className="text-blue-600 font-medium">Hidden Layer</span>
                <span>{stats?.hl_avg_scan_time_ms || 0}ms avg</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-3">
                <div
                  className="bg-blue-500 h-3 rounded-full transition-all"
                  style={{ width: `${Math.min(100, ((stats?.hl_avg_scan_time_ms || 0) / Math.max(stats?.aim_avg_scan_time_ms || 1, stats?.hl_avg_scan_time_ms || 1)) * 100)}%` }}
                ></div>
              </div>
            </div>
            <div>
              <div className="flex justify-between text-sm mb-1">
                <span className="text-purple-600 font-medium">AIM</span>
                <span>{stats?.aim_avg_scan_time_ms || 0}ms avg</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-3">
                <div
                  className="bg-purple-500 h-3 rounded-full transition-all"
                  style={{ width: `${Math.min(100, ((stats?.aim_avg_scan_time_ms || 0) / Math.max(stats?.aim_avg_scan_time_ms || 1, stats?.hl_avg_scan_time_ms || 1)) * 100)}%` }}
                ></div>
              </div>
            </div>
            <div className="pt-2 border-t">
              <div className="flex justify-between text-sm">
                <span className="text-gray-500">Block Rate - HL</span>
                <span className="font-medium">
                  {stats?.total_scans ? ((stats.hl_blocks / stats.total_scans) * 100).toFixed(1) : 0}%
                </span>
              </div>
              <div className="flex justify-between text-sm mt-1">
                <span className="text-gray-500">Block Rate - AIM</span>
                <span className="font-medium">
                  {stats?.total_scans ? ((stats.aim_blocks / stats.total_scans) * 100).toFixed(1) : 0}%
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Filters */}
      <div className="flex gap-3">
        <select className="input w-48" value={featureFilter} onChange={(e) => { setFeatureFilter(e.target.value); setPage(1) }}>
          <option value="">All Features</option>
          <option value="clinical_assistant">Clinical Assistant</option>
          <option value="document_extraction">Document Extraction</option>
          <option value="risk_calculation">Risk Calculation</option>
          <option value="trend_analysis">Trend Analysis</option>
          <option value="report_generation">Report Generation</option>
          <option value="care_coordinator_agent">Care Coordinator Agent</option>
        </select>
        <select className="input w-40" value={verdictFilter} onChange={(e) => { setVerdictFilter(e.target.value); setPage(1) }}>
          <option value="">All Verdicts</option>
          <option value="pass">Pass</option>
          <option value="block">Block</option>
        </select>
      </div>

      {/* Security Log Table */}
      <div className="card p-0 overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b">
            <tr>
              <th className="text-left px-4 py-3 font-medium text-gray-500">Time</th>
              <th className="text-left px-4 py-3 font-medium text-gray-500">Feature</th>
              <th className="text-left px-4 py-3 font-medium text-gray-500">Type</th>
              <th className="text-left px-4 py-3 font-medium text-gray-500">Hidden Layer</th>
              <th className="text-left px-4 py-3 font-medium text-gray-500">AIM</th>
              <th className="text-left px-4 py-3 font-medium text-gray-500">Final</th>
            </tr>
          </thead>
          <tbody>
            {logs.length === 0 ? (
              <tr><td colSpan={6} className="px-4 py-8 text-center text-gray-400">No security logs yet</td></tr>
            ) : logs.map((log) => (
              <tr
                key={log.id}
                className="border-b border-gray-100 hover:bg-gray-50 cursor-pointer"
                onClick={() => setSelectedLog(log)}
              >
                <td className="px-4 py-3 text-xs text-gray-500">
                  {log.timestamp ? new Date(log.timestamp).toLocaleString() : ''}
                </td>
                <td className="px-4 py-3 text-xs">{log.feature}</td>
                <td className="px-4 py-3 text-xs text-gray-500">{log.scan_type}</td>
                <td className="px-4 py-3">
                  <span className={log.hl_verdict === 'pass' ? 'badge-pass' : log.hl_verdict === 'block' ? 'badge-block' : 'badge-error'}>
                    {log.hl_verdict} ({log.hl_scan_time_ms}ms)
                  </span>
                </td>
                <td className="px-4 py-3">
                  <span className={log.aim_verdict === 'pass' ? 'badge-pass' : log.aim_verdict === 'block' ? 'badge-block' : 'badge-error'}>
                    {log.aim_verdict} ({log.aim_scan_time_ms}ms)
                  </span>
                </td>
                <td className="px-4 py-3">
                  <span className={log.final_verdict === 'pass' ? 'badge-pass' : 'badge-block'}>
                    {log.final_verdict}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      <div className="flex items-center justify-between text-sm text-gray-500">
        <span>Showing {logs.length} of {totalLogs} logs</span>
        <div className="flex gap-2">
          <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page <= 1} className="btn-secondary text-xs">Previous</button>
          <span className="px-3 py-1">Page {page}</span>
          <button onClick={() => setPage(p => p + 1)} disabled={logs.length < 50} className="btn-secondary text-xs">Next</button>
        </div>
      </div>

      {/* Log Detail Modal */}
      {selectedLog && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50" onClick={() => setSelectedLog(null)}>
          <div className="bg-white rounded-xl shadow-xl max-w-lg w-full mx-4 p-6" onClick={(e) => e.stopPropagation()}>
            <div className="flex justify-between items-start mb-4">
              <h3 className="text-lg font-bold">Security Scan #{selectedLog.id}</h3>
              <button onClick={() => setSelectedLog(null)} className="text-gray-400 hover:text-gray-600 text-xl">&times;</button>
            </div>
            <div className="space-y-3 text-sm">
              <div><strong>Feature:</strong> {selectedLog.feature}</div>
              <div><strong>Scan Type:</strong> {selectedLog.scan_type}</div>
              <div><strong>Content:</strong> <span className="text-gray-500">{selectedLog.content_preview || 'N/A'}</span></div>
              <hr />
              <div className="grid grid-cols-2 gap-4">
                <div className="p-3 bg-blue-50 rounded-lg">
                  <h4 className="font-semibold text-blue-700 mb-1">Hidden Layer</h4>
                  <p>Verdict: <span className={selectedLog.hl_verdict === 'pass' ? 'text-green-600 font-medium' : 'text-red-600 font-medium'}>{selectedLog.hl_verdict}</span></p>
                  <p>Time: {selectedLog.hl_scan_time_ms}ms</p>
                  {selectedLog.hl_reason && <p>Reason: {selectedLog.hl_reason}</p>}
                </div>
                <div className="p-3 bg-purple-50 rounded-lg">
                  <h4 className="font-semibold text-purple-700 mb-1">AIM</h4>
                  <p>Verdict: <span className={selectedLog.aim_verdict === 'pass' ? 'text-green-600 font-medium' : 'text-red-600 font-medium'}>{selectedLog.aim_verdict}</span></p>
                  <p>Time: {selectedLog.aim_scan_time_ms}ms</p>
                  {selectedLog.aim_reason && <p>Reason: {selectedLog.aim_reason}</p>}
                </div>
              </div>
              <div className="text-center pt-2">
                <span className="font-medium">Final Verdict: </span>
                <span className={selectedLog.final_verdict === 'pass' ? 'badge-pass text-base' : 'badge-block text-base'}>
                  {selectedLog.final_verdict.toUpperCase()}
                </span>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
