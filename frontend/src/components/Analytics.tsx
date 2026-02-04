import { useState, useEffect } from 'react'
import { getRiskDistribution, getConditionPrevalence, calculateRisk, analyzeTrends, predictReadmission } from '../api/client'

export default function Analytics() {
  const [riskDist, setRiskDist] = useState<any>(null)
  const [conditions, setConditions] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  // Risk calculator
  const [riskPatientId, setRiskPatientId] = useState('')
  const [riskResult, setRiskResult] = useState<any>(null)
  const [riskLoading, setRiskLoading] = useState(false)

  // Trends
  const [trendQuery, setTrendQuery] = useState('')
  const [trendResult, setTrendResult] = useState<any>(null)
  const [trendLoading, setTrendLoading] = useState(false)

  // Readmission
  const [readmitId, setReadmitId] = useState('')
  const [readmitResult, setReadmitResult] = useState<any>(null)
  const [readmitLoading, setReadmitLoading] = useState(false)

  useEffect(() => {
    Promise.all([getRiskDistribution(), getConditionPrevalence()])
      .then(([rd, cp]) => { setRiskDist(rd); setConditions(cp) })
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [])

  const handleCalculateRisk = async () => {
    if (!riskPatientId) return
    setRiskLoading(true)
    try {
      const res = await calculateRisk(riskPatientId)
      setRiskResult(res)
    } catch (e) { console.error(e) }
    finally { setRiskLoading(false) }
  }

  const handleTrends = async () => {
    if (!trendQuery) return
    setTrendLoading(true)
    try {
      const res = await analyzeTrends(trendQuery)
      setTrendResult(res)
    } catch (e) { console.error(e) }
    finally { setTrendLoading(false) }
  }

  const handleReadmission = async () => {
    if (!readmitId) return
    setReadmitLoading(true)
    try {
      const res = await predictReadmission(readmitId)
      setReadmitResult(res)
    } catch (e) { console.error(e) }
    finally { setReadmitLoading(false) }
  }

  const SecurityIndicator = ({ scan }: { scan: any }) => {
    if (!scan) return null
    return (
      <div className="flex gap-2 mt-2">
        <span className={scan.hl_verdict === 'pass' ? 'badge-pass' : 'badge-block'}>HL: {scan.hl_verdict}</span>
        <span className={scan.aim_verdict === 'pass' ? 'badge-pass' : 'badge-block'}>AIM: {scan.aim_verdict}</span>
      </div>
    )
  }

  if (loading) return <div className="text-center py-12 text-gray-500">Loading analytics...</div>

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold">Analytics</h2>

      {/* Risk Distribution */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="card">
          <h3 className="text-lg font-semibold mb-4">Risk Distribution</h3>
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium text-red-600">High Risk (&gt;75)</span>
              <span className="font-bold text-red-600">{riskDist?.high || 0}</span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-4">
              <div className="bg-red-500 h-4 rounded-full" style={{ width: `${((riskDist?.high || 0) / 200) * 100}%` }}></div>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium text-yellow-600">Medium Risk (50-75)</span>
              <span className="font-bold text-yellow-600">{riskDist?.medium || 0}</span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-4">
              <div className="bg-yellow-500 h-4 rounded-full" style={{ width: `${((riskDist?.medium || 0) / 200) * 100}%` }}></div>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium text-green-600">Low Risk (&lt;50)</span>
              <span className="font-bold text-green-600">{riskDist?.low || 0}</span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-4">
              <div className="bg-green-500 h-4 rounded-full" style={{ width: `${((riskDist?.low || 0) / 200) * 100}%` }}></div>
            </div>
          </div>
        </div>

        <div className="card">
          <h3 className="text-lg font-semibold mb-4">Condition Prevalence</h3>
          <div className="space-y-2">
            {conditions?.conditions && Object.entries(conditions.conditions).map(([cond, count]) => (
              <div key={cond} className="flex items-center justify-between">
                <span className="text-sm">{cond}</span>
                <div className="flex items-center gap-2">
                  <div className="w-32 bg-gray-200 rounded-full h-3">
                    <div className="bg-blue-500 h-3 rounded-full" style={{ width: `${((count as number) / 200) * 100}%` }}></div>
                  </div>
                  <span className="text-sm font-medium w-8 text-right">{count as number}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* High Risk Patients */}
      {riskDist?.high_patients?.length > 0 && (
        <div className="card">
          <h3 className="text-lg font-semibold mb-4">High Risk Patients</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {riskDist.high_patients.slice(0, 9).map((p: any) => (
              <div key={p.patient_id} className="border border-red-200 bg-red-50 rounded-lg p-3">
                <div className="flex justify-between items-start">
                  <div>
                    <span className="font-mono text-sm text-red-600">{p.patient_id}</span>
                    <p className="font-medium text-sm">{p.name}</p>
                  </div>
                  <span className="badge-block">Score: {p.risk_score}</span>
                </div>
                <div className="mt-1 text-xs text-gray-500">{p.conditions?.join(', ')}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* AI Tools */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Risk Calculator */}
        <div className="card">
          <h3 className="text-lg font-semibold mb-3">AI Risk Calculator</h3>
          <div className="flex gap-2">
            <input className="input" placeholder="Patient ID (e.g. PT-042)" value={riskPatientId} onChange={(e) => setRiskPatientId(e.target.value)} />
            <button onClick={handleCalculateRisk} disabled={riskLoading} className="btn-primary whitespace-nowrap">
              {riskLoading ? '...' : 'Calculate'}
            </button>
          </div>
          {riskResult && (
            <div className="mt-3 p-3 bg-gray-50 rounded-lg text-sm">
              {riskResult.blocked ? (
                <p className="text-red-600">Blocked: {riskResult.security_scan?.aim_reason || riskResult.security_scan?.hl_reason}</p>
              ) : (
                <>
                  <p><strong>Risk Score:</strong> {riskResult.risk_score}</p>
                  <p className="mt-1"><strong>Factors:</strong> {riskResult.risk_factors?.join(', ')}</p>
                  <p className="mt-1"><strong>Recommendation:</strong> {riskResult.recommendation}</p>
                  <SecurityIndicator scan={riskResult.security_scan} />
                </>
              )}
            </div>
          )}
        </div>

        {/* Trend Analysis */}
        <div className="card">
          <h3 className="text-lg font-semibold mb-3">Trend Analysis</h3>
          <div className="flex gap-2">
            <input className="input" placeholder="e.g. Show diabetes trends" value={trendQuery} onChange={(e) => setTrendQuery(e.target.value)} />
            <button onClick={handleTrends} disabled={trendLoading} className="btn-primary whitespace-nowrap">
              {trendLoading ? '...' : 'Analyze'}
            </button>
          </div>
          {trendResult && (
            <div className="mt-3 p-3 bg-gray-50 rounded-lg text-sm">
              {trendResult.blocked ? (
                <p className="text-red-600">Blocked by security</p>
              ) : (
                <>
                  <p className="whitespace-pre-wrap">{trendResult.analysis}</p>
                  <SecurityIndicator scan={trendResult.security_scan} />
                </>
              )}
            </div>
          )}
        </div>

        {/* Readmission Prediction */}
        <div className="card">
          <h3 className="text-lg font-semibold mb-3">Readmission Prediction</h3>
          <div className="flex gap-2">
            <input className="input" placeholder="Patient ID" value={readmitId} onChange={(e) => setReadmitId(e.target.value)} />
            <button onClick={handleReadmission} disabled={readmitLoading} className="btn-primary whitespace-nowrap">
              {readmitLoading ? '...' : 'Predict'}
            </button>
          </div>
          {readmitResult && (
            <div className="mt-3 p-3 bg-gray-50 rounded-lg text-sm">
              {readmitResult.blocked ? (
                <p className="text-red-600">Blocked by security</p>
              ) : (
                <>
                  <p><strong>Risk:</strong> {(readmitResult.readmission_risk * 100).toFixed(0)}%</p>
                  <p className="mt-1"><strong>Factors:</strong> {readmitResult.factors?.join(', ')}</p>
                  <p className="mt-1"><strong>Recommendation:</strong> {readmitResult.recommendation}</p>
                  <SecurityIndicator scan={readmitResult.security_scan} />
                </>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
