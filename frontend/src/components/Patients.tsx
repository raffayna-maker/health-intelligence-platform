import { useState, useEffect, useCallback } from 'react'
import { getPatients, createPatient, updatePatient, deletePatient } from '../api/client'
import { Patient } from '../types'

export default function Patients() {
  const [patients, setPatients] = useState<Patient[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [riskFilter, setRiskFilter] = useState('')
  const [loading, setLoading] = useState(true)
  const [selected, setSelected] = useState<Patient | null>(null)
  const [editing, setEditing] = useState(false)
  const [creating, setCreating] = useState(false)
  const [editForm, setEditForm] = useState<Record<string, any>>({})

  const load = useCallback(() => {
    setLoading(true)
    getPatients(page, search, riskFilter)
      .then((data) => {
        setPatients(data.patients)
        setTotal(data.total)
      })
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [page, search, riskFilter])

  useEffect(() => { load() }, [load])

  const handleDelete = async (pid: string) => {
    if (!confirm(`Delete patient ${pid}?`)) return
    await deletePatient(pid)
    load()
    if (selected?.patient_id === pid) setSelected(null)
  }

  const handleSaveEdit = async () => {
    if (!selected) return
    await updatePatient(selected.patient_id, editForm)
    setEditing(false)
    setSelected(null)
    load()
  }

  const handleCreate = async () => {
    await createPatient(editForm)
    setCreating(false)
    setEditForm({})
    load()
  }

  const startEdit = (p: Patient) => {
    setSelected(p)
    setEditing(true)
    setEditForm({
      name: p.name,
      date_of_birth: p.date_of_birth,
      gender: p.gender,
      ssn: p.ssn || '',
      phone: p.phone || '',
      email: p.email || '',
      address: p.address || '',
      conditions: p.conditions,
      medications: p.medications,
      risk_score: p.risk_score,
      notes: p.notes || '',
    })
  }

  const riskBadge = (score: number) => {
    if (score > 75) return <span className="badge-block">High ({score})</span>
    if (score >= 50) return <span className="badge-error">Medium ({score})</span>
    return <span className="badge-pass">Low ({score})</span>
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold">Patients</h2>
        <button onClick={() => { setCreating(true); setEditForm({ name: '', date_of_birth: '1980-01-01', gender: 'Male', conditions: [], medications: [], risk_score: 50 }) }} className="btn-primary">
          + Add Patient
        </button>
      </div>

      {/* Search & Filter */}
      <div className="flex gap-3">
        <input
          className="input flex-1"
          placeholder="Search by name, ID, or condition..."
          value={search}
          onChange={(e) => { setSearch(e.target.value); setPage(1) }}
        />
        <select className="input w-40" value={riskFilter} onChange={(e) => { setRiskFilter(e.target.value); setPage(1) }}>
          <option value="">All Risk</option>
          <option value="high">High Risk</option>
          <option value="medium">Medium Risk</option>
          <option value="low">Low Risk</option>
        </select>
      </div>

      {/* Patient Table */}
      <div className="card p-0 overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b">
            <tr>
              <th className="text-left px-4 py-3 font-medium text-gray-500">ID</th>
              <th className="text-left px-4 py-3 font-medium text-gray-500">Name</th>
              <th className="text-left px-4 py-3 font-medium text-gray-500">Gender</th>
              <th className="text-left px-4 py-3 font-medium text-gray-500">Conditions</th>
              <th className="text-left px-4 py-3 font-medium text-gray-500">Risk</th>
              <th className="text-left px-4 py-3 font-medium text-gray-500">Actions</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={6} className="px-4 py-8 text-center text-gray-400">Loading...</td></tr>
            ) : patients.length === 0 ? (
              <tr><td colSpan={6} className="px-4 py-8 text-center text-gray-400">No patients found</td></tr>
            ) : patients.map((p) => (
              <tr key={p.patient_id} className="border-b border-gray-100 hover:bg-gray-50 cursor-pointer" onClick={() => setSelected(p)}>
                <td className="px-4 py-3 font-mono text-blue-600">{p.patient_id}</td>
                <td className="px-4 py-3 font-medium">{p.name}</td>
                <td className="px-4 py-3">{p.gender}</td>
                <td className="px-4 py-3">
                  <div className="flex gap-1 flex-wrap">
                    {p.conditions?.map((c, i) => (
                      <span key={i} className="bg-blue-50 text-blue-700 text-xs px-2 py-0.5 rounded">{c}</span>
                    ))}
                  </div>
                </td>
                <td className="px-4 py-3">{riskBadge(p.risk_score)}</td>
                <td className="px-4 py-3">
                  <div className="flex gap-2" onClick={(e) => e.stopPropagation()}>
                    <button onClick={() => startEdit(p)} className="text-blue-600 hover:underline text-xs">Edit</button>
                    <button onClick={() => handleDelete(p.patient_id)} className="text-red-600 hover:underline text-xs">Delete</button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      <div className="flex items-center justify-between text-sm text-gray-500">
        <span>Showing {patients.length} of {total} patients</span>
        <div className="flex gap-2">
          <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page <= 1} className="btn-secondary text-xs">Previous</button>
          <span className="px-3 py-1">Page {page}</span>
          <button onClick={() => setPage(p => p + 1)} disabled={patients.length < 20} className="btn-secondary text-xs">Next</button>
        </div>
      </div>

      {/* Detail Modal */}
      {selected && !editing && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50" onClick={() => setSelected(null)}>
          <div className="bg-white rounded-xl shadow-xl max-w-lg w-full mx-4 p-6 max-h-[80vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
            <div className="flex justify-between items-start mb-4">
              <div>
                <h3 className="text-xl font-bold">{selected.name}</h3>
                <span className="text-sm text-gray-500 font-mono">{selected.patient_id}</span>
              </div>
              <button onClick={() => setSelected(null)} className="text-gray-400 hover:text-gray-600 text-xl">&times;</button>
            </div>
            <div className="grid grid-cols-2 gap-3 text-sm">
              <div><span className="text-gray-500">DOB:</span> {selected.date_of_birth}</div>
              <div><span className="text-gray-500">Gender:</span> {selected.gender}</div>
              <div><span className="text-gray-500">Risk Score:</span> {riskBadge(selected.risk_score)}</div>
              <div><span className="text-gray-500">Last Visit:</span> {selected.last_visit || 'N/A'}</div>
            </div>
            <div className="mt-4 p-3 bg-gray-50 rounded-lg space-y-1 text-sm">
              <div className="text-gray-500 font-medium text-xs uppercase tracking-wide mb-2">Contact Information</div>
              <div><span className="text-gray-500">SSN:</span> {selected.ssn || 'N/A'}</div>
              <div><span className="text-gray-500">Phone:</span> {selected.phone || 'N/A'}</div>
              <div><span className="text-gray-500">Email:</span> {selected.email || 'N/A'}</div>
              <div><span className="text-gray-500">Address:</span> {selected.address || 'N/A'}</div>
            </div>
            <div className="mt-4 space-y-2 text-sm">
              <div><span className="text-gray-500 font-medium">Conditions:</span> {selected.conditions?.join(', ') || 'None'}</div>
              <div><span className="text-gray-500 font-medium">Medications:</span> {selected.medications?.join(', ') || 'None'}</div>
              <div><span className="text-gray-500 font-medium">Allergies:</span> {selected.allergies?.join(', ') || 'None'}</div>
              <div><span className="text-gray-500 font-medium">Notes:</span> {selected.notes || 'No notes'}</div>
            </div>
            <div className="mt-4 flex gap-2">
              <button onClick={() => startEdit(selected)} className="btn-primary text-sm">Edit</button>
              <button onClick={() => { handleDelete(selected.patient_id); }} className="btn-danger text-sm">Delete</button>
            </div>
          </div>
        </div>
      )}

      {/* Edit / Create Modal */}
      {(editing || creating) && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl max-w-lg w-full mx-4 p-6 max-h-[80vh] overflow-y-auto">
            <h3 className="text-lg font-bold mb-4">{creating ? 'Add New Patient' : `Edit ${selected?.patient_id}`}</h3>
            <div className="space-y-3">
              <div>
                <label className="text-sm text-gray-600">Name</label>
                <input className="input" value={editForm.name || ''} onChange={(e) => setEditForm({ ...editForm, name: e.target.value })} />
              </div>
              <div>
                <label className="text-sm text-gray-600">Date of Birth</label>
                <input type="date" className="input" value={editForm.date_of_birth || ''} onChange={(e) => setEditForm({ ...editForm, date_of_birth: e.target.value })} />
              </div>
              <div>
                <label className="text-sm text-gray-600">Gender</label>
                <select className="input" value={editForm.gender || ''} onChange={(e) => setEditForm({ ...editForm, gender: e.target.value })}>
                  <option value="Male">Male</option>
                  <option value="Female">Female</option>
                </select>
              </div>
              <div className="text-xs text-gray-400 uppercase tracking-wide pt-2">Contact Information</div>
              <div>
                <label className="text-sm text-gray-600">SSN</label>
                <input className="input" placeholder="XXX-XX-XXXX" value={editForm.ssn || ''} onChange={(e) => setEditForm({ ...editForm, ssn: e.target.value })} />
              </div>
              <div>
                <label className="text-sm text-gray-600">Phone</label>
                <input className="input" placeholder="(555) 123-4567" value={editForm.phone || ''} onChange={(e) => setEditForm({ ...editForm, phone: e.target.value })} />
              </div>
              <div>
                <label className="text-sm text-gray-600">Email</label>
                <input type="email" className="input" placeholder="patient@email.com" value={editForm.email || ''} onChange={(e) => setEditForm({ ...editForm, email: e.target.value })} />
              </div>
              <div>
                <label className="text-sm text-gray-600">Address</label>
                <input className="input" value={editForm.address || ''} onChange={(e) => setEditForm({ ...editForm, address: e.target.value })} />
              </div>
              <div className="text-xs text-gray-400 uppercase tracking-wide pt-2">Clinical</div>
              <div>
                <label className="text-sm text-gray-600">Risk Score (0-100)</label>
                <input type="number" min="0" max="100" className="input" value={editForm.risk_score ?? 50} onChange={(e) => setEditForm({ ...editForm, risk_score: parseInt(e.target.value) })} />
              </div>
              <div>
                <label className="text-sm text-gray-600">Notes</label>
                <textarea className="input" rows={3} value={editForm.notes || ''} onChange={(e) => setEditForm({ ...editForm, notes: e.target.value })} />
              </div>
            </div>
            <div className="mt-4 flex gap-2">
              <button onClick={creating ? handleCreate : handleSaveEdit} className="btn-primary">Save</button>
              <button onClick={() => { setEditing(false); setCreating(false); setSelected(null) }} className="btn-secondary">Cancel</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
