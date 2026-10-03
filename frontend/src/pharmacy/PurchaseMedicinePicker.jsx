import React, { useEffect, useRef, useState } from 'react'
import { Plus, X } from 'lucide-react'
import api from '../api'
import toast from 'react-hot-toast'
import { parseApiError } from './pharmacyCalculations'
import { useDebouncedValue } from './useDebouncedValue'

/**
 * Search /medicines API and optionally create a new master row for purchase lines.
 */
export function PurchaseMedicinePicker({ medicineId, medicineName, onChange, defaultUnitId, onRefreshCatalog }) {
  const [open, setOpen] = useState(false)
  const [q, setQ] = useState('')
  const debouncedQ = useDebouncedValue(q, 280)
  const [results, setResults] = useState([])
  const [loading, setLoading] = useState(false)
  const [showCreate, setShowCreate] = useState(false)
  const [creating, setCreating] = useState(false)
  const [createForm, setCreateForm] = useState({ name: '', pack_info: '1x10', hsn_code: '' })
  const wrapRef = useRef(null)

  function unwrapCreatedMedicine(payload) {
    if (!payload || typeof payload !== 'object') return null
    const a = payload?.data
    if (a && typeof a === 'object' && !Array.isArray(a) && a.id) return a
    if (Array.isArray(a) && a[0] && a[0].id) return a[0]
    const b = payload?.entity
    if (b && typeof b === 'object' && b.id) return b
    if (payload?.id) return payload
    return null
  }

  useEffect(() => {
    function handle(e) {
      if (wrapRef.current && !wrapRef.current.contains(e.target)) setOpen(false)
    }
    document.addEventListener('mousedown', handle)
    return () => document.removeEventListener('mousedown', handle)
  }, [])

  useEffect(() => {
    if (!open) return
    let cancelled = false
    setLoading(true)
    const term = debouncedQ.trim()
    const url =
      term.length >= 1
        ? `/medicines/?search=${encodeURIComponent(term)}&limit=50`
        : `/medicines/?limit=50`
    api
      .get(url)
      .then((res) => {
        const list = res.data?.data || res.data?.results || []
        if (!cancelled) setResults(Array.isArray(list) ? list : [])
      })
      .catch(() => {
        if (!cancelled) setResults([])
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [debouncedQ, open])

  useEffect(() => {
    if (open) setQ(medicineName || '')
  }, [open, medicineName])

  async function createMedicine() {
    if (!createForm.name.trim() || !createForm.pack_info.trim()) {
      toast.error('Name and pack are required')
      return
    }
    setCreating(true)
    try {
      const payload = {
        sku: `PUR-${Date.now()}`,
        name: createForm.name.trim(),
        pack_info: createForm.pack_info.trim(),
        hsn_code: createForm.hsn_code.trim(),
      }
      if (defaultUnitId) payload.unit = defaultUnitId
      const { data } = await api.post('/medicines/', payload)
      const med = unwrapCreatedMedicine(data)
      const id = med?.id ? String(med.id) : ''
      const name = (med?.name || createForm.name || '').trim()
      if (!id) throw new Error('Invalid API response')
      onChange(id, name, med)
      setQ(name)
      setShowCreate(false)
      setOpen(false)
      setCreateForm({ name: '', pack_info: '1x10', hsn_code: '' })
      toast.success('Medicine created')
      // Avoid full-screen data reload/flicker right after quick-create.
      // The created medicine is already selected on this line.
    } catch (e) {
      toast.error(parseApiError(e))
    } finally {
      setCreating(false)
    }
  }

  const selectedLabel =
    medicineName || results.find((r) => r.id === medicineId)?.name || (medicineId ? '—' : '')

  return (
    <div ref={wrapRef} className="relative min-w-0">
      <div className="flex gap-0.5 items-stretch">
        <button
          type="button"
          onClick={() => setOpen((o) => !o)}
          className="flex-1 min-w-0 text-left border border-slate-200 rounded px-1 py-0.5 text-[10px] truncate bg-white hover:bg-slate-50"
          title={medicineId ? selectedLabel : 'Search or pick medicine'}
        >
          {medicineId ? selectedLabel || 'Selected' : 'Search medicine…'}
        </button>
        <button
          type="button"
          title="New medicine"
          onClick={() => {
            setCreateForm((f) => ({ ...f, name: q.trim() || f.name }))
            setShowCreate(true)
            setOpen(false)
          }}
          className="shrink-0 px-0.5 border border-emerald-200 rounded bg-emerald-50 text-emerald-800 hover:bg-emerald-100"
        >
          <Plus size={14} className="mx-auto" />
        </button>
      </div>
      {open && (
        <div className="absolute z-50 left-0 top-full mt-0.5 w-[min(16rem,70vw)] max-h-52 overflow-hidden flex flex-col bg-white border border-slate-200 shadow-lg rounded">
          <input
            autoFocus
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Name / SKU…"
            className="w-full border-b border-slate-100 px-1.5 py-1 text-[10px] outline-none shrink-0"
          />
          <div className="overflow-y-auto flex-1 min-h-0">
            {loading && <div className="p-1.5 text-[9px] text-slate-400">Searching…</div>}
            {!loading &&
              results.map((m) => (
                <button
                  key={m.id}
                  type="button"
                  className="w-full text-left px-1.5 py-1 text-[10px] hover:bg-blue-50 truncate border-b border-slate-50 last:border-0"
                  onClick={() => {
                    onChange(m.id, m.name, m)
                    setOpen(false)
                  }}
                >
                  {m.name}
                  <span className="text-slate-400 text-[9px] ml-1">{m.sku}</span>
                </button>
              ))}
            {!loading && results.length === 0 && (
              <div className="p-1.5 text-[9px] text-slate-500">No matches. Use + to add new.</div>
            )}
          </div>
        </div>
      )}
      {showCreate && (
        <div
          className="fixed inset-0 bg-black/40 z-[100] flex items-center justify-center p-4"
          onClick={() => !creating && setShowCreate(false)}
          onKeyDown={(e) => e.key === 'Escape' && !creating && setShowCreate(false)}
          role="presentation"
        >
          <div
            className="bg-white rounded-lg shadow-xl p-3 w-full max-w-sm border border-slate-200"
            onClick={(e) => e.stopPropagation()}
            onKeyDown={(e) => {
              if (e.key === 'Enter') {
                e.preventDefault()
                if (!creating) createMedicine()
              }
            }}
            role="dialog"
            aria-label="New medicine"
          >
            <div className="flex justify-between items-center mb-2">
              <span className="text-xs font-bold text-slate-800">New medicine master</span>
              <button type="button" className="text-slate-400 hover:text-slate-700" onClick={() => !creating && setShowCreate(false)}>
                <X size={16} />
              </button>
            </div>
            <p className="text-[9px] text-slate-500 mb-2">
              Pack <strong>1x10</strong> means one strip = 10 tablets (saved for stock display). Unit defaults to Tablet if none exists.
            </p>
            <div className="space-y-2">
              <label className="block">
                <span className="text-[9px] font-semibold text-slate-500 uppercase">Name *</span>
                <input
                  value={createForm.name}
                  onChange={(e) => setCreateForm((f) => ({ ...f, name: e.target.value }))}
                  className="mt-0.5 w-full border border-slate-200 rounded px-2 py-1 text-xs"
                  placeholder="e.g. PARACETAMOL 500MG"
                />
              </label>
              <label className="block">
                <span className="text-[9px] font-semibold text-slate-500 uppercase">Pack *</span>
                <input
                  value={createForm.pack_info}
                  onChange={(e) => setCreateForm((f) => ({ ...f, pack_info: e.target.value }))}
                  className="mt-0.5 w-full border border-slate-200 rounded px-2 py-1 text-xs"
                  placeholder="e.g. 1x10 (1 strip x 10 tablets)"
                />
              </label>
              <label className="block">
                <span className="text-[9px] font-semibold text-slate-500 uppercase">HSN</span>
                <input
                  value={createForm.hsn_code}
                  onChange={(e) => setCreateForm((f) => ({ ...f, hsn_code: e.target.value }))}
                  className="mt-0.5 w-full border border-slate-200 rounded px-2 py-1 text-xs"
                  placeholder="Optional"
                />
              </label>
            </div>
            <button
              type="button"
              disabled={creating}
              onClick={createMedicine}
              className="mt-3 w-full bg-emerald-600 text-white text-xs font-semibold py-2 rounded hover:bg-emerald-700 disabled:opacity-50"
            >
              {creating ? 'Saving…' : 'Create & use on this line'}
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
