export type VerificationStatus = 'verified' | 'failed' | 'unknown' | 'pending'

export type DemoInvoice = {
  id: string
  date: string
  status: VerificationStatus
}

export type CasePriority =
  | 'High priority'
  | 'Elevated priority'
  | 'Review'
  | 'Informational'

export type DemoCase = {
  id: string
  title: string
  priority: CasePriority
  status: 'Open' | 'In review' | 'Closed'
  updated: string
  evidenceGap: boolean
  lastAction: string
}

export type PatternLevel =
  | 'High-priority pattern detected'
  | 'Suspicious pattern detected'
  | 'Insufficient data'

export type DemoPattern = {
  id: string
  label: string
  level: PatternLevel
  date: string
}

// All records below are synthetic. They describe no real company or transaction.
// Periods are measured back from this fixed date so results are reproducible.
export const REFERENCE_DATE = '2026-10-18'

export const invoices: DemoInvoice[] = [
  { id: 'INV-D-001', date: '2026-06-14', status: 'verified' },
  { id: 'INV-D-002', date: '2026-06-28', status: 'verified' },
  { id: 'INV-D-003', date: '2026-07-09', status: 'failed' },
  { id: 'INV-D-004', date: '2026-07-21', status: 'verified' },
  { id: 'INV-D-005', date: '2026-08-02', status: 'unknown' },
  { id: 'INV-D-006', date: '2026-08-11', status: 'verified' },
  { id: 'INV-D-007', date: '2026-08-19', status: 'verified' },
  { id: 'INV-D-008', date: '2026-08-27', status: 'failed' },
  { id: 'INV-D-009', date: '2026-09-03', status: 'pending' },
  { id: 'INV-D-010', date: '2026-09-08', status: 'verified' },
  { id: 'INV-D-011', date: '2026-09-15', status: 'unknown' },
  { id: 'INV-D-012', date: '2026-09-22', status: 'verified' },
  { id: 'INV-D-013', date: '2026-09-29', status: 'verified' },
  { id: 'INV-D-014', date: '2026-10-02', status: 'failed' },
  { id: 'INV-D-015', date: '2026-10-06', status: 'pending' },
  { id: 'INV-D-016', date: '2026-10-09', status: 'verified' },
  { id: 'INV-D-017', date: '2026-10-13', status: 'unknown' },
  { id: 'INV-D-018', date: '2026-10-16', status: 'verified' },
]

export const cases: DemoCase[] = [
  {
    id: 'CASE-D-001',
    title: 'Circular trade between three demonstration companies',
    priority: 'High priority',
    status: 'Open',
    updated: '2026-10-15',
    evidenceGap: true,
    lastAction: 'Graph finding linked to case',
  },
  {
    id: 'CASE-D-002',
    title: 'Signed amount differs from visible amount',
    priority: 'Elevated priority',
    status: 'In review',
    updated: '2026-10-12',
    evidenceGap: false,
    lastAction: 'Reviewer assigned',
  },
  {
    id: 'CASE-D-003',
    title: 'Payment account differs from signed payload',
    priority: 'High priority',
    status: 'In review',
    updated: '2026-10-10',
    evidenceGap: false,
    lastAction: 'Status changed to In review',
  },
  {
    id: 'CASE-D-004',
    title: 'Repeated invoice reference across two suppliers',
    priority: 'Review',
    status: 'Open',
    updated: '2026-09-30',
    evidenceGap: true,
    lastAction: 'Supporting evidence requested',
  },
  {
    id: 'CASE-D-005',
    title: 'Issuer public key not found',
    priority: 'Review',
    status: 'Open',
    updated: '2026-09-05',
    evidenceGap: true,
    lastAction: 'Case created',
  },
  {
    id: 'CASE-D-006',
    title: 'Circular trade with complete supporting evidence',
    priority: 'Informational',
    status: 'Closed',
    updated: '2026-08-20',
    evidenceGap: false,
    lastAction: 'Closed with investigator note',
  },
  {
    id: 'CASE-D-007',
    title: 'Transaction amount inconsistent with linked invoice',
    priority: 'Elevated priority',
    status: 'Open',
    updated: '2026-07-28',
    evidenceGap: true,
    lastAction: 'Case created',
  },
]

export const patterns: DemoPattern[] = [
  {
    id: 'PAT-D-01',
    label: 'Directed cycle across three companies',
    level: 'High-priority pattern detected',
    date: '2026-10-14',
  },
  {
    id: 'PAT-D-02',
    label: 'Repeated invoice reference across related entities',
    level: 'Suspicious pattern detected',
    date: '2026-09-29',
  },
  {
    id: 'PAT-D-03',
    label: 'Unusual transaction frequency between two companies',
    level: 'Suspicious pattern detected',
    date: '2026-09-02',
  },
  {
    id: 'PAT-D-04',
    label: 'Directed cycle with documented supply relationship',
    level: 'Suspicious pattern detected',
    date: '2026-08-18',
  },
  {
    id: 'PAT-D-05',
    label: 'Dense relationship with too little data to assess',
    level: 'Insufficient data',
    date: '2026-07-25',
  },
]
