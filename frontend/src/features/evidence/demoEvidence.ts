export type EvidenceKind =
  | 'Fact'
  | 'Rule-based finding'
  | 'Uncertain information'
  | 'Investigator note'

export type EvidenceRecord = {
  id: string
  caseId: string
  kind: EvidenceKind
  subject: string
  check: string
  result: string
  explanation: string
  limitations: string
  source: string
  sourceType: string
  sourceAvailable: boolean
  timestamp: string
}

export const evidenceKinds: EvidenceKind[] = [
  'Fact',
  'Rule-based finding',
  'Uncertain information',
  'Investigator note',
]

const TXN = 'Demonstration transaction records'
const NOT_CONNECTED = ' (not connected in this demonstration)'

// All records below are synthetic. They describe no real company or transaction.
export const demoEvidence: EvidenceRecord[] = [
  {
    id: 'EV-D-001',
    caseId: 'CASE-D-001',
    kind: 'Fact',
    subject: 'Transactions T4, T5, T6',
    check: 'Transaction retrieval',
    result: 'Three transactions found, 10 to 12 Sep 2026',
    explanation:
      'T4 Dune Textiles to Elm Packaging, T5 Elm Packaging to Fern Agro, T6 Fern Agro to Dune Textiles.',
    limitations: 'Synthetic records. No external source was consulted.',
    source: TXN,
    sourceType: 'Transaction record',
    sourceAvailable: true,
    timestamp: '2026-10-14T09:10:00Z',
  },
  {
    id: 'EV-D-002',
    caseId: 'CASE-D-001',
    kind: 'Rule-based finding',
    subject: 'Transactions T4, T5, T6',
    check: 'Directed cycle of three companies',
    result: 'Pattern detected (high priority)',
    explanation: 'The three transactions form a cycle that completes within 3 days.',
    limitations:
      'An indicator for investigation only. Legitimate settlement arrangements can produce the same shape.',
    source: 'Demonstration graph rules',
    sourceType: 'Rule engine',
    sourceAvailable: true,
    timestamp: '2026-10-14T09:12:00Z',
  },
  {
    id: 'EV-D-003',
    caseId: 'CASE-D-001',
    kind: 'Rule-based finding',
    subject: 'Transactions T5, T6',
    check: 'Repeated invoice reference',
    result: 'INV-D-202 appears on two transactions',
    explanation: 'The same reference is recorded against T5 and T6.',
    limitations:
      'May be a data-entry error. It does not by itself show a duplicate payment.',
    source: 'Demonstration graph rules',
    sourceType: 'Rule engine',
    sourceAvailable: true,
    timestamp: '2026-10-14T09:12:00Z',
  },
  {
    id: 'EV-D-004',
    caseId: 'CASE-D-001',
    kind: 'Uncertain information',
    subject: 'Transactions T4, T5',
    check: 'Supporting document availability',
    result: 'No supporting documents found',
    explanation: 'No delivery or payment documents are attached to these transactions.',
    limitations: 'Absence from this record does not show the documents do not exist.',
    source: 'Document store' + NOT_CONNECTED,
    sourceType: 'Document store',
    sourceAvailable: false,
    timestamp: '2026-10-15T11:40:00Z',
  },
  {
    id: 'EV-D-005',
    caseId: 'CASE-D-002',
    kind: 'Fact',
    subject: 'Invoice INV-D-014',
    check: 'Signature verification',
    result: 'Signature valid for the signed payload',
    explanation: 'The signed payload verifies under the issuer public key in the fixture.',
    limitations: 'A valid signature does not show the goods or services were delivered.',
    source: 'Demonstration signature fixture',
    sourceType: 'Document verification',
    sourceAvailable: true,
    timestamp: '2026-10-09T08:05:00Z',
  },
  {
    id: 'EV-D-006',
    caseId: 'CASE-D-002',
    kind: 'Rule-based finding',
    subject: 'Invoice INV-D-014',
    check: 'Visible field comparison',
    result: 'Amount differs from the signed payload',
    explanation: 'The amount read from the visible invoice does not match the signed amount.',
    limitations: 'Can indicate an altered document or an extraction error.',
    source: 'Demonstration comparison rules',
    sourceType: 'Rule engine',
    sourceAvailable: true,
    timestamp: '2026-10-09T08:06:00Z',
  },
  {
    id: 'EV-D-007',
    caseId: 'CASE-D-002',
    kind: 'Uncertain information',
    subject: 'Invoice INV-D-014',
    check: 'Extraction confidence',
    result: 'Low confidence on the amount field',
    explanation: 'The amount was read with low confidence, so manual review is required.',
    limitations: 'Extracted text is not proof of authenticity.',
    source: 'Demonstration extraction fixture',
    sourceType: 'Document processing',
    sourceAvailable: true,
    timestamp: '2026-10-09T08:06:00Z',
  },
  {
    id: 'EV-D-008',
    caseId: 'CASE-D-003',
    kind: 'Rule-based finding',
    subject: 'Invoice INV-D-008',
    check: 'Payment account comparison',
    result: 'Account differs from the signed payload',
    explanation: 'The payment account on the visible invoice does not match the signed account.',
    limitations: 'The issuer may have changed accounts and communicated it separately.',
    source: 'Demonstration comparison rules',
    sourceType: 'Rule engine',
    sourceAvailable: true,
    timestamp: '2026-09-01T10:20:00Z',
  },
  {
    id: 'EV-D-009',
    caseId: 'CASE-D-003',
    kind: 'Investigator note',
    subject: 'Invoice INV-D-008',
    check: 'Reviewer note',
    result: 'Issuer contact requested',
    explanation:
      'The reviewer asked the issuer to confirm the payment account through an independent channel.',
    limitations: 'Awaiting a reply. This note is not a finding.',
    source: 'Investigator note (demonstration)',
    sourceType: 'Investigator',
    sourceAvailable: true,
    timestamp: '2026-10-10T12:15:00Z',
  },
  {
    id: 'EV-D-010',
    caseId: 'CASE-D-004',
    kind: 'Uncertain information',
    subject: 'Transactions T5, T6',
    check: 'Same-document comparison',
    result: 'Not checked',
    explanation:
      'The underlying documents were not available, so file hashes could not be compared.',
    limitations:
      'A repeated reference is not shown to be a repeated document until the files are compared.',
    source: 'Document store' + NOT_CONNECTED,
    sourceType: 'Document store',
    sourceAvailable: false,
    timestamp: '2026-09-28T07:45:00Z',
  },
  {
    id: 'EV-D-011',
    caseId: 'CASE-D-005',
    kind: 'Uncertain information',
    subject: 'Invoice INV-D-005',
    check: 'Issuer public key lookup',
    result: 'No key found',
    explanation:
      'No public key record exists for the claimed issuer, so the signature could not be checked.',
    limitations: 'The result is Unknown, not a pass. The issuer may simply not be enrolled.',
    source: 'Demonstration key-discovery fixture',
    sourceType: 'Key discovery',
    sourceAvailable: true,
    timestamp: '2026-09-05T13:30:00Z',
  },
  {
    id: 'EV-D-012',
    caseId: 'CASE-D-006',
    kind: 'Fact',
    subject: 'Transactions T1, T2, T3',
    check: 'Transaction retrieval',
    result: 'Three transactions found with complete supporting records',
    explanation:
      'T1 Alder Traders to Birch Metals, T2 Birch Metals to Cedar Logistics, T3 Cedar Logistics to Alder Traders.',
    limitations: 'Synthetic records. No external source was consulted.',
    source: TXN,
    sourceType: 'Transaction record',
    sourceAvailable: true,
    timestamp: '2026-08-05T09:00:00Z',
  },
  {
    id: 'EV-D-013',
    caseId: 'CASE-D-006',
    kind: 'Investigator note',
    subject: 'CASE-D-006',
    check: 'Closing note',
    result: 'Closed: supply relationship documented',
    explanation:
      'The investigator confirmed the documented supply relationship behind the cycle.',
    limitations: 'Synthetic note for demonstration.',
    source: 'Investigator note (demonstration)',
    sourceType: 'Investigator',
    sourceAvailable: true,
    timestamp: '2026-08-20T15:30:00Z',
  },
  {
    id: 'EV-D-014',
    caseId: 'CASE-D-007',
    kind: 'Rule-based finding',
    subject: 'Transaction T8',
    check: 'Transaction versus invoice amount',
    result: 'INR 610,000 recorded against a linked invoice of INR 640,000',
    explanation: 'The transaction is INR 30,000 lower than the linked invoice total.',
    limitations:
      'Can be a partial payment, a correction or timing. It is not assumed to be intentional.',
    source: 'Demonstration validation rules',
    sourceType: 'Rule engine',
    sourceAvailable: true,
    timestamp: '2026-07-28T10:00:00Z',
  },
  {
    id: 'EV-D-015',
    caseId: 'CASE-D-007',
    kind: 'Uncertain information',
    subject: 'Transaction T8',
    check: 'Payment record availability',
    result: 'No payment record found',
    explanation: 'No payment record or credit note is attached to explain the difference.',
    limitations: 'Absence from this record does not show that no payment record exists.',
    source: 'Payment records' + NOT_CONNECTED,
    sourceType: 'Payment records',
    sourceAvailable: false,
    timestamp: '2026-07-28T10:05:00Z',
  },
]
