/**
 * Decorative OPD sheet frame (VARDAAN-style) shown when no scanned background is set.
 * Hidden when .opd-sheet--with-bg is on the parent canvas (background image in use).
 */
export function OpdSheetChrome() {
  return (
    <div className="opd-sheet-chrome" aria-hidden="true">
      <header className="opd-header">
        <div className="opd-header-brand">
          <span className="opd-logo-wrap">
            <svg className="opd-logo-icon" viewBox="0 0 32 32" aria-hidden>
              <rect fill="#ffffff" rx="4" width="32" height="32" />
              <path
                fill="#dc2626"
                d="M14 8h4v8h8v4h-8v8h-4v-8H6v-4h8z"
              />
            </svg>
          </span>
          <div className="opd-header-text">
            <div className="opd-hospital-name">VARDAAN HOSPITAL</div>
            <div className="opd-hospital-meta">
              Near oxford School, Rohtak By Pass Road, JIND M. +91 99924-25764, +91 70828-77717
            </div>
          </div>
        </div>
      </header>

      <section className="opd-patient-section">
        <div className="opd-patient-col">
          <div className="opd-field-line">
            <span className="opd-lbl">OPD No</span>
            <span className="opd-dots" />
          </div>
          <div className="opd-field-line">
            <span className="opd-lbl">Patient Name</span>
            <span className="opd-dots" />
          </div>
          <div className="opd-field-line">
            <span className="opd-lbl">Age / Sex</span>
            <span className="opd-dots" />
          </div>
          <div className="opd-field-line">
            <span className="opd-lbl">Guardian Name</span>
            <span className="opd-dots" />
          </div>
          <div className="opd-field-line">
            <span className="opd-lbl">Address</span>
            <span className="opd-dots" />
          </div>
        </div>
        <div className="opd-patient-col">
          <div className="opd-field-line">
            <span className="opd-lbl">Date</span>
            <span className="opd-dots" />
          </div>
          <div className="opd-field-line">
            <span className="opd-lbl">Doctor</span>
            <span className="opd-dots" />
          </div>
          <div className="opd-field-line">
            <span className="opd-lbl">Reg. No.</span>
            <span className="opd-dots" />
          </div>
          <div className="opd-field-line">
            <span className="opd-lbl">Amount</span>
            <span className="opd-dots" />
          </div>
          <div className="opd-field-line">
            <span className="opd-lbl">Mobile</span>
            <span className="opd-dots" />
          </div>
        </div>
      </section>

      <div className="opd-mid-panel">
        <div className="opd-mid-grid">
          <div className="opd-mid-cell opd-mid-vitals">
            <span className="opd-mid-title">Vital assessment</span>
            <ul className="opd-mid-list">
              <li>BP</li>
              <li>PR</li>
              <li>Temp</li>
              <li>RR</li>
              <li>SPO2</li>
              <li>Wt. / Ht. / BMI</li>
            </ul>
          </div>
          <div className="opd-mid-cell opd-mid-center">
            <span className="opd-mid-title">CO-Morbidities &amp; screening</span>
            <p className="opd-mid-placeholder">DM · HTN · CAD · COPD · CVA · THYROID · Nutritional screening</p>
            <div className="opd-pain-scale">
              <span>Pain 0 — 10</span>
              <div className="opd-pain-bar" />
            </div>
          </div>
          <div className="opd-mid-cell opd-mid-side">
            <span className="opd-mid-title">Allergy &amp; addiction</span>
            <p className="opd-mid-placeholder">Drug · Food · Others · Smoking · Alcohol</p>
          </div>
        </div>
        <div className="opd-mid-bottom">
          <div className="opd-mid-wide">Chief complaints</div>
          <div className="opd-mid-wide">Preventive / special advice</div>
        </div>
      </div>

      <div className="opd-watermark">VARDAAN HOSPITAL</div>

      <footer className="opd-sheet-footer">
        <p className="opd-disclaimer">
          Prescribed Medicines are only suggestions, patient is free to choose any reliable
          generic/brand of their choice with exactly the same content.
        </p>
        <div className="opd-bar-grey">
          <span className="opd-bar-hindi">कृपया अगली बार पुरानी पर्ची व रिपोर्टस साथ लाएं</span>
          <span className="opd-bar-mlc">❖ Not Valid For MLC</span>
        </div>
        <div className="opd-bar-teal" />
      </footer>
    </div>
  )
}
