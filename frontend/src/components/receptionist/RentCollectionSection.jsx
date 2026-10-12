import React, { useCallback, useEffect, useMemo, useState } from 'react'
import toast from 'react-hot-toast'
import { format } from 'date-fns'
import { Download, History, MessageCircle, Pencil, Phone, Plus, Printer, RefreshCw, Search, Storefront, X, XCircle } from 'lucide-react'
import api from '../../api'
import { getApiErrorMessage } from '../../utils/apiError'
import { formatDateTime } from '../../utils/dateTimeFormat'
import { payModeLabel, printCollectionReceipt } from '../../utils/collectionReceiptPrint'
import { getPaymentSlipProfile, loadReceptionPortalProfileCache } from '../../utils/receptionPortalProfile'
import { VoidReceiptModal } from './AmbulanceCollectionSection'
import {
  PAYMENT_MODES,
  digitsOnlyPhone,
  downloadCsv,
  fmtMoney,
  monthLabel,
  quickRange,
  shopLabel,
  toDateTimeInputValue,
  todayStr,
  unwrapData,
  unwrapRows,
} from './collectionSectionUtils'

const RENT_PAYMENT_MODES = [...PAYMENT_MODES.slice(0, 4), { id: 'cheque', label: 'Cheque' }, PAYMENT_MODES[4]]

const inputCls = 'w-full border border-gray-200 rounded-lg px-2.5 py-1.5 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-violet-200 focus:border-violet-300'
const labelCls = 'block text-[11px] font-semibold text-gray-500 mb-0.5'

const currentMonth = () => format(new Date(), 'yyyy-MM')

export function printRentReceipt(row) {
  return printCollectionReceipt({
    title: 'Rent Receipt',
    accent: '#6d28d9',
    fields: [
      { label: 'Receipt No', value: row.receipt_no },
      { label: 'Date', value: formatDateTime(row.collected_at) },
      { label: 'Rent For', value: monthLabel(row.rent_month) },
      { label: 'Shop', value: shopLabel(row) },
      { label: 'Owner / Tenant', value: row.owner_name },
      { label: 'Paid By', value: row.paid_by },
      { label: 'Monthly Rent', value: `₹${fmtMoney(row.monthly_rent)}` },
      { label: 'Pay Mode', value: payModeLabel(row.payment_mode) },
      { label: 'Reference', value: row.reference_no },
      { label: 'Received By', value: row.collected_by_name },
      { label: 'Remarks', value: row.remarks, span: 2 },
    ],
    amount: row.amount,
    note: 'Rent received with thanks.',
  })
}

function reminderMessage(row, hospitalName) {
  const months = (row.unpaid_months || []).map(monthLabel).join(', ')
  return `Dear ${row.owner_name}, rent of Rs. ${fmtMoney(row.pending)} for ${shopLabel(row)} is pending`
    + `${months ? ` (${months})` : ''}. Kindly pay at the hospital reception at the earliest. - ${hospitalName}`
}

function ShopModal({ shop, onClose, onSaved }) {
  const isEdit = Boolean(shop?.id)
  const [form, setForm] = useState(() => ({
    shop_name: shop?.shop_name || '',
    shop_number: shop?.shop_number || '',
    owner_name: shop?.owner_name || '',
    owner_phone: shop?.owner_phone || '',
    monthly_rent: shop?.monthly_rent ?? '',
    due_day: shop?.due_day ?? 5,
    rent_start_date: shop?.rent_start_date || format(new Date(), 'yyyy-MM-01'),
    security_deposit: shop?.security_deposit ?? '',
    notes: shop?.notes || '',
    is_active: shop?.is_active ?? true,
  }))
  const [saving, setSaving] = useState(false)
  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.type === 'checkbox' ? e.target.checked : e.target.value }))

  async function save(e) {
    e.preventDefault()
    if (!form.shop_name.trim() || !form.owner_name.trim()) { toast.error('Shop name and owner are required'); return }
    if (!(Number(form.monthly_rent) > 0)) { toast.error('Enter monthly rent'); return }
    setSaving(true)
    try {
      const payload = {
        ...form,
        due_day: Math.min(Math.max(Number(form.due_day) || 1, 1), 28),
        security_deposit: form.security_deposit === '' ? '0' : form.security_deposit,
      }
      const res = isEdit ? await api.patch(`/rent/shops/${shop.id}/`, payload) : await api.post('/rent/shops/', payload)
      toast.success(isEdit ? 'Shop updated' : 'Shop added')
      onSaved(unwrapData(res))
    } catch (err) {
      toast.error(getApiErrorMessage(err))
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="fixed inset-0 z-[1400] bg-slate-900/50 flex items-center justify-center p-4">
      <form onSubmit={save} className="bg-white rounded-2xl shadow-2xl w-full max-w-lg p-5 space-y-3">
        <div className="flex items-center justify-between">
          <h3 className="font-bold text-gray-900">{isEdit ? 'Edit shop' : 'Add shop'}</h3>
          <button type="button" onClick={onClose} className="text-gray-400 hover:text-gray-700"><X size={18} /></button>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className={labelCls}>Shop name *</label>
            <input autoFocus value={form.shop_name} onChange={set('shop_name')} placeholder="e.g. Medical Store" className={inputCls} />
          </div>
          <div>
            <label className={labelCls}>Shop no. / location</label>
            <input value={form.shop_number} onChange={set('shop_number')} placeholder="e.g. G-2, Ground floor" className={inputCls} />
          </div>
          <div>
            <label className={labelCls}>Owner / tenant *</label>
            <input value={form.owner_name} onChange={set('owner_name')} className={inputCls} />
          </div>
          <div>
            <label className={labelCls}>Owner phone</label>
            <input value={form.owner_phone} onChange={set('owner_phone')} className={inputCls} />
          </div>
          <div>
            <label className={labelCls}>Monthly rent (₹) *</label>
            <input type="number" min="0" step="0.01" value={form.monthly_rent} onChange={set('monthly_rent')} className={inputCls} />
          </div>
          <div>
            <label className={labelCls}>Due day of month (1–28)</label>
            <input type="number" min="1" max="28" value={form.due_day} onChange={set('due_day')} className={inputCls} />
          </div>
          <div>
            <label className={labelCls}>Rent starts from *</label>
            <input type="date" value={form.rent_start_date} onChange={set('rent_start_date')} className={inputCls} />
          </div>
          <div>
            <label className={labelCls}>Security deposit (₹)</label>
            <input type="number" min="0" step="0.01" value={form.security_deposit} onChange={set('security_deposit')} className={inputCls} />
          </div>
          <div className="col-span-2">
            <label className={labelCls}>Notes</label>
            <input value={form.notes} onChange={set('notes')} placeholder="Agreement details, increments…" className={inputCls} />
          </div>
          <label className="col-span-2 flex items-center gap-2 text-sm text-gray-700">
            <input type="checkbox" checked={form.is_active} onChange={set('is_active')} /> Active (rent is being charged)
          </label>
        </div>
        {isEdit && (
          <p className="text-[11px] text-amber-700 bg-amber-50 border border-amber-200 rounded-lg px-2.5 py-1.5">
            Changing monthly rent or start date recalculates pending rent for all past months.
          </p>
        )}
        <div className="flex justify-end gap-2 pt-1">
          <button type="button" onClick={onClose} className="px-4 py-2 rounded-lg bg-gray-100 text-sm font-semibold text-gray-700">Cancel</button>
          <button type="submit" disabled={saving} className="px-4 py-2 rounded-lg bg-violet-600 text-white text-sm font-bold hover:bg-violet-700 disabled:opacity-50">
            {saving ? 'Saving…' : 'Save'}
          </button>
        </div>
      </form>
    </div>
  )
}

function LedgerModal({ shopId, onClose, onCollect }) {
  const [ledger, setLedger] = useState(null)
  useEffect(() => {
    api.get(`/rent/shops/${shopId}/ledger/`)
      .then((res) => setLedger(unwrapData(res)))
      .catch(() => toast.error('Failed to load ledger'))
  }, [shopId])

  const statusCls = {
    paid: 'bg-emerald-100 text-emerald-700',
    partial: 'bg-amber-100 text-amber-700',
    unpaid: 'bg-rose-100 text-rose-700',
    advance: 'bg-sky-100 text-sky-700',
  }

  return (
    <div className="fixed inset-0 z-[1400] bg-slate-900/50 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-2xl max-h-[85vh] flex flex-col overflow-hidden">
        <div className="px-5 py-3 border-b border-gray-100 flex items-center justify-between">
          <div>
            <h3 className="font-bold text-gray-900">{ledger ? shopLabel(ledger.shop) : 'Rent ledger'}</h3>
            {ledger && <p className="text-[11px] text-gray-500">{ledger.shop.owner_name} · ₹{fmtMoney(ledger.shop.monthly_rent)}/month · due on day {ledger.shop.due_day}</p>}
          </div>
          <button type="button" onClick={onClose} className="text-gray-400 hover:text-gray-700"><X size={18} /></button>
        </div>
        {!ledger ? (
          <p className="p-8 text-center text-gray-400 text-sm">Loading…</p>
        ) : (
          <>
            <div className="grid grid-cols-4 gap-2 px-5 py-3 text-center">
              {[
                ['Expected', ledger.total_expected, 'text-gray-900'],
                ['Paid', ledger.total_paid, 'text-emerald-700'],
                ['Pending', ledger.pending, 'text-rose-700'],
                ['Advance', ledger.advance_paid, 'text-sky-700'],
              ].map(([label, val, cls]) => (
                <div key={label} className="rounded-lg bg-gray-50 border border-gray-100 py-1.5">
                  <p className="text-[10px] uppercase font-semibold text-gray-500">{label}</p>
                  <p className={`font-bold tabular-nums ${cls}`}>₹{fmtMoney(val)}</p>
                </div>
              ))}
            </div>
            <div className="overflow-y-auto flex-1">
              <table className="w-full text-sm">
                <thead className="bg-gray-50 sticky top-0 text-[10px] uppercase text-gray-500">
                  <tr>
                    <th className="px-4 py-2 text-left">Month</th>
                    <th className="px-4 py-2 text-left">Due date</th>
                    <th className="px-4 py-2 text-right">Rent</th>
                    <th className="px-4 py-2 text-right">Paid</th>
                    <th className="px-4 py-2 text-right">Balance</th>
                    <th className="px-4 py-2 text-left">Status</th>
                    <th className="px-4 py-2" />
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-50">
                  {[...ledger.months].reverse().map((m) => (
                    <tr key={m.month}>
                      <td className="px-4 py-1.5 font-semibold">{monthLabel(m.month)}</td>
                      <td className="px-4 py-1.5 text-xs text-gray-500">{format(new Date(`${m.due_date}T12:00:00`), 'd MMM yyyy')}</td>
                      <td className="px-4 py-1.5 text-right tabular-nums">₹{fmtMoney(m.expected)}</td>
                      <td className="px-4 py-1.5 text-right tabular-nums">₹{fmtMoney(m.paid)}</td>
                      <td className="px-4 py-1.5 text-right tabular-nums font-semibold">{Number(m.balance) > 0 ? `₹${fmtMoney(m.balance)}` : '—'}</td>
                      <td className="px-4 py-1.5">
                        <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded capitalize ${statusCls[m.status]}`}>{m.status}</span>
                        {m.overdue && <span className="ml-1 text-[10px] font-bold text-rose-600">Overdue</span>}
                      </td>
                      <td className="px-4 py-1.5 text-right">
                        {Number(m.balance) > 0 && m.status !== 'advance' && (
                          <button type="button" onClick={() => onCollect(ledger.shop.id, m.month.slice(0, 7), m.balance)} className="text-[11px] font-bold text-violet-700 hover:underline">Collect</button>
                        )}
                      </td>
                    </tr>
                  ))}
                  {ledger.months.length === 0 && (
                    <tr><td colSpan={7} className="px-4 py-6 text-center text-gray-400">Rent has not started yet</td></tr>
                  )}
                </tbody>
              </table>
            </div>
          </>
        )}
      </div>
    </div>
  )
}

function emptyForm() {
  return {
    shop: '',
    rent_month: currentMonth(),
    amount: '',
    payment_mode: 'cash',
    paid_by: '',
    reference_no: '',
    remarks: '',
    collected_at: toDateTimeInputValue(new Date()),
  }
}

export default function RentCollectionSection() {
  const [shops, setShops] = useState([])
  const [pending, setPending] = useState(null)
  const [receipts, setReceipts] = useState([])
  const [[dateFrom, dateTo], setRange] = useState(() => quickRange('month'))
  const [tab, setTab] = useState('pending')
  const [shopFilter, setShopFilter] = useState('')
  const [search, setSearch] = useState('')
  const [pendingOnly, setPendingOnly] = useState(true)
  const [loading, setLoading] = useState(false)
  const [form, setForm] = useState(emptyForm)
  const [shopLedger, setShopLedger] = useState(null)
  const [saving, setSaving] = useState(false)
  const [shopModal, setShopModal] = useState(null)
  const [ledgerShopId, setLedgerShopId] = useState(null)
  const [voidTarget, setVoidTarget] = useState(null)

  const activeShops = useMemo(() => shops.filter((s) => s.is_active), [shops])

  const loadShops = useCallback(async () => {
    try {
      setShops(unwrapRows(await api.get('/rent/shops/')))
    } catch {
      toast.error('Failed to load shops')
    }
  }, [])

  const loadPending = useCallback(async () => {
    try {
      setPending(unwrapData(await api.get(`/rent/shops/pending/?as_of=${todayStr()}`)))
    } catch {
      toast.error('Failed to load pending rent')
    }
  }, [])

  const loadReceipts = useCallback(async () => {
    setLoading(true)
    try {
      const params = new URLSearchParams({
        limit: '500',
        collected_at__date__gte: dateFrom,
        collected_at__date__lte: dateTo,
      })
      if (shopFilter) params.set('shop', shopFilter)
      if (search.trim()) params.set('search', search.trim())
      setReceipts(unwrapRows(await api.get(`/rent/collections/?${params}`)))
    } catch {
      toast.error('Failed to load rent receipts')
    } finally {
      setLoading(false)
    }
  }, [dateFrom, dateTo, shopFilter, search])

  useEffect(() => { loadShops(); loadPending() }, [loadShops, loadPending])
  useEffect(() => {
    const t = setTimeout(loadReceipts, 250)
    return () => clearTimeout(t)
  }, [loadReceipts])

  const refreshAll = useCallback(() => {
    loadShops()
    loadPending()
    loadReceipts()
  }, [loadShops, loadPending, loadReceipts])

  const balanceFor = useCallback((ledger, month) => {
    const row = ledger?.months?.find((m) => m.month.slice(0, 7) === month)
    if (row) return row.balance
    return ledger?.shop?.monthly_rent ?? ''
  }, [])

  async function selectShop(shopId, month = null, amount = null) {
    const shop = shops.find((s) => s.id === shopId)
    setForm((f) => ({ ...f, shop: shopId, paid_by: shop?.owner_name || '', rent_month: month || f.rent_month, amount: amount ?? '' }))
    setShopLedger(null)
    if (!shopId) return
    try {
      const ledger = unwrapData(await api.get(`/rent/shops/${shopId}/ledger/`))
      setShopLedger(ledger)
      const targetMonth = month || ledger.oldest_unpaid_month?.slice(0, 7) || currentMonth()
      setForm((f) => (f.shop !== shopId ? f : {
        ...f,
        rent_month: targetMonth,
        amount: amount ?? String(Number(balanceFor(ledger, targetMonth)) || ''),
      }))
    } catch {
      toast.error('Failed to load shop ledger')
    }
  }

  function changeMonth(month) {
    setForm((f) => ({ ...f, rent_month: month, amount: shopLedger ? String(Number(balanceFor(shopLedger, month)) || '') : f.amount }))
  }

  async function submit(printAfter) {
    if (!form.shop) { toast.error('Select a shop'); return }
    if (!form.rent_month) { toast.error('Select rent month'); return }
    if (!(Number(form.amount) > 0)) { toast.error('Enter amount'); return }
    setSaving(true)
    try {
      const payload = { ...form, collected_at: form.collected_at ? new Date(form.collected_at).toISOString() : undefined }
      const row = unwrapData(await api.post('/rent/collections/', payload))
      toast.success(`Saved ${row.receipt_no} · ₹${fmtMoney(row.amount)}`)
      if (printAfter) printRentReceipt(row)
      setForm(emptyForm())
      setShopLedger(null)
      refreshAll()
    } catch (err) {
      toast.error(getApiErrorMessage(err))
    } finally {
      setSaving(false)
    }
  }

  async function confirmVoid(reason) {
    try {
      await api.post(`/rent/collections/${voidTarget.id}/void/`, { void_reason: reason })
      toast.success('Receipt cancelled')
      setVoidTarget(null)
      refreshAll()
    } catch (err) {
      toast.error(getApiErrorMessage(err))
    }
  }

  async function sendReminder(row) {
    const phone = digitsOnlyPhone(row.owner_phone)
    if (!phone) { toast.error('No phone number saved for this owner'); return }
    await loadReceptionPortalProfileCache()
    const msg = reminderMessage(row, getPaymentSlipProfile().hospital_name || 'Hospital')
    window.open(`https://wa.me/${phone}?text=${encodeURIComponent(msg)}`, '_blank', 'noopener')
  }

  function exportPendingCsv() {
    downloadCsv(
      `pending-rent-${todayStr()}.csv`,
      ['Shop', 'Shop no', 'Owner', 'Phone', 'Monthly rent', 'Unpaid months', 'Overdue months', 'Pending', 'Last paid'],
      (pending?.shops || []).map((r) => [
        r.shop_name, r.shop_number, r.owner_name, r.owner_phone, r.monthly_rent,
        (r.unpaid_months || []).map(monthLabel).join(' / '), r.overdue_months, r.pending,
        r.last_paid_at ? formatDateTime(r.last_paid_at) : '',
      ]),
    )
  }

  function exportReceiptsCsv() {
    downloadCsv(
      `rent-receipts-${dateFrom}-to-${dateTo}.csv`,
      ['Receipt', 'Date', 'Shop', 'Owner', 'Rent month', 'Mode', 'Reference', 'Amount', 'Paid by', 'Received by'],
      receipts.map((r) => [
        r.receipt_no, formatDateTime(r.collected_at), shopLabel(r), r.owner_name, monthLabel(r.rent_month),
        payModeLabel(r.payment_mode), r.reference_no, r.amount, r.paid_by, r.collected_by_name,
      ]),
    )
  }

  const pendingRows = useMemo(() => {
    const rows = pending?.shops || []
    const q = search.trim().toLowerCase()
    return rows
      .filter((r) => !pendingOnly || Number(r.pending) > 0)
      .filter((r) => !q || [r.shop_name, r.shop_number, r.owner_name, r.owner_phone].some((v) => String(v || '').toLowerCase().includes(q)))
      .sort((a, b) => Number(b.pending) - Number(a.pending))
  }, [pending, pendingOnly, search])

  const receiptsTotal = receipts.reduce((s, r) => s + (Number(r.amount) || 0), 0)
  const monthlyRoll = activeShops.reduce((s, r) => s + (Number(r.monthly_rent) || 0), 0)
  const overdueShops = (pending?.shops || []).filter((r) => r.overdue_months > 0).length
  const selectedShop = shops.find((s) => s.id === form.shop)
  const selectedPending = pending?.shops?.find((r) => r.id === form.shop)

  return (
    <div className="max-w-[1400px] mx-auto space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <span className="w-9 h-9 rounded-xl bg-violet-100 text-violet-700 flex items-center justify-center"><Storefront size={18} /></span>
          <div>
            <h2 className="text-base font-bold text-gray-900 leading-tight">Rent Collection</h2>
            <p className="text-[11px] text-gray-500">Shop-wise rent, owner-wise tracking and pending dues</p>
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-1.5">
          {['today', 'week', 'month'].map((k) => (
            <button key={k} type="button" onClick={() => setRange(quickRange(k))}
              className="text-[11px] font-semibold px-2 py-1 rounded bg-white border border-gray-200 text-gray-600 hover:border-violet-300 hover:text-violet-700 capitalize">
              {k}
            </button>
          ))}
          <input type="date" value={dateFrom} onChange={(e) => setRange([e.target.value, dateTo])} className="border border-gray-200 rounded-md px-2 py-1 text-xs" />
          <span className="text-[10px] text-gray-400">–</span>
          <input type="date" value={dateTo} onChange={(e) => setRange([dateFrom, e.target.value])} className="border border-gray-200 rounded-md px-2 py-1 text-xs" />
          <button type="button" onClick={refreshAll} disabled={loading} className="p-1.5 rounded-md bg-white border border-gray-200 text-gray-600 hover:bg-gray-50" title="Refresh">
            <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
          </button>
        </div>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-2">
        {[
          { label: 'Collected (period)', value: `₹${fmtMoney(receiptsTotal)}`, sub: `${receipts.length} receipt(s)`, cls: 'border-violet-200 bg-violet-50/60' },
          { label: 'Pending rent', value: `₹${fmtMoney(pending?.totals?.pending)}`, sub: `${pending?.totals?.shops_with_pending || 0} shop(s) with dues`, cls: Number(pending?.totals?.pending) > 0 ? 'border-rose-300 bg-rose-50/70' : 'border-emerald-200 bg-emerald-50/60' },
          { label: 'Overdue shops', value: overdueShops, sub: 'Past due date', cls: overdueShops ? 'border-amber-300 bg-amber-50/70' : 'border-gray-200 bg-white' },
          { label: 'Monthly rent roll', value: `₹${fmtMoney(monthlyRoll)}`, sub: `${activeShops.length} active shop(s)`, cls: 'border-gray-200 bg-white' },
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
          <h3 className="text-sm font-bold text-gray-900">Collect rent</h3>
          {activeShops.length === 0 ? (
            <div className="text-xs text-gray-500 bg-gray-50 border border-dashed border-gray-300 rounded-lg p-3">
              No shops added yet.
              <button type="button" onClick={() => setShopModal({})} className="ml-1 font-bold text-violet-700 hover:underline">Add a shop</button>
            </div>
          ) : (
            <div>
              <label className={labelCls}>Shop *</label>
              <select value={form.shop} onChange={(e) => selectShop(e.target.value)} className={inputCls}>
                <option value="">Select shop…</option>
                {activeShops.map((s) => (
                  <option key={s.id} value={s.id}>{shopLabel(s)} — {s.owner_name}</option>
                ))}
              </select>
            </div>
          )}

          {selectedShop && (
            <div className="rounded-lg border border-violet-100 bg-violet-50/50 px-3 py-2 text-xs space-y-0.5">
              <div className="flex justify-between"><span className="text-gray-500">Owner</span><span className="font-semibold">{selectedShop.owner_name}{selectedShop.owner_phone ? ` · ${selectedShop.owner_phone}` : ''}</span></div>
              <div className="flex justify-between"><span className="text-gray-500">Monthly rent</span><span className="font-semibold">₹{fmtMoney(selectedShop.monthly_rent)}</span></div>
              {selectedPending && (
                <div className="flex justify-between">
                  <span className="text-gray-500">Pending</span>
                  <span className={`font-bold ${Number(selectedPending.pending) > 0 ? 'text-rose-700' : 'text-emerald-700'}`}>
                    {Number(selectedPending.pending) > 0 ? `₹${fmtMoney(selectedPending.pending)} · ${selectedPending.unpaid_months.length} month(s)` : 'All clear'}
                  </span>
                </div>
              )}
            </div>
          )}

          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className={labelCls}>Rent for month *</label>
              <input type="month" value={form.rent_month} onChange={(e) => changeMonth(e.target.value)} className={inputCls} />
            </div>
            <div>
              <label className={labelCls}>Amount (₹) *</label>
              <input type="number" min="0" step="0.01" value={form.amount} onChange={(e) => setForm((f) => ({ ...f, amount: e.target.value }))} className={`${inputCls} font-bold`} />
            </div>
          </div>
          {selectedPending?.unpaid_months?.length > 1 && (
            <div className="flex flex-wrap gap-1">
              {selectedPending.unpaid_months.map((m) => (
                <button key={m} type="button" onClick={() => changeMonth(m.slice(0, 7))}
                  className={`text-[10px] font-bold px-1.5 py-0.5 rounded border ${form.rent_month === m.slice(0, 7) ? 'bg-violet-600 text-white border-violet-600' : 'bg-white text-rose-700 border-rose-200'}`}>
                  {monthLabel(m)}
                </button>
              ))}
            </div>
          )}
          <div>
            <label className={labelCls}>Payment mode</label>
            <div className="flex flex-wrap gap-1">
              {RENT_PAYMENT_MODES.map((m) => (
                <button key={m.id} type="button" onClick={() => setForm((f) => ({ ...f, payment_mode: m.id }))}
                  className={`px-2.5 py-1 rounded-md text-xs font-semibold border ${form.payment_mode === m.id ? 'bg-gray-900 text-white border-gray-900' : 'bg-white text-gray-600 border-gray-200'}`}>
                  {m.label}
                </button>
              ))}
            </div>
          </div>
          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className={labelCls}>Paid by</label>
              <input value={form.paid_by} onChange={(e) => setForm((f) => ({ ...f, paid_by: e.target.value }))} className={inputCls} />
            </div>
            <div>
              <label className={labelCls}>Txn / cheque no.</label>
              <input value={form.reference_no} onChange={(e) => setForm((f) => ({ ...f, reference_no: e.target.value }))} className={inputCls} />
            </div>
            <div className="col-span-2">
              <label className={labelCls}>Remarks</label>
              <input value={form.remarks} onChange={(e) => setForm((f) => ({ ...f, remarks: e.target.value }))} className={inputCls} />
            </div>
            <div className="col-span-2">
              <label className={labelCls}>Received at</label>
              <input type="datetime-local" value={form.collected_at} onChange={(e) => setForm((f) => ({ ...f, collected_at: e.target.value }))} className={inputCls} />
            </div>
          </div>
          <div className="flex gap-2 pt-1">
            <button type="button" disabled={saving} onClick={() => submit(true)}
              className="flex-1 flex items-center justify-center gap-1.5 bg-violet-600 text-white py-2 rounded-lg text-sm font-bold hover:bg-violet-700 disabled:opacity-50">
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
                { id: 'pending', label: `Pending rent (${pending?.totals?.shops_with_pending || 0})` },
                { id: 'receipts', label: `Receipts (${receipts.length})` },
                { id: 'shops', label: `Shops (${shops.length})` },
              ].map((t) => (
                <button key={t.id} type="button" onClick={() => setTab(t.id)}
                  className={`px-3 py-2.5 text-xs font-semibold ${tab === t.id ? 'text-violet-700 border-b-2 border-violet-600' : 'text-gray-500 hover:text-gray-700'}`}>
                  {t.label}
                </button>
              ))}
            </div>
            <div className="flex items-center gap-1.5 py-1.5">
              {tab !== 'shops' && (
                <div className="relative">
                  <Search size={12} className="absolute left-2 top-1/2 -translate-y-1/2 text-gray-400" />
                  <input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Shop, owner, receipt…" className="border border-gray-200 rounded-md pl-6 pr-2 py-1 text-xs w-44" />
                </div>
              )}
              {tab === 'pending' && (
                <>
                  <label className="flex items-center gap-1 text-[11px] text-gray-600">
                    <input type="checkbox" checked={pendingOnly} onChange={(e) => setPendingOnly(e.target.checked)} /> Only with dues
                  </label>
                  <button type="button" onClick={exportPendingCsv} className="flex items-center gap-1 px-2 py-1 rounded-md border border-gray-200 text-xs font-semibold text-gray-700 hover:bg-gray-50">
                    <Download size={12} /> CSV
                  </button>
                </>
              )}
              {tab === 'receipts' && (
                <>
                  <select value={shopFilter} onChange={(e) => setShopFilter(e.target.value)} className="border border-gray-200 rounded-md px-2 py-1 text-xs max-w-[160px]">
                    <option value="">All shops</option>
                    {shops.map((s) => <option key={s.id} value={s.id}>{shopLabel(s)}</option>)}
                  </select>
                  <button type="button" onClick={exportReceiptsCsv} className="flex items-center gap-1 px-2 py-1 rounded-md border border-gray-200 text-xs font-semibold text-gray-700 hover:bg-gray-50">
                    <Download size={12} /> CSV
                  </button>
                </>
              )}
              {tab === 'shops' && (
                <button type="button" onClick={() => setShopModal({})} className="flex items-center gap-1 px-2.5 py-1 rounded-md bg-violet-600 text-white text-xs font-bold hover:bg-violet-700">
                  <Plus size={12} /> Add shop
                </button>
              )}
            </div>
          </div>

          <div className="overflow-x-auto max-h-[min(68vh,700px)] overflow-y-auto">
            {tab === 'pending' && (
              <table className="w-full text-sm">
                <thead className="bg-gray-50 sticky top-0 text-[10px] uppercase text-gray-500">
                  <tr>
                    <th className="px-3 py-2 text-left">Shop</th>
                    <th className="px-3 py-2 text-left">Owner</th>
                    <th className="px-3 py-2 text-right">Rent / mo</th>
                    <th className="px-3 py-2 text-left">Unpaid months</th>
                    <th className="px-3 py-2 text-right">Pending</th>
                    <th className="px-3 py-2 text-left">Last paid</th>
                    <th className="px-3 py-2" />
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-50">
                  {pendingRows.length === 0 ? (
                    <tr><td colSpan={7} className="px-3 py-8 text-center text-gray-400">{pendingOnly ? 'No pending rent. All shops are clear.' : 'No shops found'}</td></tr>
                  ) : pendingRows.map((r) => (
                    <tr key={r.id} className="hover:bg-violet-50/40 align-top">
                      <td className="px-3 py-2">
                        <p className="font-semibold text-gray-900">{r.shop_name}</p>
                        {r.shop_number && <p className="text-[10px] text-gray-500">{r.shop_number}</p>}
                      </td>
                      <td className="px-3 py-2 text-xs">
                        {r.owner_name}
                        {r.owner_phone && <p className="text-[10px] text-gray-500">{r.owner_phone}</p>}
                      </td>
                      <td className="px-3 py-2 text-right tabular-nums text-xs">₹{fmtMoney(r.monthly_rent)}</td>
                      <td className="px-3 py-2">
                        <div className="flex flex-wrap gap-1 max-w-[260px]">
                          {(r.unpaid_months || []).length === 0
                            ? <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-emerald-100 text-emerald-700">Clear</span>
                            : r.unpaid_months.map((m) => (
                              <span key={m} className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-rose-100 text-rose-700">{monthLabel(m)}</span>
                            ))}
                        </div>
                        {r.overdue_months > 0 && <p className="text-[10px] text-rose-600 font-semibold mt-0.5">{r.overdue_months} month(s) overdue</p>}
                      </td>
                      <td className="px-3 py-2 text-right font-bold tabular-nums text-rose-700">{Number(r.pending) > 0 ? `₹${fmtMoney(r.pending)}` : '—'}</td>
                      <td className="px-3 py-2 text-xs text-gray-500 whitespace-nowrap">{r.last_paid_at ? formatDateTime(r.last_paid_at) : 'Never'}</td>
                      <td className="px-3 py-2 text-right whitespace-nowrap">
                        {Number(r.pending) > 0 && (
                          <button type="button" onClick={() => selectShop(r.id)} className="text-[11px] font-bold text-violet-700 hover:underline mr-1.5">Collect</button>
                        )}
                        <button type="button" onClick={() => setLedgerShopId(r.id)} className="p-1 text-gray-500 hover:text-gray-900" title="Month-wise ledger"><History size={14} /></button>
                        {r.owner_phone && (
                          <>
                            <a href={`tel:${r.owner_phone}`} className="inline-block p-1 text-emerald-700" title="Call owner"><Phone size={14} /></a>
                            {Number(r.pending) > 0 && (
                              <button type="button" onClick={() => sendReminder(r)} className="p-1 text-green-600 hover:text-green-800" title="Send WhatsApp reminder"><MessageCircle size={14} /></button>
                            )}
                          </>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
                {pendingRows.length > 0 && (
                  <tfoot className="bg-gray-50 border-t border-gray-200 font-bold">
                    <tr>
                      <td className="px-3 py-2" colSpan={4}>Total pending</td>
                      <td className="px-3 py-2 text-right text-rose-700 tabular-nums">₹{fmtMoney(pendingRows.reduce((s, r) => s + Number(r.pending || 0), 0))}</td>
                      <td colSpan={2} />
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
                    <th className="px-3 py-2 text-left">Shop</th>
                    <th className="px-3 py-2 text-left">Owner</th>
                    <th className="px-3 py-2 text-left">For month</th>
                    <th className="px-3 py-2 text-left">Mode</th>
                    <th className="px-3 py-2 text-right">Amount</th>
                    <th className="px-3 py-2 text-left">By</th>
                    <th className="px-3 py-2" />
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-50">
                  {receipts.length === 0 ? (
                    <tr><td colSpan={9} className="px-3 py-8 text-center text-gray-400">{loading ? 'Loading…' : 'No rent collected in this period'}</td></tr>
                  ) : receipts.map((r) => (
                    <tr key={r.id} className="hover:bg-violet-50/40">
                      <td className="px-3 py-2 font-mono text-xs font-semibold">{r.receipt_no}</td>
                      <td className="px-3 py-2 text-xs whitespace-nowrap tabular-nums">{formatDateTime(r.collected_at)}</td>
                      <td className="px-3 py-2 text-xs font-semibold">{shopLabel(r)}</td>
                      <td className="px-3 py-2 text-xs">{r.owner_name}</td>
                      <td className="px-3 py-2 text-xs">{monthLabel(r.rent_month)}</td>
                      <td className="px-3 py-2 text-xs uppercase">{r.payment_mode}{r.reference_no ? <span className="normal-case text-gray-400"> · {r.reference_no}</span> : null}</td>
                      <td className="px-3 py-2 text-right font-bold text-violet-700 tabular-nums">₹{fmtMoney(r.amount)}</td>
                      <td className="px-3 py-2 text-xs">{r.collected_by_name}</td>
                      <td className="px-3 py-2 text-right whitespace-nowrap">
                        <button type="button" onClick={() => printRentReceipt(r)} className="p-1 text-gray-500 hover:text-gray-900" title="Print receipt"><Printer size={14} /></button>
                        <button type="button" onClick={() => setVoidTarget(r)} className="p-1 text-gray-400 hover:text-rose-600" title="Cancel receipt"><XCircle size={14} /></button>
                      </td>
                    </tr>
                  ))}
                </tbody>
                {receipts.length > 0 && (
                  <tfoot className="bg-gray-50 border-t border-gray-200 font-bold">
                    <tr>
                      <td className="px-3 py-2" colSpan={6}>Total</td>
                      <td className="px-3 py-2 text-right text-violet-700 tabular-nums">₹{fmtMoney(receiptsTotal)}</td>
                      <td colSpan={2} />
                    </tr>
                  </tfoot>
                )}
              </table>
            )}

            {tab === 'shops' && (
              <table className="w-full text-sm">
                <thead className="bg-gray-50 sticky top-0 text-[10px] uppercase text-gray-500">
                  <tr>
                    <th className="px-3 py-2 text-left">Shop</th>
                    <th className="px-3 py-2 text-left">Owner</th>
                    <th className="px-3 py-2 text-right">Rent / mo</th>
                    <th className="px-3 py-2 text-center">Due day</th>
                    <th className="px-3 py-2 text-left">Since</th>
                    <th className="px-3 py-2 text-right">Deposit</th>
                    <th className="px-3 py-2 text-left">Status</th>
                    <th className="px-3 py-2" />
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-50">
                  {shops.length === 0 ? (
                    <tr><td colSpan={8} className="px-3 py-8 text-center text-gray-400">No shops added</td></tr>
                  ) : shops.map((s) => (
                    <tr key={s.id} className="hover:bg-gray-50">
                      <td className="px-3 py-2 font-semibold">{shopLabel(s)}</td>
                      <td className="px-3 py-2 text-xs">{s.owner_name}{s.owner_phone ? ` · ${s.owner_phone}` : ''}</td>
                      <td className="px-3 py-2 text-right tabular-nums">₹{fmtMoney(s.monthly_rent)}</td>
                      <td className="px-3 py-2 text-center text-xs">{s.due_day}</td>
                      <td className="px-3 py-2 text-xs">{s.rent_start_date ? format(new Date(`${s.rent_start_date}T12:00:00`), 'MMM yyyy') : '—'}</td>
                      <td className="px-3 py-2 text-right text-xs tabular-nums">{Number(s.security_deposit) > 0 ? `₹${fmtMoney(s.security_deposit)}` : '—'}</td>
                      <td className="px-3 py-2">
                        <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${s.is_active ? 'bg-emerald-100 text-emerald-700' : 'bg-gray-100 text-gray-500'}`}>
                          {s.is_active ? 'Active' : 'Vacated'}
                        </span>
                      </td>
                      <td className="px-3 py-2 text-right whitespace-nowrap">
                        <button type="button" onClick={() => setLedgerShopId(s.id)} className="p-1 text-gray-500 hover:text-gray-900" title="Ledger"><History size={14} /></button>
                        <button type="button" onClick={() => setShopModal(s)} className="p-1 text-gray-500 hover:text-gray-900" title="Edit"><Pencil size={14} /></button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>
      </div>

      {shopModal && (
        <ShopModal
          shop={shopModal}
          onClose={() => setShopModal(null)}
          onSaved={() => { setShopModal(null); loadShops(); loadPending() }}
        />
      )}
      {ledgerShopId && (
        <LedgerModal
          shopId={ledgerShopId}
          onClose={() => setLedgerShopId(null)}
          onCollect={(shopId, month, balance) => { setLedgerShopId(null); selectShop(shopId, month, String(Number(balance))) }}
        />
      )}
      {voidTarget && (
        <VoidReceiptModal
          title="Cancel rent receipt"
          receiptNo={voidTarget.receipt_no}
          onClose={() => setVoidTarget(null)}
          onConfirm={confirmVoid}
        />
      )}
    </div>
  )
}
