import React from 'react'
import { fmtMoney, formatVehicleNo, shopLabel } from './collectionSectionUtils'

function esc(s) {
  return String(s ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
}

function money(n) {
  const v = Number(n) || 0
  return `${v < 0 ? '−' : ''}₹${fmtMoney(Math.abs(v))}`
}

/**
 * Flatten the /reports/ca-summary/ payload into display rows.
 * `amount` is part of gross received; `memo` is shown for the CA but never added again.
 */
export function buildCaRows(ca) {
  if (!ca) return []
  const heads = Object.fromEntries((ca.heads || []).map((h) => [h.key, h]))
  const ipd = ca.ipd || {}
  const rows = []
  let no = 0
  const head = (key, label, extra = {}) => {
    const h = heads[key] || { count: 0, amount: '0.00' }
    no += 1
    rows.push({ kind: 'head', no, label, count: h.count, amount: Number(h.amount), ...extra })
  }
  const sub = (label, amount, extra = {}) => rows.push({ kind: 'sub', label, amount, ...extra })

  head('iol', 'IOL')
  head('caesarean', 'Caesarean')
  head('delivery', 'Delivery')
  head('room_charges', 'Room charges', {
    memo: Number(ipd.room_adjusted) ? `${money(ipd.room_adjusted)} adjusted from IPD advance (${ipd.room_adjusted_count || 0} discharge(s))` : '',
  })
  head('ipd_advance', 'IPD advance received')
  sub('Less: room charges adjusted from advance', null, { memo: money(-Number(ipd.room_adjusted || 0)) })
  sub('Net IPD (advance after room charges)', null, { memo: money(ipd.net_ipd), strongMemo: true })
  const amb = heads.ambulance || {}
  head('ambulance', 'Ambulance', { countNote: amb.trips ? `${amb.trips} trip(s)` : '' })
  for (const v of ca.ambulance_by_vehicle || []) {
    sub(`${formatVehicleNo(v.vehicle_number)}${v.label ? ` · ${v.label}` : ''}`, null, {
      count: v.count,
      countNote: `${v.trips} trip(s)`,
      memo: money(v.amount),
    })
  }
  head('rent', 'Shop rent', {
    memo: Number(ca.pending_rent?.amount) ? `Pending ${money(ca.pending_rent.amount)} (${ca.pending_rent.shops} shop(s))` : '',
  })
  for (const s of ca.rent_by_shop || []) {
    sub(`${shopLabel(s)}${s.owner_name ? ` · ${s.owner_name}` : ''}`, null, { count: s.count, memo: money(s.amount) })
  }
  head('opd', 'OPD fees')
  head('lab', 'Lab')
  head('other_services', 'Other services')
  for (const c of ca.other_services_by_category || []) {
    sub(c.category, null, { count: c.count, memo: money(c.amount) })
  }
  head('refunds', 'Refunds')
  return rows
}

export function caSummaryCsvRows(ca) {
  const rows = buildCaRows(ca).map((r) => [
    r.kind === 'head' ? r.no : '',
    r.kind === 'head' ? r.label : `   ${r.label}`,
    r.count ?? '',
    r.amount != null ? r.amount.toFixed(2) : '',
    r.memo || '',
  ])
  if (!ca) return rows
  const m = ca.modes || {}
  rows.push(
    [],
    ['', 'Gross received', '', ca.gross_received, ''],
    ['', 'Less: expenses from collection', ca.expenses_count, `-${ca.expenses_total}`, ''],
    ['', 'Net after expenses', '', ca.net_after_expenses, ''],
    ['', 'Cash', '', m.cash, ''],
    ['', 'UPI', '', m.upi, ''],
    ['', 'Card', '', m.card, ''],
    ['', 'Other', '', m.other, ''],
  )
  return rows
}

export function renderCaSummaryHtml(ca) {
  if (!ca) return ''
  const rows = buildCaRows(ca)
  const m = ca.modes || {}
  const recon = ca.reconciliation || {}
  const body = rows.map((r) => {
    const count = `${r.count ?? ''}${r.countNote ? `<br/><span style="font-size:8px">${esc(r.countNote)}</span>` : ''}`
    if (r.kind === 'head') {
      return `<tr>
        <td class="c">${r.no}</td>
        <td><strong>${esc(r.label)}</strong></td>
        <td class="c">${count}</td>
        <td class="r"><strong>${money(r.amount)}</strong></td>
        <td style="font-size:8.5px">${esc(r.memo || '')}</td>
      </tr>`
    }
    return `<tr>
      <td></td>
      <td style="padding-left:14px;font-size:8.5px">${esc(r.label)}</td>
      <td class="c" style="font-size:8.5px">${count}</td>
      <td></td>
      <td class="r" style="font-size:8.5px${r.strongMemo ? ';font-weight:bold' : ''}">${esc(r.memo || '')}</td>
    </tr>`
  }).join('')

  return `
    <h2 class="sec">Collection Summary (for CA)</h2>
    <table class="tbl">
      <thead>
        <tr>
          <th class="c" style="width:5%">#</th><th>Head</th><th class="c" style="width:10%">Count</th>
          <th class="r" style="width:16%">Amount received</th><th style="width:30%">Memo (not added to total)</th>
        </tr>
      </thead>
      <tbody>${body}</tbody>
      <tfoot>
        <tr><td></td><td>Gross received</td><td></td><td class="r">${money(ca.gross_received)}</td><td></td></tr>
        <tr><td></td><td>Less: expenses paid from collection</td><td class="c">${ca.expenses_count || 0}</td><td class="r">${money(-Number(ca.expenses_total || 0))}</td><td></td></tr>
        <tr><td></td><td>Net after expenses</td><td></td><td class="r">${money(ca.net_after_expenses)}</td><td></td></tr>
        <tr><td></td><td colspan="4" style="font-weight:normal">By mode: Cash ${money(m.cash)} · UPI ${money(m.upi)} · Card ${money(m.card)} · Other ${money(m.other)}</td></tr>
        ${recon.reconciled === false ? `<tr><td></td><td colspan="4" style="color:#b91c1c">Check: heads differ from recorded receipts (${money(recon.source_total)}) by ${money(recon.difference)}</td></tr>` : ''}
      </tfoot>
    </table>`
}

export function CaSummaryPanel({ ca }) {
  if (!ca) {
    return <div className="px-3 py-6 text-center text-gray-400 text-sm">CA summary is not available for this filter.</div>
  }
  const rows = buildCaRows(ca)
  const m = ca.modes || {}
  const recon = ca.reconciliation || {}
  return (
    <div>
      <table className="w-full text-sm">
        <thead className="bg-gray-50 sticky top-0 text-[10px] uppercase text-gray-500">
          <tr>
            <th className="px-3 py-2 text-left w-10">#</th>
            <th className="px-3 py-2 text-left">Head</th>
            <th className="px-3 py-2 text-center">Count</th>
            <th className="px-3 py-2 text-right">Amount received</th>
            <th className="px-3 py-2 text-left">Memo (not added)</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-50">
          {rows.map((r, i) => (r.kind === 'head' ? (
            <tr key={i} className="hover:bg-indigo-50/40">
              <td className="px-3 py-2 text-gray-500">{r.no}</td>
              <td className="px-3 py-2 font-semibold text-gray-800">{r.label}</td>
              <td className="px-3 py-2 text-center tabular-nums">
                {r.count}
                {r.countNote ? <span className="block text-[10px] text-gray-500">{r.countNote}</span> : null}
              </td>
              <td className={`px-3 py-2 text-right font-bold tabular-nums ${r.amount < 0 ? 'text-rose-700' : 'text-gray-900'}`}>{money(r.amount)}</td>
              <td className="px-3 py-2 text-xs text-gray-600">{r.memo}</td>
            </tr>
          ) : (
            <tr key={i} className="bg-gray-50/40">
              <td />
              <td className="px-3 py-1.5 pl-7 text-xs text-gray-600">{r.label}</td>
              <td className="px-3 py-1.5 text-center text-xs tabular-nums text-gray-600">
                {r.count ?? ''}
                {r.countNote ? <span className="block text-[10px] text-gray-400">{r.countNote}</span> : null}
              </td>
              <td />
              <td className={`px-3 py-1.5 text-xs tabular-nums ${r.strongMemo ? 'font-bold text-indigo-700' : 'text-gray-600'}`}>{r.memo}</td>
            </tr>
          )))}
        </tbody>
        <tfoot className="text-sm">
          <tr className="border-t-2 border-gray-200 bg-emerald-50/50">
            <td />
            <td className="px-3 py-2 font-bold">Gross received</td>
            <td />
            <td className="px-3 py-2 text-right font-bold tabular-nums">{money(ca.gross_received)}</td>
            <td className="px-3 py-2 text-[11px] text-gray-500">
              Cash {money(m.cash)} · UPI {money(m.upi)} · Card {money(m.card)} · Other {money(m.other)}
            </td>
          </tr>
          <tr className="bg-rose-50/40">
            <td />
            <td className="px-3 py-2">Less: expenses from collection</td>
            <td className="px-3 py-2 text-center tabular-nums">{ca.expenses_count || 0}</td>
            <td className="px-3 py-2 text-right tabular-nums text-rose-700">{money(-Number(ca.expenses_total || 0))}</td>
            <td />
          </tr>
          <tr className="bg-indigo-50/60">
            <td />
            <td className="px-3 py-2 font-bold">Net after expenses</td>
            <td />
            <td className="px-3 py-2 text-right font-bold tabular-nums text-indigo-800">{money(ca.net_after_expenses)}</td>
            <td className="px-3 py-2 text-[11px]">
              {recon.reconciled === false
                ? <span className="font-semibold text-rose-700">Heads differ from receipts by {money(recon.difference)}</span>
                : <span className="text-emerald-700">Heads match recorded receipts</span>}
            </td>
          </tr>
        </tfoot>
      </table>
    </div>
  )
}
