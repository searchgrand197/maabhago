/** Normalize category / form name for matching presets and API rows. */
export function normalizeCategoryName(s) {
  return String(s || '')
    .trim()
    .toLowerCase()
}

function cap(s) {
  const t = String(s || '').trim()
  if (!t) return ''
  return t.charAt(0).toUpperCase() + t.slice(1)
}

/** Default when no preset and no API row. */
export const DEFAULT_CATEGORY_RULE = {
  rule_type: 'unit_only',
  allow_loose_sale: true,
  base_unit_label: 'unit',
  retail_pack_label: '',
  outer_pack_label: '',
}

/**
 * Built-in presets (auto-apply when no managed row in medicine-categories).
 * `names`: medicine form / category names (case-insensitive).
 */
export const CATEGORY_RULE_PRESETS = [
  {
    names: ['tablet'],
    rule_type: 'strip_based',
    allow_loose_sale: true,
    base_unit_label: 'tablet',
    retail_pack_label: 'strip',
    outer_pack_label: '',
  },
  {
    names: ['capsule'],
    rule_type: 'strip_based',
    allow_loose_sale: true,
    base_unit_label: 'capsule',
    retail_pack_label: 'strip',
    outer_pack_label: '',
  },
  {
    names: ['lozenges', 'lozenge'],
    rule_type: 'strip_based',
    allow_loose_sale: true,
    base_unit_label: 'piece',
    retail_pack_label: 'strip',
    outer_pack_label: '',
  },
  {
    names: ['suppository'],
    rule_type: 'strip_based',
    allow_loose_sale: true,
    base_unit_label: 'piece',
    retail_pack_label: 'strip',
    outer_pack_label: '',
  },
  {
    names: ['syrup', 'suspension', 'drops', 'lotion'],
    rule_type: 'liquid',
    allow_loose_sale: false,
    base_unit_label: 'bottle',
    retail_pack_label: '',
    outer_pack_label: '',
  },
  {
    names: ['injection'],
    rule_type: 'flexible',
    allow_loose_sale: true,
    base_unit_label: 'ampule',
    retail_pack_label: 'vial',
    outer_pack_label: 'box',
  },
  {
    names: ['sachet'],
    rule_type: 'flexible',
    allow_loose_sale: true,
    base_unit_label: 'sachet',
    retail_pack_label: 'sachet',
    outer_pack_label: 'box',
  },
  {
    names: ['powder'],
    rule_type: 'flexible',
    allow_loose_sale: true,
    base_unit_label: 'sachet',
    retail_pack_label: 'sachet',
    outer_pack_label: 'box',
  },
  {
    names: ['device'],
    rule_type: 'unit_only',
    allow_loose_sale: true,
    base_unit_label: 'piece',
    retail_pack_label: '',
    outer_pack_label: '',
  },
  {
    names: ['thermometer'],
    rule_type: 'unit_only',
    allow_loose_sale: true,
    base_unit_label: 'piece',
    retail_pack_label: '',
    outer_pack_label: '',
  },
  {
    names: ['shampoo'],
    rule_type: 'unit_only',
    allow_loose_sale: false,
    base_unit_label: 'bottle',
    retail_pack_label: '',
    outer_pack_label: '',
  },
  {
    names: ['soap'],
    rule_type: 'unit_only',
    allow_loose_sale: true,
    base_unit_label: 'piece',
    retail_pack_label: '',
    outer_pack_label: '',
  },
]

export function presetRuleForForm(formName) {
  const n = normalizeCategoryName(formName)
  if (!n) return { ...DEFAULT_CATEGORY_RULE }
  for (const row of CATEGORY_RULE_PRESETS) {
    if (row.names.some((x) => normalizeCategoryName(x) === n)) {
      const { names, ...rest } = row
      return { ...DEFAULT_CATEGORY_RULE, ...rest }
    }
  }
  return { ...DEFAULT_CATEGORY_RULE }
}

/**
 * Merge API medicine-category row (if any) over built-in preset.
 * @param {string} formName - product form / category name
 * @param {Array<object>} apiRows - GET /medicine-categories/ rows
 */
export function resolveCategoryRules(formName, apiRows = []) {
  const n = normalizeCategoryName(formName)
  const preset = presetRuleForForm(formName)
  const row = (apiRows || []).find((r) => normalizeCategoryName(r?.name) === n)
  if (!row || !row.id) {
    return {
      ...preset,
      source: 'preset',
      displayName: formName || '',
    }
  }
  return {
    rule_type: row.rule_type || preset.rule_type,
    allow_loose_sale:
      typeof row.allow_loose_sale === 'boolean' ? row.allow_loose_sale : preset.allow_loose_sale,
    base_unit_label: (row.base_unit_label || '').trim() || preset.base_unit_label,
    retail_pack_label: (row.retail_pack_label || '').trim() || preset.retail_pack_label,
    outer_pack_label: (row.outer_pack_label || '').trim() || preset.outer_pack_label,
    source: 'api',
    displayName: row.name || formName,
  }
}

export function ruleTypeLabel(ruleType) {
  const m = {
    strip_based: 'Strip-based (allow loose sale)',
    liquid: 'Liquid (no loose sale)',
    flexible: 'Flexible (outer + retail + base)',
    unit_only: 'Unit only',
  }
  return m[ruleType] || ruleType
}

/** Short hint for Units / Pack row in add medicine (dynamic N from user input). */
export function conversionHintLines(rules, unitsPerPack, mrpInputType) {
  const up = Number(unitsPerPack) || 0
  const base = cap(rules.base_unit_label || 'unit')
  const retail = (rules.retail_pack_label || '').trim()
  const outer = (rules.outer_pack_label || '').trim()
  const lines = []
  if (mrpInputType === 'pack' && up > 0 && retail) {
    lines.push(`1 ${cap(retail)} = ${up} ${base}`)
  } else if (mrpInputType === 'pack' && up > 0) {
    lines.push(`1 pack = ${up} ${base}`)
  }
  if (outer && retail && base) {
    lines.push(`Chain: ${cap(outer)} → ${cap(retail)} → ${base}`)
  } else if (retail && base && retail.toLowerCase() !== base.toLowerCase()) {
    lines.push(`Sale path: ${cap(retail)} → ${base}`)
  }
  if (rules.rule_type === 'liquid' && rules.allow_loose_sale === false) {
    lines.push('Loose fractional sale off — count in bottles / packs.')
  }
  return lines
}

export function packFieldLabel(rules) {
  const r = (rules.retail_pack_label || '').trim()
  return r ? cap(r) : 'Full pack'
}

export function baseFieldLabel(rules) {
  return cap(rules.base_unit_label || 'unit')
}

/** Read-only reference for Categories screen (matches ERP defaults). */
export const CATEGORY_RULE_REFERENCE = [
  {
    title: 'STRIP_BASED (allow loose sale)',
    lines: [
      'Tablet → Strip → Tablet',
      'Capsule → Strip → Capsule',
      'Lozenges → Strip → Piece',
      'Suppository → Strip → Piece',
    ],
  },
  {
    title: 'LIQUID (no loose sale)',
    lines: ['Syrup → Bottle', 'Suspension → Bottle', 'Drops → Bottle', 'Lotion → Bottle'],
  },
  {
    title: 'FLEXIBLE (both allowed)',
    lines: ['Injection → Box → Vial/Ampule', 'Sachet → Box → Sachet', 'Powder → Box → Sachet'],
  },
  {
    title: 'UNIT_ONLY',
    lines: ['Device → Piece', 'Thermometer → Piece', 'Shampoo → Bottle', 'Soap → Piece'],
  },
]
