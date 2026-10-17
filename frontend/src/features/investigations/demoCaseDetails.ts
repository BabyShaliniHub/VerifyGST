export type CaseDetail = {
  created: string
  companies: string[]
  records: string[]
  evidenceCompleteness: string
  reasons: string[]
  nextStep: string
}

// Synthetic detail for the demonstration cases in features/overview/demoData.ts.
export const caseDetails: Record<string, CaseDetail> = {
  'CASE-D-001': {
    created: '2026-10-14',
    companies: ['Dune Textiles', 'Elm Packaging', 'Fern Agro'],
    records: ['Transactions T4, T5, T6', 'Invoice references INV-D-201, INV-D-202'],
    evidenceCompleteness: 'Low: 0 of 3 transactions fully supported (2 missing, 1 partial)',
    reasons: [
      'Directed cycle of three companies completed within 3 days (finding FIND-D-02).',
      'Invoice reference INV-D-202 appears on two transactions.',
      'Supporting evidence is missing or partial for all three transactions.',
    ],
    nextStep:
      'Request supporting delivery and payment records for all three transactions and compare the documents behind INV-D-202.',
  },
  'CASE-D-002': {
    created: '2026-10-09',
    companies: ['Grove Chemicals', 'Hazel Components'],
    records: ['Invoice INV-D-014'],
    evidenceCompleteness:
      'Moderate: signed payload and visible fields are available, delivery evidence not yet reviewed',
    reasons: [
      'The amount on the visible invoice differs from the amount in the signed payload.',
      'This can indicate an altered document or an extraction error and needs manual review.',
    ],
    nextStep:
      'Compare the original invoice file with the signed payload and review the extraction confidence.',
  },
  'CASE-D-003': {
    created: '2026-09-01',
    companies: ['Fern Agro'],
    records: ['Invoice INV-D-008'],
    evidenceCompleteness: 'Moderate: signed payload and visible fields are available',
    reasons: [
      'The payment account on the visible invoice differs from the account in the signed payload.',
      'A changed payment account is a reason to confirm the details with the issuer separately.',
    ],
    nextStep:
      'Confirm the correct payment account with the issuer through an independent channel before any payment is released.',
  },
  'CASE-D-004': {
    created: '2026-09-28',
    companies: ['Elm Packaging', 'Fern Agro'],
    records: ['Transactions T5, T6', 'Invoice reference INV-D-202'],
    evidenceCompleteness: 'Low: no supporting documents attached for the repeated reference',
    reasons: [
      'The same invoice reference appears on two different transactions.',
      'A repeated reference can come from a data-entry error or document reuse and does not by itself show a duplicate payment.',
    ],
    nextStep:
      'Request the underlying invoice documents for both transactions and check whether they are the same document.',
  },
  'CASE-D-005': {
    created: '2026-09-05',
    companies: ['Hazel Components'],
    records: ['Invoice INV-D-005'],
    evidenceCompleteness:
      'None: the issuer public key could not be found, so the signature could not be checked',
    reasons: [
      'No public key was found for the claimed issuer.',
      'An unknown key is never treated as a successful verification.',
    ],
    nextStep:
      'Check whether the issuer is enrolled and ask them to publish or confirm their verification key.',
  },
  'CASE-D-006': {
    created: '2026-08-05',
    companies: ['Alder Traders', 'Birch Metals', 'Cedar Logistics'],
    records: ['Transactions T1, T2, T3'],
    evidenceCompleteness: 'High: 3 of 3 transactions fully supported',
    reasons: [
      'Directed cycle of three companies (finding FIND-D-01).',
      'The supply relationship is documented and the evidence is complete.',
    ],
    nextStep: 'No further action. Closed with an investigator note.',
  },
  'CASE-D-007': {
    created: '2026-07-28',
    companies: ['Grove Chemicals', 'Hazel Components'],
    records: ['Transaction T8', 'Invoice reference INV-D-105'],
    evidenceCompleteness: 'Partial: transaction evidence is partial, linked invoice total is available',
    reasons: [
      'The linked invoice total is INR 640,000 but the transaction records INR 610,000.',
      'This can be a partial payment, a correction or timing. It is not assumed to be intentional.',
    ],
    nextStep:
      'Ask for the payment record and any credit note that explains the INR 30,000 difference.',
  },
}
