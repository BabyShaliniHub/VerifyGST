export type CheckStatus = 'passed' | 'failed' | 'unknown' | 'not_checked' | 'manual_review'

export type CheckResult = {
  id: string
  label: string
  status: CheckStatus
  detail: string
}

export const FIELD_KEYS = [
  'invoiceNumber',
  'invoiceDate',
  'issuer',
  'buyer',
  'amount',
  'paymentAccount',
] as const

export type FieldKey = (typeof FIELD_KEYS)[number]
export type FieldValues = Record<FieldKey, string>

export const fieldLabels: Record<FieldKey, string> = {
  invoiceNumber: 'Invoice number',
  invoiceDate: 'Invoice date',
  issuer: 'Issuer',
  buyer: 'Buyer',
  amount: 'Amount',
  paymentAccount: 'Payment account',
}

export type SampleInvoice = {
  id: string
  label: string
  visible: FieldValues
  signed: FieldValues | null
  lowConfidence: FieldKey[]
  checks: CheckResult[]
  nextActions: string[]
}

type Tuple = [CheckStatus, string]

const CHECK_LABELS = [
  'Field extraction',
  'Issuer public key',
  'Signature verification',
  'Signed payload comparison',
  'Duplicate reference check',
]

const OFFICIAL_CHECK: CheckResult = {
  id: 'check-official',
  label: 'IRN and QR verification (official)',
  status: 'not_checked',
  detail:
    'No authorized e-invoice verification service is connected. VerifiGST does not replace the official process.',
}

function buildChecks(tuples: Tuple[]): CheckResult[] {
  const base = tuples.map(([status, detail], i) => ({
    id: `check-${i}`,
    label: CHECK_LABELS[i],
    status,
    detail,
  }))
  return [...base, OFFICIAL_CHECK]
}

// All samples are synthetic. They describe no real company, invoice or account.
const BASE: FieldValues = {
  invoiceNumber: 'SYN-2026-0142',
  invoiceDate: '2026-10-02',
  issuer: 'Grove Chemicals',
  buyer: 'Hazel Components',
  amount: 'INR 640,000.00',
  paymentAccount: 'Account ending 5521',
}

export const samples: SampleInvoice[] = [
  {
    id: 'intact',
    label: 'Intact invoice with a valid signature',
    visible: BASE,
    signed: BASE,
    lowConfidence: [],
    checks: buildChecks([
      ['passed', 'All fields were read with high confidence (98 percent average).'],
      ['passed', 'A key was found for the issuer in the demonstration enrolled-issuer list.'],
      ['passed', 'The signature verifies for the signed payload.'],
      ['passed', 'All six compared fields match the signed payload.'],
      ['passed', 'No other record in the demonstration data uses this reference.'],
    ]),
    nextActions: [
      'Compare the invoice with delivery and payment records. A valid signature does not show that goods or services were delivered.',
    ],
  },
  {
    id: 'amount',
    label: 'Visible amount differs from the signed amount',
    visible: { ...BASE, amount: 'INR 840,000.00' },
    signed: BASE,
    lowConfidence: [],
    checks: buildChecks([
      ['passed', 'All fields were read with high confidence (97 percent average).'],
      ['passed', 'A key was found for the issuer in the demonstration enrolled-issuer list.'],
      ['passed', 'The signature verifies for the signed payload.'],
      ['failed', 'The amount differs: INR 840,000.00 on the invoice, INR 640,000.00 in the signed payload.'],
      ['passed', 'No other record in the demonstration data uses this reference.'],
    ]),
    nextActions: [
      'Do not rely on the visible amount. Obtain the original invoice from the issuer through an independent channel.',
      'Find out how the visible document was produced.',
    ],
  },
  {
    id: 'account',
    label: 'Payment account differs from the signed account',
    visible: { ...BASE, paymentAccount: 'Account ending 9083' },
    signed: BASE,
    lowConfidence: [],
    checks: buildChecks([
      ['passed', 'All fields were read with high confidence (97 percent average).'],
      ['passed', 'A key was found for the issuer in the demonstration enrolled-issuer list.'],
      ['passed', 'The signature verifies for the signed payload.'],
      ['failed', 'The payment account differs from the signed payload.'],
      ['passed', 'No other record in the demonstration data uses this reference.'],
    ]),
    nextActions: [
      'Do not release payment. Confirm the payment account with the issuer through an independent channel.',
    ],
  },
  {
    id: 'bad-signature',
    label: 'Signature does not verify',
    visible: BASE,
    signed: null,
    lowConfidence: [],
    checks: buildChecks([
      ['passed', 'All fields were read with high confidence (96 percent average).'],
      ['passed', 'A key was found for the issuer in the demonstration enrolled-issuer list.'],
      ['failed', 'The signature does not verify for the signed payload.'],
      ['not_checked', 'Not run, because the signed payload cannot be trusted.'],
      ['passed', 'No other record in the demonstration data uses this reference.'],
    ]),
    nextActions: [
      'Treat the document as unverified. Ask the issuer to confirm or re-issue the invoice.',
    ],
  },
  {
    id: 'unknown-key',
    label: 'Issuer public key not found',
    visible: BASE,
    signed: null,
    lowConfidence: [],
    checks: buildChecks([
      ['passed', 'All fields were read with high confidence (98 percent average).'],
      ['unknown', 'No public key was found for the claimed issuer.'],
      ['unknown', 'The signature cannot be checked without a key.'],
      ['not_checked', 'Not run, because no key was found.'],
      ['passed', 'No other record in the demonstration data uses this reference.'],
    ]),
    nextActions: [
      'Check whether the issuer is enrolled and ask them to publish or confirm their verification key.',
      'An unknown key is never treated as a pass.',
    ],
  },
  {
    id: 'low-confidence',
    label: 'Low-confidence extraction',
    visible: { ...BASE, invoiceNumber: 'SYN-2026-01?2', amount: 'INR 6?0,000.00' },
    signed: BASE,
    lowConfidence: ['invoiceNumber', 'amount'],
    checks: buildChecks([
      ['manual_review', 'The invoice number and amount were read with low confidence (58 and 61 percent).'],
      ['passed', 'A key was found for the issuer in the demonstration enrolled-issuer list.'],
      ['passed', 'The signature verifies for the signed payload.'],
      ['manual_review', 'Two fields could not be read reliably. The other fields match.'],
      ['unknown', 'The reference is unreliable, so a duplicate check cannot be trusted.'],
    ]),
    nextActions: [
      'Review the document manually and correct the extracted fields.',
      'Run the checks again after the fields are corrected.',
    ],
  },
  {
    id: 'repeated',
    label: 'Repeated invoice reference',
    visible: { ...BASE, invoiceNumber: 'INV-D-202' },
    signed: { ...BASE, invoiceNumber: 'INV-D-202' },
    lowConfidence: [],
    checks: buildChecks([
      ['passed', 'All fields were read with high confidence (98 percent average).'],
      ['passed', 'A key was found for the issuer in the demonstration enrolled-issuer list.'],
      ['passed', 'The signature verifies for the signed payload.'],
      ['passed', 'All six compared fields match the signed payload.'],
      ['manual_review', 'The same reference appears on two other records in the demonstration data. A repeated reference is not proof of a duplicate payment.'],
    ]),
    nextActions: [
      'Compare the documents behind the repeated reference, including file hashes, before drawing any conclusion.',
    ],
  },
]

export const uploadChecks: CheckResult[] = buildChecks(
  CHECK_LABELS.map(
    (): Tuple => [
      'not_checked',
      'The verification engine is not connected in this demonstration, so this file was not checked.',
    ],
  ),
)
