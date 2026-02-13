import { useState, useEffect } from 'react'
import { getDashboardStats } from '../api/client'
import { DashboardStats } from '../types'
import SecurityBadges from './SecurityBadges'

export default function Dashboard() {
  const [stats, setStats] = useState<DashboardStats | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    getDashboardStats()
      .then(setStats)
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <div className="text-center py-12 text-gray-500">Loading dashboard...</div>

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold">Dashboard</h2>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="card">
          <div className="text-sm text-gray-500 mb-1">Total Patients</div>
          <div className="text-3xl font-bold text-blue-600">{stats?.patients.total || 0}</div>
        </div>
        <div className="card">
          <div className="text-sm text-gray-500 mb-1">Security Scans</div>
          <div className="text-3xl font-bold text-green-600">{stats?.security.total_scans || 0}</div>
        </div>
        <div className="card">
          <div className="text-sm text-gray-500 mb-1">Threats Blocked</div>
          <div className="text-3xl font-bold text-red-600">{stats?.security.total_blocks || 0}</div>
        </div>
        <div className="card">
          <div className="text-sm text-gray-500 mb-1">Agent Runs</div>
          <div className="text-3xl font-bold text-purple-600">{stats?.agents.total_runs || 0}</div>
          <div className="text-xs text-gray-400 mt-1">
            {stats?.agents.successful_runs || 0} successful
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Recent Agent Runs */}
        <div className="card">
          <h3 className="text-lg font-semibold mb-4">Recent Agent Runs</h3>
          {stats?.recent_agent_runs.length === 0 ? (
            <p className="text-gray-400 text-sm">No agent runs yet</p>
          ) : (
            <div className="space-y-3">
              {stats?.recent_agent_runs.map((run) => (
                <div key={run.id} className="flex items-center justify-between py-2 border-b border-gray-100 last:border-0">
                  <div>
                    <span className="font-medium text-sm">
                      {run.agent_type === 'care_coordinator' ? 'Care Coordinator' : run.agent_type.split('_').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ')}
                    </span>
                    <p className="text-xs text-gray-400">{run.started_at ? new Date(run.started_at).toLocaleString() : ''}</p>
                  </div>
                  <span className={`text-xs font-medium px-2 py-1 rounded ${
                    run.status === 'completed' ? 'bg-green-100 text-green-700' :
                    run.status === 'running' ? 'bg-blue-100 text-blue-700' :
                    run.status === 'blocked' ? 'bg-red-100 text-red-700' :
                    'bg-gray-100 text-gray-700'
                  }`}>
                    {run.status}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Recent Security Events */}
        <div className="card">
          <h3 className="text-lg font-semibold mb-4">Recent Security Events</h3>
          {stats?.recent_security_events.length === 0 ? (
            <p className="text-gray-400 text-sm">No security events yet</p>
          ) : (
            <div className="space-y-3">
              {stats?.recent_security_events.map((event) => (
                <div key={event.id} className="flex items-center justify-between py-2 border-b border-gray-100 last:border-0">
                  <div>
                    <span className="font-medium text-sm">{event.feature}</span>
                    <div className="mt-1">
                      <SecurityBadges
                        toolResults={event.tool_results}
                        hlVerdict={event.hl_verdict}
                        aimVerdict={event.aim_verdict}
                        compact
                      />
                    </div>
                  </div>
                  <span className={event.final_verdict === 'pass' ? 'badge-pass' : 'badge-block'}>
                    {event.final_verdict}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
