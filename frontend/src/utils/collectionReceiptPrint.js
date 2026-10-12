import { createSameTabPrintWindow } from './printHtmlInHiddenFrame'
import { formatDateTime } from './dateTimeFormat'
import {
  PAYMENT_SLIP_PRINT_CLOSE_SCRIPT,
  buildPaymentSlipContainerCss,
  buildPaymentSlipHeaderCss,
  buildPaymentSlipProfileLines,
  buildPaymentSlipTopHeaderHtml,
  resolvePaymentSlipLogoUrl,
} from './paymentSlipPrint'
import { getPaymentSlipProfile, loadReceptionPortalProfileCache } from './receptionPortalProfile'

const ONES = ['', 'One', 'Two', 'Three', 'Four', 'Five', 'Six', 'Seven', 'Eight', 'Nine', 'Ten', 'Eleven',
  'Twelve', 'Thirteen', 'Fourteen', 'Fifteen', 'Sixteen', 'Seventeen', 'Eighteen', 'Nineteen']
const TENS = ['', '', 'Twenty', 'Thirty', 'Forty', 'Fifty', 'Sixty', 'Seventy', 'Eighty', 'Ninety']

function twoDigits(n) {
  if (n < 20) return ONES[n]
  return `${TENS[Math.floor(n / 10)]}${n % 10 ? ` ${ONES[n % 10]}` : ''}`
}

function threeDigits(n) {
  const h = Math.floor(n / 100)
  const rest = n % 100
  return [h ? `${ONES[h]} Hundred` : '', rest ? twoDigits(rest) : ''].filter(Boolean).join(' ')
}

/** Indian numbering (lakh / crore), e.g. 125000.5 -> "One Lakh Twenty Five Thousand Rupees and Fifty Paise Only". */
export function amountInWords(value) {
  const num = Math.abs(Number(value) || 0)
  let rupees = Math.floor(num)
  const paise = Math.round((num - rupees) * 100)
  if (rupees === 0 && paise === 0) return 'Zero Rupees Only'

  const parts = []
  const crore = Math.floor(rupees / 10000000)
  rupees %= 10000000
  const lakh = Math.floor(rupees / 100000)
  rupees %= 100000
  const thousand = Math.floor(rupees / 1000)
  rupees %= 1000
  if (crore) parts.push(`${threeDigits(crore)} Crore`)
  if (lakh) parts.push(`${twoDigits(lakh)} Lakh`)
  if (thousand) parts.push(`${twoDigits(thousand)} Thousand`)
  if (rupees) parts.push(threeDigits(rupees))

  const rupeeText = parts.length ? `${parts.join(' ')} Rupees` : ''
  const paiseText = paise ? `${twoDigits(paise)} Paise` : ''
  return `${[rupeeText, paiseText].filter(Boolean).join(' and ')} Only`
}

export function payModeLabel(mode) {
  const m = String(mode || 'cash').toLowerCase()
  return {
    cash: 'Cash', upi: 'UPI', card: 'Card', bank_transfer: 'Bank Transfer', cheque: 'Cheque', other: 'Other',
  }[m] || 'Other'
}

function escapeHtml(s) {
  return String(s ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
}

function buildStyles(accent) {
  return `
    @page { size: A4 portrait; margin: 0; }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { font-family: Arial, sans-serif; font-size: 11px; color: #111; width: 210mm; background: #fff; }
    ${buildPaymentSlipContainerCss()}
    ${buildPaymentSlipHeaderCss({ accentColor: accent })}
    .receipt-title {
      text-align: center; font-size: 13px; font-weight: 700; text-transform: uppercase;
      letter-spacing: 2px; border-bottom: 1px solid #111; padding-bottom: 2mm; margin-bottom: 3mm; color: ${accent};
    }
    .info-grid { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 2.5mm 4mm; margin-bottom: 4mm; font-size: 10.5px; }
    .info-cell { display: flex; flex-direction: column; gap: 1px; }
    .info-label { color: #666; font-size: 9px; text-transform: uppercase; letter-spacing: .3px; }
    .info-val { font-weight: 700; color: #111; }
    .amount-box {
      border: 1.5px solid ${accent}; border-radius: 4px; padding: 3mm 4mm; display: flex;
      justify-content: space-between; align-items: center; gap: 4mm;
    }
    .amount-words { font-size: 10.5px; font-style: italic; color: #333; }
    .amount-fig { font-size: 20px; font-weight: 900; color: ${accent}; white-space: nowrap; }
    .footer {
      margin-top: auto; padding-top: 2mm; display: flex; justify-content: space-between;
      align-items: flex-end; font-size: 9px; color: #555;
    }
    .sign { text-align: center; min-width: 45mm; border-top: 1px solid #555; padding-top: 1mm; }
    .stamp {
      border: 2px solid ${accent}; color: ${accent}; font-weight: 900; font-size: 13px;
      padding: 2px 10px; border-radius: 4px; letter-spacing: 2px;
    }
  `
}

/**
 * Prints a half-A4 receipt with the hospital header.
 * ``fields`` is a list of ``{ label, value, span }`` shown in a 3-column grid.
 */
export async function printCollectionReceipt({ title, accent = '#0f766e', stamp = 'RECEIVED', fields = [], amount, note = '' }) {
  await loadReceptionPortalProfileCache()
  const profile = getPaymentSlipProfile()
  const fieldsHtml = fields
    .filter((f) => f && f.value != null && String(f.value).trim() !== '')
    .map((f) => `
      <div class="info-cell"${f.span ? ` style="grid-column: span ${f.span}"` : ''}>
        <span class="info-label">${escapeHtml(f.label)}</span>
        <span class="info-val">${escapeHtml(f.value)}</span>
      </div>`)
    .join('')
  const amt = Number(amount) || 0

  const html = `<!DOCTYPE html><html><head><meta charset="utf-8"/>
    <title>${escapeHtml(title)}</title>
    <style>${buildStyles(accent)}</style></head><body>
    <div class="slip">
      ${buildPaymentSlipTopHeaderHtml({
        hospitalName: profile.hospital_name || 'Hospital',
        logoUrl: resolvePaymentSlipLogoUrl(profile),
        tagline: 'Healthcare &amp; Diagnostics',
        profileLines: buildPaymentSlipProfileLines(profile, escapeHtml),
        escapeHtml,
      })}
      <div class="receipt-title">${escapeHtml(title)}</div>
      <div class="info-grid">${fieldsHtml}</div>
      <div class="amount-box">
        <div class="amount-words">${escapeHtml(amountInWords(amt))}</div>
        <div class="amount-fig">₹${amt.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</div>
      </div>
      <div class="footer">
        <div>${escapeHtml(note)}<br/>Printed ${escapeHtml(formatDateTime(new Date()))}</div>
        <div class="stamp">${escapeHtml(stamp)}</div>
        <div class="sign">Authorised signatory</div>
      </div>
    </div>
    ${PAYMENT_SLIP_PRINT_CLOSE_SCRIPT}
  </body></html>`

  const w = createSameTabPrintWindow()
  w.document.write(html)
  w.document.close()
}
