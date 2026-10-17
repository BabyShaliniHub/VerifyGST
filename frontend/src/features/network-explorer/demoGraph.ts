export type NodeStatus = 'none' | 'suspicious' | 'high' | 'insufficient'
export type EvidenceLevel = 'complete' | 'partial' | 'missing'
export type FindingLevel = 'Suspicious pattern detected' | 'High-priority pattern detected'

export type DemoCompany = {
  id: string
  name: string
  demoRef: string
  status: NodeStatus
  x: number
  y: number
}

export type DemoTransaction = {
  id: string
  source: string
  target: string
  invoiceRef: string
  amountInr: number
  date: string
  evidence: EvidenceLevel
  note?: string
}

export type DemoFinding = {
  id: string
  title: string
  level: FindingLevel
  rule: string
  companyIds: string[]
  transactionIds: string[]
  supportingData: string[]
  limitations: string
  nextStep: string
}

export const statusLabels: Record<NodeStatus, string> = {
  none: 'No configured rule triggered',
  suspicious: 'Suspicious pattern detected',
  high: 'High-priority pattern detected',
  insufficient: 'Insufficient data',
}

export const evidenceLabels: Record<EvidenceLevel, string> = {
  complete: 'Evidence complete',
  partial: 'Evidence partial',
  missing: 'Evidence missing',
}

// All records below are synthetic. They describe no real company or transaction.
export const companies: DemoCompany[] = [
  { id: 'C1', name: 'Alder Traders', demoRef: 'DEMO-C1', status: 'suspicious', x: 120, y: 260 },
  { id: 'C2', name: 'Birch Metals', demoRef: 'DEMO-C2', status: 'suspicious', x: 340, y: 100 },
  { id: 'C3', name: 'Cedar Logistics', demoRef: 'DEMO-C3', status: 'suspicious', x: 340, y: 420 },
  { id: 'C4', name: 'Dune Textiles', demoRef: 'DEMO-C4', status: 'high', x: 980, y: 260 },
  { id: 'C5', name: 'Elm Packaging', demoRef: 'DEMO-C5', status: 'high', x: 1200, y: 100 },
  { id: 'C6', name: 'Fern Agro', demoRef: 'DEMO-C6', status: 'high', x: 1200, y: 420 },
  { id: 'C7', name: 'Grove Chemicals', demoRef: 'DEMO-C7', status: 'none', x: 560, y: 420 },
  { id: 'C8', name: 'Hazel Components', demoRef: 'DEMO-C8', status: 'insufficient', x: 770, y: 340 },
]

export const transactions: DemoTransaction[] = [
  { id: 'T1', source: 'C1', target: 'C2', invoiceRef: 'INV-D-101', amountInr: 1250000, date: '2026-07-05', evidence: 'complete' },
  { id: 'T2', source: 'C2', target: 'C3', invoiceRef: 'INV-D-102', amountInr: 1180000, date: '2026-07-19', evidence: 'complete' },
  { id: 'T3', source: 'C3', target: 'C1', invoiceRef: 'INV-D-103', amountInr: 1300000, date: '2026-08-02', evidence: 'complete' },
  { id: 'T4', source: 'C4', target: 'C5', invoiceRef: 'INV-D-201', amountInr: 4800000, date: '2026-09-10', evidence: 'missing' },
  { id: 'T5', source: 'C5', target: 'C6', invoiceRef: 'INV-D-202', amountInr: 4790000, date: '2026-09-11', evidence: 'missing' },
  { id: 'T6', source: 'C6', target: 'C4', invoiceRef: 'INV-D-202', amountInr: 4780000, date: '2026-09-12', evidence: 'partial' },
  { id: 'T7', source: 'C3', target: 'C7', invoiceRef: 'INV-D-104', amountInr: 640000, date: '2026-08-14', evidence: 'complete' },
  {
    id: 'T8',
    source: 'C7',
    target: 'C8',
    invoiceRef: 'INV-D-105',
    amountInr: 610000,
    date: '2026-08-28',
    evidence: 'partial',
    note: 'The linked invoice total is INR 640,000 but the transaction records INR 610,000. This could be a partial payment or a correction.',
  },
  { id: 'T9', source: 'C8', target: 'C4', invoiceRef: 'INV-D-106', amountInr: 520000, date: '2026-09-05', evidence: 'partial' },
]

export const findings: DemoFinding[] = [
  {
    id: 'FIND-D-01',
    title: 'Directed cycle across three companies, evidence complete',
    level: 'Suspicious pattern detected',
    rule: 'Demonstration rule: directed transaction cycle of three companies',
    companyIds: ['C1', 'C2', 'C3'],
    transactionIds: ['T1', 'T2', 'T3'],
    supportingData: [
      'The cycle spans 05 Jul 2026 to 02 Aug 2026.',
      'All three transactions have complete supporting evidence in the demonstration record.',
      'Amounts are within about 10 percent of each other.',
    ],
    limitations:
      'A cycle alone is not evidence of wrongdoing. Circular flows can arise from legitimate multi-stage processing or returns.',
    nextStep:
      'Confirm the documented supply relationship. If the evidence holds, the case can be closed with a note.',
  },
  {
    id: 'FIND-D-02',
    title: 'Directed cycle with evidence gaps and a repeated invoice reference',
    level: 'High-priority pattern detected',
    rule: 'Demonstration rule: directed cycle of three companies completed within a few days, with missing evidence',
    companyIds: ['C4', 'C5', 'C6'],
    transactionIds: ['T4', 'T5', 'T6'],
    supportingData: [
      'The cycle completes within 3 days (10 Sep 2026 to 12 Sep 2026).',
      'Invoice reference INV-D-202 appears on two transactions.',
      'Supporting evidence is missing for two transactions and partial for one.',
      'Amounts differ by less than 1 percent.',
    ],
    limitations:
      'These are indicators for investigation, not proof. Rapid circular flows can occur in legitimate settlement arrangements, and missing evidence may only mean it has not been collected yet.',
    nextStep:
      'Request supporting delivery and payment records for all three transactions and compare the documents behind INV-D-202.',
  },
]
