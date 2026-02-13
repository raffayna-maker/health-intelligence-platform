import { useState, useEffect } from 'react'
import { generateReport, getReports, getReport, deleteReport } from '../api/client'
import { ReportItem } from '../types'
import SecurityBadges from './SecurityBadges'

export default function Reports() {
  const [reports, setReports] = useState<ReportItem[]>([])
  const [loading, setLoading] = useState(true)
  const [generating, setGenerating] = useState(false)
  const [reportType, setReportType] = useState('summary')
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')
  const [viewingReport, setViewingReport] = useState<any>(null)
  const [generatedResult, setGeneratedResult] = useState<any>(null)

  const load = () => {
    setLoading(true)
    getReports()
      .then((data) => setReports(data.reports))
      .catch(console.error)
      .finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [])

  const handleGenerate = async () => {
    setGenerating(true)
    setGeneratedResult(null)
    try {
      const result = await generateReport(
        reportType,
        dateFrom || undefined,
        dateTo || undefined,
      )
      setGeneratedResult(result)
      load()
    } catch (err) {
      console.error(err)
      alert('Report generation failed')
    } finally {
      setGenerating(false)
    }
  }

  const handleView = async (id: number) => {
    try {
      const data = await getReport(id)
      setViewingReport(data)
    } catch (err) { console.error(err) }
  }

  const handleDelete = async (id: number) => {
    if (!confirm('Delete this report?')) return
    await deleteReport(id)
    load()
  }

  const handleDownload = (report: any) => {
    const blob = new Blob([report.content || ''], { type: 'text/markdown' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${report.title?.replace(/\s+/g, '_') || 'report'}.md`
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold">Reports</h2>

      {/* Report Generator */}
      <div className="card">
        <h3 className="text-lg font-semibold mb-4">Generate Report</h3>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div>
            <label className="text-sm text-gray-600">Report Type</label>
            <select className="input" value={reportType} onChange={(e) => setReportType(e.target.value)}>
              <option value="summary">Patient Summary</option>
              <option value="compliance">HIPAA Compliance</option>
              <option value="analytics">Analytics & Risk</option>
            </select>
          </div>
          <div>
            <label className="text-sm text-gray-600">Date From</label>
            <input type="date" className="input" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} />
          </div>
          <div>
            <label className="text-sm text-gray-600">Date To</label>
            <input type="date" className="input" value={dateTo} onChange={(e) => setDateTo(e.target.value)} />
          </div>
          <div className="flex items-end">
            <button onClick={handleGenerate} disabled={generating} className="btn-primary w-full">
              {generating ? 'Generating...' : 'Generate Report'}
            </button>
          </div>
        </div>

        {/* Security scan result */}
        {generatedResult?.security_scan && (
          <div className="mt-3">
            <SecurityBadges
              toolResults={generatedResult.security_scan.tool_results}
              hlVerdict={generatedResult.security_scan.hl_verdict}
              aimVerdict={generatedResult.security_scan.aim_verdict}
              compact
            />
          </div>
        )}

        {generatedResult?.blocked && (
          <div className="mt-3 bg-red-50 border border-red-200 rounded-lg p-3">
            <p className="text-red-700 font-medium">Report generation blocked by security</p>
          </div>
        )}
      </div>

      {/* Generated Report Preview */}
      {generatedResult && !generatedResult.blocked && generatedResult.content && (
        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold">{generatedResult.title}</h3>
            <button onClick={() => handleDownload(generatedResult)} className="btn-secondary text-sm">
              Download
            </button>
          </div>
          <div className="prose prose-sm max-w-none bg-gray-50 p-4 rounded-lg whitespace-pre-wrap text-sm">
            {generatedResult.content}
          </div>
        </div>
      )}

      {/* Report History */}
      <div className="card">
        <h3 className="text-lg font-semibold mb-4">Report History</h3>
        {loading ? (
          <p className="text-gray-400">Loading...</p>
        ) : reports.length === 0 ? (
          <p className="text-gray-400 text-sm">No reports generated yet</p>
        ) : (
          <div className="space-y-2">
            {reports.map((r) => (
              <div key={r.id} className="flex items-center justify-between py-2 border-b border-gray-100 last:border-0">
                <div>
                  <span className="font-medium text-sm">{r.title}</span>
                  <div className="flex gap-2 mt-0.5">
                    <span className="text-xs bg-blue-50 text-blue-700 px-2 py-0.5 rounded">{r.report_type}</span>
                    <span className="text-xs text-gray-400">
                      {r.generated_at ? new Date(r.generated_at).toLocaleString() : ''}
                    </span>
                  </div>
                </div>
                <div className="flex gap-2">
                  <button onClick={() => handleView(r.id)} className="text-blue-600 hover:underline text-xs">View</button>
                  <button onClick={() => handleDownload(r)} className="text-green-600 hover:underline text-xs">Download</button>
                  <button onClick={() => handleDelete(r.id)} className="text-red-600 hover:underline text-xs">Delete</button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Report Detail Modal */}
      {viewingReport && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50" onClick={() => setViewingReport(null)}>
          <div className="bg-white rounded-xl shadow-xl max-w-3xl w-full mx-4 p-6 max-h-[80vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
            <div className="flex justify-between items-start mb-4">
              <h3 className="text-lg font-bold">{viewingReport.title}</h3>
              <button onClick={() => setViewingReport(null)} className="text-gray-400 hover:text-gray-600 text-xl">&times;</button>
            </div>
            <div className="prose prose-sm max-w-none whitespace-pre-wrap text-sm bg-gray-50 p-4 rounded-lg">
              {viewingReport.content}
            </div>
            <div className="mt-4 flex gap-2">
              <button onClick={() => handleDownload(viewingReport)} className="btn-primary text-sm">Download</button>
              <button onClick={() => setViewingReport(null)} className="btn-secondary text-sm">Close</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
