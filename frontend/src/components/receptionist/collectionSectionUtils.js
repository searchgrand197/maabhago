import { format, startOfMonth, startOfWeek, subDays } from 'date-fns'

export const PAYMENT_MODES = [
  { id: 'cash', label: 'Cash' },
  { id: 'upi', label: 'UPI' },
  { id: 'card', label: 'Card' },
  { id: 'bank_transfer', label: 'Bank' },
  { id: 'other', label: 'Other' },
]

export function unwrapData(res) {
  const body = res?.data
  return body?.data ?? body
}

export function unwrapRows(res) {
  const body = unwrapData(res)
  if (Array.isArray(body?.results)) return body.results
  if (Array.isArray(body)) return body
  return []
}

export function fmtMoney(n) {
  const v = Number(n)
  if (!Number.isFinite(v)) return '0.00'
  return v.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

export function todayStr() {
  return format(new Date(), 'yyyy-MM-dd')
}

export function toDateTimeInputValue(v) {
  const d = new Date(v)
  if (Number.isNaN(d.getTime())) return ''
  return format(d, "yyyy-MM-dd'T'HH:mm")
}

export function quickRange(kind) {
  const now = new Date()
  const iso = (d) => format(d, 'yyyy-MM-dd')
  if (kind === 'yesterday') {
    const y = subDays(now, 1)
    return [iso(y), iso(y)]
  }
  if (kind === 'week') return [iso(startOfWeek(now, { weekStartsOn: 1 })), iso(now)]
  if (kind === 'month') return [iso(startOfMonth(now)), iso(now)]
  return [iso(now), iso(now)]
}

export function downloadCsv(filename, header, rows) {
  const csv = [header, ...rows]
    .map((r) => r.map((c) => `"${String(c ?? '').replace(/"/g, '""')}"`).join(','))
    .join('\n')
  const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8' }))
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}

export function formatVehicleNo(value) {
  const v = String(value || '').toUpperCase()
  const m = v.match(/^([A-Z]{2})(\d{1,2})([A-Z]{0,3})(\d{1,4})$/)
  return m ? [m[1], m[2], m[3], m[4]].filter(Boolean).join(' ') : v
}

/** ``2026-09`` or ``2026-09-01`` -> ``Sep 2026`` */
export function monthLabel(value) {
  if (!value) return '—'
  const [y, m] = String(value).split('-')
  return format(new Date(Number(y), Number(m) - 1, 1), 'MMM yyyy')
}

export function shopLabel(s) {
  if (!s) return ''
  return `${s.shop_name}${s.shop_number ? ` (${s.shop_number})` : ''}`
}

export function digitsOnlyPhone(phone) {
  const digits = String(phone || '').replace(/\D/g, '')
  if (digits.length === 10) return `91${digits}`
  return digits
}
