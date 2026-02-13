import { useState, useEffect } from 'react'
import { getDocuments, uploadDocument, extractDocument, classifyDocument, deleteDocument } from '../api/client'
import { DocumentItem } from '../types'
import SecurityBadges from './SecurityBadges'

export default function Documents() {
  const [documents, setDocuments] = useState<DocumentItem[]>([])
  const [loading, setLoading] = useState(true)
  const [uploading, setUploading] = useState(false)
  const [processing, setProcessing] = useState<number | null>(null)
  const [result, setResult] = useState<any>(null)

  const load = () => {
    setLoading(true)
    getDocuments()
      .then((data) => setDocuments(data.documents))
      .catch(console.error)
      .finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [])

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    setUploading(true)
    try {
      await uploadDocument(file)
      load()
    } catch (err) {
      console.error(err)
      alert('Upload failed')
    } finally {
      setUploading(false)
    }
  }

  const handleExtract = async (docId: number) => {
    setProcessing(docId)
    setResult(null)
    try {
      const res = await extractDocument(docId)
      setResult({ type: 'extract', docId, ...res })
      load()
    } catch (err) {
      console.error(err)
    } finally {
      setProcessing(null)
    }
  }

  const handleClassify = async (docId: number) => {
    setProcessing(docId)
    setResult(null)
    try {
      const res = await classifyDocument(docId)
      setResult({ type: 'classify', docId, ...res })
      load()
    } catch (err) {
      console.error(err)
    } finally {
      setProcessing(null)
    }
  }

  const handleDelete = async (docId: number) => {
    if (!confirm('Delete this document?')) return
    await deleteDocument(docId)
    load()
  }

  const formatSize = (bytes?: number) => {
    if (!bytes) return 'N/A'
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold">Documents</h2>
        <label className={`btn-primary cursor-pointer ${uploading ? 'opacity-50' : ''}`}>
          {uploading ? 'Uploading...' : '+ Upload Document'}
          <input type="file" className="hidden" onChange={handleUpload} disabled={uploading} />
        </label>
      </div>

      {/* Document List */}
      <div className="card p-0 overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b">
            <tr>
              <th className="text-left px-4 py-3 font-medium text-gray-500">Filename</th>
              <th className="text-left px-4 py-3 font-medium text-gray-500">Type</th>
              <th className="text-left px-4 py-3 font-medium text-gray-500">Size</th>
              <th className="text-left px-4 py-3 font-medium text-gray-500">Classification</th>
              <th className="text-left px-4 py-3 font-medium text-gray-500">Extracted</th>
              <th className="text-left px-4 py-3 font-medium text-gray-500">Actions</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={6} className="px-4 py-8 text-center text-gray-400">Loading...</td></tr>
            ) : documents.length === 0 ? (
              <tr><td colSpan={6} className="px-4 py-8 text-center text-gray-400">No documents. Upload one to get started.</td></tr>
            ) : documents.map((doc) => (
              <tr key={doc.id} className="border-b border-gray-100 hover:bg-gray-50">
                <td className="px-4 py-3 font-medium">{doc.filename}</td>
                <td className="px-4 py-3 text-gray-500">{doc.file_type}</td>
                <td className="px-4 py-3 text-gray-500">{formatSize(doc.file_size)}</td>
                <td className="px-4 py-3">
                  {doc.classification ? (
                    <span className="bg-purple-50 text-purple-700 text-xs px-2 py-0.5 rounded">{doc.classification}</span>
                  ) : <span className="text-gray-300">-</span>}
                </td>
                <td className="px-4 py-3">
                  {doc.extracted_data ? (
                    <span className="badge-pass">Yes</span>
                  ) : <span className="text-gray-300">-</span>}
                </td>
                <td className="px-4 py-3">
                  <div className="flex gap-2">
                    <button
                      onClick={() => handleExtract(doc.id)}
                      disabled={processing === doc.id}
                      className="text-blue-600 hover:underline text-xs disabled:opacity-50"
                    >
                      {processing === doc.id ? 'Processing...' : 'AI Extract'}
                    </button>
                    <button
                      onClick={() => handleClassify(doc.id)}
                      disabled={processing === doc.id}
                      className="text-purple-600 hover:underline text-xs disabled:opacity-50"
                    >
                      Classify
                    </button>
                    <button onClick={() => handleDelete(doc.id)} className="text-red-600 hover:underline text-xs">Delete</button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Result Modal */}
      {result && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50" onClick={() => setResult(null)}>
          <div className="bg-white rounded-xl shadow-xl max-w-lg w-full mx-4 p-6 max-h-[80vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
            <div className="flex justify-between items-start mb-4">
              <h3 className="text-lg font-bold">
                {result.blocked ? 'Blocked by Security' : result.type === 'extract' ? 'Extraction Result' : 'Classification Result'}
              </h3>
              <button onClick={() => setResult(null)} className="text-gray-400 hover:text-gray-600 text-xl">&times;</button>
            </div>

            {result.blocked ? (
              <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                <p className="text-red-800 font-medium">Blocked by: {result.blocked_by}</p>
                <p className="text-red-600 text-sm mt-1">{result.blocked_reason}</p>
              </div>
            ) : result.type === 'extract' ? (
              <pre className="bg-gray-50 p-4 rounded-lg text-xs overflow-x-auto">
                {JSON.stringify(result.extracted_data, null, 2)}
              </pre>
            ) : (
              <div>
                <p><span className="font-medium">Classification:</span> {result.classification}</p>
                <p><span className="font-medium">Confidence:</span> {(result.confidence * 100).toFixed(0)}%</p>
              </div>
            )}

            {result.security_scan && (
              <div className="mt-4 pt-4 border-t">
                <h4 className="text-sm font-medium mb-2">Security Scan</h4>
                <SecurityBadges
                  toolResults={result.security_scan?.tool_results}
                  hlVerdict={result.security_scan?.hl_verdict}
                  hlScanTimeMs={result.security_scan?.hl_scan_time_ms}
                  aimVerdict={result.security_scan?.aim_verdict}
                  aimScanTimeMs={result.security_scan?.aim_scan_time_ms}
                />
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
