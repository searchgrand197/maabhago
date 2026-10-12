import React, { useCallback, useEffect, useMemo, useState } from 'react'
import toast from 'react-hot-toast'
import { AlertTriangle, Ambulance, Download, Pencil, Phone, Plus, Printer, RefreshCw, Search, X, XCircle } from 'lucide-react'
import api from '../../api'
import { getApiErrorMessage } from '../../utils/apiError'
import { formatDateTime } from '../../utils/dateTimeFormat'
import { payModeLabel, printCollectionReceipt } from '../../utils/collectionReceiptPrint'
import {
  PAYMENT_MODES,
  downloadCsv,
  fmtMoney,
  formatVehicleNo,
  quickRange,
  toDateTimeInputValue,
  unwrapData,
  unwrapRows,
} from './collectionSectionUtils'

const inputCls = 'w-full border border-gray-200 rounded-lg px-2.5 py-1.5 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-rose-200 focus:border-rose-300'
const labelCls = 'block text-[11px] font-semibold text-gray-500 mb-0.5'

function emptyForm(vehicle = null) {
  return {
    vehicle: vehicle?.id || '',
    driver_name: vehicle?.driver_name || '',
    driver_phone: vehicle?.driver_phone || '',
    trip_count: 1,
    amount: '',
    payment_mode: 'cash',
    patient_name: '',
    trip_from: '',
    trip_to: '',
    distance_km: '',
    remarks: '',
    collected_at: toDateTimeInputValue(new Date()),
  }
}

export function printAmbulanceReceipt(row) {
  return printCollectionReceipt({
    title: 'Ambulance Collection Receipt',
    accent: '#b91c1c',
    fields: [
      { label: 'Receipt No', value: row.receipt_no },
      { label: 'Date', value: formatDateTime(row.collected_at) },
      { label: 'Vehicle No', value: formatVehicleNo(row.vehicle_number) },
      { label: 'Driver', value: row.driver_name },
      { label: 'Driver Phone', value: row.driver_phone },
      { label: 'Trips', value: row.trip_count },
      { label: 'Patient', value: row.patient_name },
      { label: 'Route', value: [row.trip_from, row.trip_to].filter(Boolean).join(' → ') },
      { label: 'Distance', value: row.distance_km ? `${row.distance_km} km` : '' },
      { label: 'Pay Mode', value: payModeLabel(row.payment_mode) },
      { label: 'Received By', value: row.collected_by_name },
      { label: 'Remarks', value: row.remarks, span: 3 },
    ],
    amount: row.amount,
    note: 'Amount received from ambulance driver.',
  })
}

function LastSeenBadge({ row }) {
  const d = row.days_since_last_collection
  if (d == null) return <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-gray-100 text-gray-500">Never</span>
  if (d === 0) return <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-emerald-100 text-emerald-700">Today</span>
  const cls = d >= 3 ? 'bg-rose-100 text-rose-700' : 'bg-amber-100 text-amber-700'
  return <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${cls}`}>{d} day{d > 1 ? 's' : ''} ago</span>
}

function VehicleModal({ vehicle, onClose, onSaved }) {
  const isEdit = Boolean(vehicle?.id)
  const [form, setForm] = useState(() => ({
    vehicle_number: vehicle?.vehicle_number ? formatVehicleNo(vehicle.vehicle_number) : '',
    label: vehicle?.label || '',
    driver_name: vehicle?.driver_name || '',
    driver_phone: vehicle?.driver_phone || '',
    expected_daily_amount: vehicle?.expected_daily_amount ?? '',
    notes: vehicle?.notes || '',
    is_active: vehicle?.is_active ?? true,
  }))
  const [saving, setSaving] = useState(false)
  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.type === 'checkbox' ? e.target.checked : e.target.value }))

  async function save(e) {
    e.preventDefault()
    if (!form.vehicle_number.trim()) { toast.error('Vehicle number is required'); return }
    setSaving(true)
    try {
      const payload = { ...form, expected_daily_amount: form.expected_daily_amount === '' ? '0' : form.expected_daily_amount }
      const res = isEdit
        ? await api.patch(`/ambulance/vehicles/${vehicle.id}/`, payload)
        : await api.post('/ambulance/vehicles/', payload)
      toast.success(isEdit ? 'Vehicle updated' : 'Vehicle added')
      onSaved(unwrapData(res))
    } catch (err) {
      toast.error(getApiErrorMessage(err))
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="fixed inset-0 z-[1400] bg-slate-900/50 flex items-center justify-center p-4">
      <form onSubmit={save} className="bg-white rounded-2xl shadow-2xl w-full max-w-md p-5 space-y-3">
        <div className="flex items-center justify-between">
          <h3 className="font-bold text-gray-900">{isEdit ? 'Edit ambulance' : 'Add ambulance'}</h3>
          <button type="button" onClick={onClose} className="text-gray-400 hover:text-gray-700"><X size={18} /></button>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div className="col-span-2">
            <label className={labelCls}>Vehicle number *</label>
            <input autoFocus value={form.vehicle_number} onChange={set('vehicle_number')} placeholder="HR 31 AB 1234" className={`${inputCls} uppercase font-mono`} />
          </div>
          <div className="col-span-2">
            <label className={labelCls}>Label / type</label>
            <input value={form.label} onChange={set('label')} placeholder="e.g. BLS Van, ALS, Hearse" className={inputCls} />
          </div>
          <div>
            <label className={labelCls}>Default driver</label>
            <input value={form.driver_name} onChange={set('driver_name')} className={inputCls} />
          </div>
          <div>
            <label className={labelCls}>Driver phone</label>
            <input value={form.driver_phone} onChange={set('driver_phone')} className={inputCls} />
          </div>
          <div className="col-span-2">
            <label className={labelCls}>Expected collection per day (₹)</label>
            <input type="number" min="0" step="0.01" value={form.expected_daily_amount} onChange={set('expected_daily_amount')} placeholder="Optional target for shortfall tracking" className={inputCls} />
          </div>
          <div className="col-span-2">
            <label className={labelCls}>Notes</label>
            <input value={form.notes} onChange={set('notes')} className={inputCls} />
          </div>
          <label className="col-span-2 flex items-center gap-2 text-sm text-gray-700">
            <input type="checkbox" checked={form.is_active} onChange={set('is_active')} /> Active (available for collection)
          </label>
        </div>
        <div className="flex justify-end gap-2 pt-1">
          <button type="button" onClick={onClose} className="px-4 py-2 rounded-lg bg-gray-100 text-sm font-semibold text-gray-700">Cancel</button>
          <button type="submit" disabled={saving} className="px-4 py-2 rounded-lg bg-rose-600 text-white text-sm font-bold hover:bg-rose-700 disabled:opacity-50">
            {saving ? 'Saving…' : 'Save'}
          </button>
        </div>
      </form>
    </div>
  )
}

export function VoidReceiptModal({ title, receiptNo, onClose, onConfirm }) {
  const [reason, setReason] = useState('')
  const [saving, setSaving] = useState(false)
  async function submit(e) {
    e.preventDefault()
    if (!reason.trim()) { toast.error('Reason is required'); return }
    setSaving(true)
    try {
      await onConfirm(reason.trim())
    } finally {
      setSaving(false)
    }
  }
  return (
    <div className="fixed inset-0 z-[1400] bg-slate-900/50 flex items-center justify-center p-4">
      <form onSubmit={submit} className="bg-white rounded-2xl shadow-2xl w-full max-w-sm p-5 space-y-3">
        <h3 className="font-bold text-gray-900">{title}</h3>
        <p className="text-xs text-gray-500">Receipt <span className="font-mono font-semibold">{receiptNo}</span> will be cancelled and removed from collection totals.</p>
        <textarea autoFocus rows={3} value={reason} onChange={(e) => setReason(e.target.value)} placeholder="Reason for cancellation" className={inputCls} />
        <div className="flex justify-end gap-2">
          <button type="button" onClick={onClose} className="px-4 py-2 rounded-lg bg-gray-100 text-sm font-semibold text-gray-700">Back</button>
          <button type="submit" disabled={saving} className="px-4 py-2 rounded-lg bg-rose-600 text-white text-sm font-bold disabled:opacity-50">
            {saving ? 'Cancelling…' : 'Cancel receipt'}
          </button>
        </div>
      </form>
    </div>
  )
}

export default function AmbulanceCollectionSection() {
  const [vehicles, setVehicles] = useState([])
  const [[dateFrom, dateTo], setRange] = useState(() => quickRange('today'))
  const [summary, setSummary] = useState(null)
  const [receipts, setReceipts] = useState([])
  const [tab, setTab] = useState('summary')
  const [vehicleFilter, setVehicleFilter] = useState('')
  const [search, setSearch] = useState('')
  const [loading, setLoading] = useState(false)
  const [form, setForm] = useState(() => emptyForm())
  const [saving, setSaving] = useState(false)
  const [vehicleModal, setVehicleModal] = useState(null)
  const [voidTarget, setVoidTarget] = useState(null)

  const activeVehicles = useMemo(() => vehicles.filter((v) => v.is_active), [vehicles])

  const loadVehicles = useCallback(async () => {
    try {
      setVehicles(unwrapRows(await api.get('/ambulance/vehicles/')))
    } catch {
      toast.error('Failed to load ambulances')
    }
  }, [])

  const loadData = useCallback(async () => {
    setLoading(true)
    try {
      const params = new URLSearchParams({
        limit: '500',
        collected_at__date__gte: dateFrom,
        collected_at__date__lte: dateTo,
      })
      if (vehicleFilter) params.set('vehicle', vehicleFilter)
      if (search.trim()) params.set('search', search.trim())
      const [sumRes, listRes] = await Promise.all([
        api.get(`/ambulance/vehicles/summary/?date_from=${dateFrom}&date_to=${dateTo}`),
        api.get(`/ambulance/collections/?${params}`),
      ])
      setSummary(unwrapData(sumRes))
      setReceipts(unwrapRows(listRes))
    } catch {
      toast.error('Failed to load ambulance collections')
    } finally {
      setLoading(false)
    }
  }, [dateFrom, dateTo, vehicleFilter, search])

  useEffect(() => { loadVehicles() }, [loadVehicles])
  useEffect(() => {
    const t = setTimeout(loadData, 250)
    return () => clearTimeout(t)
  }, [loadData])

  const setField = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }))

  function pickVehicle(id) {
    const v = vehicles.find((x) => x.id === id)
    setForm((f) => ({
      ...f,
      vehicle: id,
      driver_name: v?.driver_name || '',
      driver_phone: v?.driver_phone || '',
    }))
  }

  async function submit(printAfter) {
    if (!form.vehicle) { toast.error('Select a vehicle'); return }
    if (!(Number(form.amount) > 0)) { toast.error('Enter amount received'); return }
    setSaving(true)
    try {
      const payload = {
        ...form,
        trip_count: Number(form.trip_count) || 1,
        distance_km: form.distance_km === '' ? null : form.distance_km,
        collected_at: form.collected_at ? new Date(form.collected_at).toISOString() : undefined,
      }
      const row = unwrapData(await api.post('/ambulance/collections/', payload))
      toast.success(`Saved ${row.receipt_no} · ₹${fmtMoney(row.amount)}`)
      if (printAfter) printAmbulanceReceipt(row)
      const v = vehicles.find((x) => x.id === form.vehicle)
      setForm(emptyForm(v))
      loadData()
    } catch (err) {
      toast.error(getApiErrorMessage(err))
    } finally {
      setSaving(false)
    }
  }

  async function confirmVoid(reason) {
    try {
      await api.post(`/ambulance/collections/${voidTarget.id}/void/`, { void_reason: reason })
      toast.success('Receipt cancelled')
      setVoidTarget(null)
      loadData()
    } catch (err) {
      toast.error(getApiErrorMessage(err))
    }
  }

  function exportCsv() {
    downloadCsv(
      `ambulance-collection-${dateFrom}-to-${dateTo}.csv`,
      ['Receipt', 'Date', 'Vehicle', 'Driver', 'Driver phone', 'Trips', 'Patient', 'From', 'To', 'Km', 'Mode', 'Amount', 'Received by', 'Remarks'],
      receipts.map((r) => [
        r.receipt_no, formatDateTime(r.collected_at), formatVehicleNo(r.vehicle_number), r.driver_name, r.driver_phone,
        r.trip_count, r.patient_name, r.trip_from, r.trip_to, r.distance_km ?? '', payModeLabel(r.payment_mode), r.amount,
        r.collected_by_name, r.remarks,
      ]),
    )
  }

  const totals = summary?.totals || {}
  const vehicleRows = summary?.vehicles || []
  const idleVehicles = vehicleRows.filter((r) => r.is_active && (r.days_since_last_collection == null || r.days_since_last_collection >= 3))
  const selectedVehicle = vehicles.find((v) => v.id === form.vehicle)

  return (
    <div className="max-w-[1400px] mx-auto space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <span className="w-9 h-9 rounded-xl bg-rose-100 text-rose-700 flex items-center justify-center"><Ambulance size={18} /></span>
          <div>
            <h2 className="text-base font-bold text-gray-900 leading-tight">Ambulance Collection</h2>
            <p className="text-[11px] text-gray-500">Money handed over by drivers, tracked per vehicle number</p>
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-1.5">
          {['today', 'yesterday', 'week', 'month'].map((k) => (
            <button key={k} type="button" onClick={() => setRange(quickRange(k))}
              className="text-[11px] font-semibold px-2 py-1 rounded bg-white border border-gray-200 text-gray-600 hover:border-rose-300 hover:text-rose-700 capitalize">
              {k}
            </button>
          ))}
          <input type="date" value={dateFrom} onChange={(e) => setRange([e.target.value, dateTo])} className="border border-gray-200 rounded-md px-2 py-1 text-xs" />
          <span className="text-[10px] text-gray-400">–</span>
          <input type="date" value={dateTo} onChange={(e) => setRange([dateFrom, e.target.value])} className="border border-gray-200 rounded-md px-2 py-1 text-xs" />
          <button type="button" onClick={loadData} disabled={loading} className="p-1.5 rounded-md bg-white border border-gray-200 text-gray-600 hover:bg-gray-50" title="Refresh">
            <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
          </button>
        </div>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-5 gap-2">
        {[
          { label: 'Collected', value: `₹${fmtMoney(totals.total)}`, sub: `${totals.entries || 0} receipt(s)`, cls: 'border-rose-200 bg-rose-50/60' },
          { label: 'Trips', value: totals.trips || 0, sub: 'In selected period', cls: 'border-sky-200 bg-sky-50/60' },
          { label: 'Cash', value: `₹${fmtMoney(totals.cash)}`, sub: 'To cash drawer', cls: 'border-emerald-200 bg-emerald-50/60' },
          { label: 'UPI / Other', value: `₹${fmtMoney(Number(totals.upi || 0) + Number(totals.other || 0))}`, sub: `UPI ₹${fmtMoney(totals.upi)}`, cls: 'border-indigo-200 bg-indigo-50/60' },
          { label: 'Ambulances', value: activeVehicles.length, sub: idleVehicles.length ? `${idleVehicles.length} idle 3+ days` : 'All reporting', cls: idleVehicles.length ? 'border-amber-300 bg-amber-50/70' : 'border-gray-200 bg-white' },
        ].map((c) => (
          <div key={c.label} className={`rounded-xl border px-3 py-2 ${c.cls}`}>
            <p className="text-[10px] font-semibold uppercase text-gray-500">{c.label}</p>
            <p className="text-lg font-bold text-gray-900 tabular-nums leading-tight">{c.value}</p>
            <p className="text-[10px] text-gray-600">{c.sub}</p>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-[360px_1fr] gap-3 items-start">
        <div className="bg-white border border-gray-200 rounded-xl shadow-sm p-4 space-y-3">
          <h3 className="text-sm font-bold text-gray-900">New collection</h3>
          {activeVehicles.length === 0 ? (
            <div className="text-xs text-gray-500 bg-gray-50 border border-dashed border-gray-300 rounded-lg p-3">
              No ambulances registered yet.
              <button type="button" onClick={() => setVehicleModal({})} className="ml-1 font-bold text-rose-700 hover:underline">Add one</button>
            </div>
          ) : (
            <div>
              <label className={labelCls}>Vehicle *</label>
              <div className="flex flex-wrap gap-1.5">
                {activeVehicles.map((v) => (
                  <button key={v.id} type="button" onClick={() => pickVehicle(v.id)}
                    className={`px-2 py-1 rounded-lg border text-xs font-mono font-bold ${form.vehicle === v.id ? 'bg-rose-600 border-rose-600 text-white' : 'bg-white border-gray-200 text-gray-700 hover:border-rose-300'}`}
                    title={v.label || v.driver_name}>
                    {formatVehicleNo(v.vehicle_number)}
                  </button>
                ))}
              </div>
              {selectedVehicle?.label && <p className="text-[10px] text-gray-500 mt-1">{selectedVehicle.label}</p>}
            </div>
          )}
          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className={labelCls}>Driver</label>
              <input value={form.driver_name} onChange={setField('driver_name')} className={inputCls} />
            </div>
            <div>
              <label className={labelCls}>Driver phone</label>
              <input value={form.driver_phone} onChange={setField('driver_phone')} className={inputCls} />
            </div>
            <div>
              <label className={labelCls}>Amount received (₹) *</label>
              <input type="number" min="0" step="0.01" value={form.amount} onChange={setField('amount')} className={`${inputCls} font-bold`} />
            </div>
            <div>
              <label className={labelCls}>Trips</label>
              <input type="number" min="1" value={form.trip_count} onChange={setField('trip_count')} className={inputCls} />
            </div>
          </div>
          <div>
            <label className={labelCls}>Payment mode</label>
            <div className="flex flex-wrap gap-1">
              {PAYMENT_MODES.map((m) => (
                <button key={m.id} type="button" onClick={() => setForm((f) => ({ ...f, payment_mode: m.id }))}
                  className={`px-2.5 py-1 rounded-md text-xs font-semibold border ${form.payment_mode === m.id ? 'bg-gray-900 text-white border-gray-900' : 'bg-white text-gray-600 border-gray-200'}`}>
                  {m.label}
                </button>
              ))}
            </div>
          </div>
          <details className="group">
            <summary className="text-[11px] font-semibold text-rose-700 cursor-pointer select-none">Trip details (optional)</summary>
            <div className="grid grid-cols-2 gap-2 mt-2">
              <div className="col-span-2">
                <label className={labelCls}>Patient</label>
                <input value={form.patient_name} onChange={setField('patient_name')} className={inputCls} />
              </div>
              <div>
                <label className={labelCls}>From</label>
                <input value={form.trip_from} onChange={setField('trip_from')} className={inputCls} />
              </div>
              <div>
                <label className={labelCls}>To</label>
                <input value={form.trip_to} onChange={setField('trip_to')} className={inputCls} />
              </div>
              <div>
                <label className={labelCls}>Distance (km)</label>
                <input type="number" min="0" step="0.1" value={form.distance_km} onChange={setField('distance_km')} className={inputCls} />
              </div>
            </div>
          </details>
          <div className="grid grid-cols-2 gap-2">
            <div className="col-span-2">
              <label className={labelCls}>Remarks</label>
              <input value={form.remarks} onChange={setField('remarks')} className={inputCls} />
            </div>
            <div className="col-span-2">
              <label className={labelCls}>Received at</label>
              <input type="datetime-local" value={form.collected_at} onChange={setField('collected_at')} className={inputCls} />
            </div>
          </div>
          <div className="flex gap-2 pt-1">
            <button type="button" disabled={saving} onClick={() => submit(true)}
              className="flex-1 flex items-center justify-center gap-1.5 bg-rose-600 text-white py-2 rounded-lg text-sm font-bold hover:bg-rose-700 disabled:opacity-50">
              <Printer size={14} /> Save &amp; print
            </button>
            <button type="button" disabled={saving} onClick={() => submit(false)}
              className="px-4 py-2 rounded-lg bg-gray-100 text-gray-700 text-sm font-semibold hover:bg-gray-200 disabled:opacity-50">
              Save
            </button>
          </div>
        </div>

        <div className="bg-white border border-gray-200 rounded-xl shadow-sm overflow-hidden">
          <div className="flex flex-wrap items-center justify-between border-b border-gray-100 px-2">
            <div className="flex">
              {[
                { id: 'summary', label: 'Vehicle-wise' },
                { id: 'receipts', label: `Receipts (${receipts.length})` },
                { id: 'vehicles', label: `Ambulances (${vehicles.length})` },
              ].map((t) => (
                <button key={t.id} type="button" onClick={() => setTab(t.id)}
                  className={`px-3 py-2.5 text-xs font-semibold ${tab === t.id ? 'text-rose-700 border-b-2 border-rose-600' : 'text-gray-500 hover:text-gray-700'}`}>
                  {t.label}
                </button>
              ))}
            </div>
            <div className="flex items-center gap-1.5 py-1.5">
              {tab === 'receipts' && (
                <>
                  <div className="relative">
                    <Search size={12} className="absolute left-2 top-1/2 -translate-y-1/2 text-gray-400" />
                    <input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Receipt, driver, patient…" className="border border-gray-200 rounded-md pl-6 pr-2 py-1 text-xs w-44" />
                  </div>
                  <select value={vehicleFilter} onChange={(e) => setVehicleFilter(e.target.value)} className="border border-gray-200 rounded-md px-2 py-1 text-xs">
                    <option value="">All vehicles</option>
                    {vehicles.map((v) => <option key={v.id} value={v.id}>{formatVehicleNo(v.vehicle_number)}</option>)}
                  </select>
                  <button type="button" onClick={exportCsv} className="flex items-center gap-1 px-2 py-1 rounded-md border border-gray-200 text-xs font-semibold text-gray-700 hover:bg-gray-50">
                    <Download size={12} /> CSV
                  </button>
                </>
              )}
              {tab === 'vehicles' && (
                <button type="button" onClick={() => setVehicleModal({})} className="flex items-center gap-1 px-2.5 py-1 rounded-md bg-rose-600 text-white text-xs font-bold hover:bg-rose-700">
                  <Plus size={12} /> Add ambulance
                </button>
              )}
            </div>
          </div>

          <div className="overflow-x-auto max-h-[min(68vh,700px)] overflow-y-auto">
            {tab === 'summary' && (
              <table className="w-full text-sm">
                <thead className="bg-gray-50 sticky top-0 text-[10px] uppercase text-gray-500">
                  <tr>
                    <th className="px-3 py-2 text-left">Vehicle</th>
                    <th className="px-3 py-2 text-left">Driver</th>
                    <th className="px-3 py-2 text-center">Trips</th>
                    <th className="px-3 py-2 text-right">Cash</th>
                    <th className="px-3 py-2 text-right">UPI/Other</th>
                    <th className="px-3 py-2 text-right">Total</th>
                    <th className="px-3 py-2 text-right">Shortfall</th>
                    <th className="px-3 py-2 text-left">Last collection</th>
                    <th className="px-3 py-2" />
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-50">
                  {vehicleRows.length === 0 ? (
                    <tr><td colSpan={9} className="px-3 py-8 text-center text-gray-400">No ambulances yet</td></tr>
                  ) : vehicleRows.map((r) => (
                    <tr key={r.vehicle_id} className={`hover:bg-rose-50/40 ${r.is_active ? '' : 'opacity-60'}`}>
                      <td className="px-3 py-2">
                        <p className="font-mono font-bold text-gray-900">{formatVehicleNo(r.vehicle_number)}</p>
                        {r.label && <p className="text-[10px] text-gray-500">{r.label}</p>}
                      </td>
                      <td className="px-3 py-2 text-xs">
                        {r.driver_name || '—'}
                        {r.driver_phone && (
                          <a href={`tel:${r.driver_phone}`} className="ml-1 inline-flex items-center text-emerald-700" title="Call driver"><Phone size={11} /></a>
                        )}
                      </td>
                      <td className="px-3 py-2 text-center tabular-nums">{r.trips}</td>
                      <td className="px-3 py-2 text-right tabular-nums">₹{fmtMoney(r.cash)}</td>
                      <td className="px-3 py-2 text-right tabular-nums">₹{fmtMoney(Number(r.upi) + Number(r.other))}</td>
                      <td className="px-3 py-2 text-right font-bold text-rose-700 tabular-nums">₹{fmtMoney(r.total)}</td>
                      <td className="px-3 py-2 text-right tabular-nums">
                        {Number(r.expected) > 0
                          ? (Number(r.shortfall) > 0
                            ? <span className="text-amber-700 font-semibold">₹{fmtMoney(r.shortfall)}</span>
                            : <span className="text-emerald-700 font-semibold">Target met</span>)
                          : <span className="text-gray-300">—</span>}
                      </td>
                      <td className="px-3 py-2"><LastSeenBadge row={r} /></td>
                      <td className="px-3 py-2 text-right whitespace-nowrap">
                        {r.is_active && (
                          <button type="button" onClick={() => pickVehicle(r.vehicle_id)} className="text-[11px] font-bold text-rose-700 hover:underline mr-2">Collect</button>
                        )}
                        <button type="button" onClick={() => { setVehicleFilter(r.vehicle_id); setTab('receipts') }} className="text-[11px] font-semibold text-gray-500 hover:underline">Receipts</button>
                      </td>
                    </tr>
                  ))}
                </tbody>
                {vehicleRows.length > 0 && (
                  <tfoot className="bg-gray-50 border-t border-gray-200 text-sm font-bold">
                    <tr>
                      <td className="px-3 py-2" colSpan={2}>Total</td>
                      <td className="px-3 py-2 text-center tabular-nums">{totals.trips || 0}</td>
                      <td className="px-3 py-2 text-right tabular-nums">₹{fmtMoney(totals.cash)}</td>
                      <td className="px-3 py-2 text-right tabular-nums">₹{fmtMoney(Number(totals.upi || 0) + Number(totals.other || 0))}</td>
                      <td className="px-3 py-2 text-right text-rose-700 tabular-nums">₹{fmtMoney(totals.total)}</td>
                      <td colSpan={3} />
                    </tr>
                  </tfoot>
                )}
              </table>
            )}

            {tab === 'receipts' && (
              <table className="w-full text-sm">
                <thead className="bg-gray-50 sticky top-0 text-[10px] uppercase text-gray-500">
                  <tr>
                    <th className="px-3 py-2 text-left">Receipt</th>
                    <th className="px-3 py-2 text-left">Date</th>
                    <th className="px-3 py-2 text-left">Vehicle</th>
                    <th className="px-3 py-2 text-left">Driver</th>
                    <th className="px-3 py-2 text-left">Trip</th>
                    <th className="px-3 py-2 text-left">Mode</th>
                    <th className="px-3 py-2 text-right">Amount</th>
                    <th className="px-3 py-2 text-left">By</th>
                    <th className="px-3 py-2" />
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-50">
                  {receipts.length === 0 ? (
                    <tr><td colSpan={9} className="px-3 py-8 text-center text-gray-400">{loading ? 'Loading…' : 'No collections in this period'}</td></tr>
                  ) : receipts.map((r) => (
                    <tr key={r.id} className="hover:bg-rose-50/40">
                      <td className="px-3 py-2 font-mono text-xs font-semibold">{r.receipt_no}</td>
                      <td className="px-3 py-2 text-xs whitespace-nowrap tabular-nums">{formatDateTime(r.collected_at)}</td>
                      <td className="px-3 py-2 font-mono text-xs font-bold">{formatVehicleNo(r.vehicle_number)}</td>
                      <td className="px-3 py-2 text-xs">{r.driver_name || '—'}</td>
                      <td className="px-3 py-2 text-xs text-gray-600">
                        {r.trip_count} trip{r.trip_count > 1 ? 's' : ''}
                        {r.patient_name ? ` · ${r.patient_name}` : ''}
                        {(r.trip_from || r.trip_to) ? ` · ${[r.trip_from, r.trip_to].filter(Boolean).join(' → ')}` : ''}
                      </td>
                      <td className="px-3 py-2 text-xs uppercase">{r.payment_mode}</td>
                      <td className="px-3 py-2 text-right font-bold text-rose-700 tabular-nums">₹{fmtMoney(r.amount)}</td>
                      <td className="px-3 py-2 text-xs">{r.collected_by_name}</td>
                      <td className="px-3 py-2 text-right whitespace-nowrap">
                        <button type="button" onClick={() => printAmbulanceReceipt(r)} className="p-1 text-gray-500 hover:text-gray-900" title="Print receipt"><Printer size={14} /></button>
                        <button type="button" onClick={() => setVoidTarget(r)} className="p-1 text-gray-400 hover:text-rose-600" title="Cancel receipt"><XCircle size={14} /></button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}

            {tab === 'vehicles' && (
              <table className="w-full text-sm">
                <thead className="bg-gray-50 sticky top-0 text-[10px] uppercase text-gray-500">
                  <tr>
                    <th className="px-3 py-2 text-left">Vehicle</th>
                    <th className="px-3 py-2 text-left">Label</th>
                    <th className="px-3 py-2 text-left">Default driver</th>
                    <th className="px-3 py-2 text-right">Daily target</th>
                    <th className="px-3 py-2 text-left">Status</th>
                    <th className="px-3 py-2" />
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-50">
                  {vehicles.length === 0 ? (
                    <tr><td colSpan={6} className="px-3 py-8 text-center text-gray-400">No ambulances registered</td></tr>
                  ) : vehicles.map((v) => (
                    <tr key={v.id} className="hover:bg-gray-50">
                      <td className="px-3 py-2 font-mono font-bold">{formatVehicleNo(v.vehicle_number)}</td>
                      <td className="px-3 py-2 text-xs">{v.label || '—'}</td>
                      <td className="px-3 py-2 text-xs">{v.driver_name || '—'}{v.driver_phone ? ` · ${v.driver_phone}` : ''}</td>
                      <td className="px-3 py-2 text-right text-xs tabular-nums">{Number(v.expected_daily_amount) > 0 ? `₹${fmtMoney(v.expected_daily_amount)}` : '—'}</td>
                      <td className="px-3 py-2">
                        <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${v.is_active ? 'bg-emerald-100 text-emerald-700' : 'bg-gray-100 text-gray-500'}`}>
                          {v.is_active ? 'Active' : 'Inactive'}
                        </span>
                      </td>
                      <td className="px-3 py-2 text-right">
                        <button type="button" onClick={() => setVehicleModal(v)} className="p-1 text-gray-500 hover:text-gray-900" title="Edit"><Pencil size={14} /></button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>

          {tab === 'summary' && idleVehicles.length > 0 && (
            <div className="flex items-start gap-2 px-3 py-2 bg-amber-50 border-t border-amber-200 text-[11px] text-amber-800">
              <AlertTriangle size={14} className="shrink-0 mt-0.5" />
              <span>
                No collection for 3+ days from{' '}
                <strong>{idleVehicles.map((r) => formatVehicleNo(r.vehicle_number)).join(', ')}</strong>.
                Follow up with the driver.
              </span>
            </div>
          )}
        </div>
      </div>

      {vehicleModal && (
        <VehicleModal
          vehicle={vehicleModal}
          onClose={() => setVehicleModal(null)}
          onSaved={() => { setVehicleModal(null); loadVehicles(); loadData() }}
        />
      )}
      {voidTarget && (
        <VoidReceiptModal
          title="Cancel ambulance receipt"
          receiptNo={voidTarget.receipt_no}
          onClose={() => setVoidTarget(null)}
          onConfirm={confirmVoid}
        />
      )}
    </div>
  )
}
