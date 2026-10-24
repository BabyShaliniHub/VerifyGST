export type CheckStatus = 'passed' | 'failed' | 'unknown' | 'not_checked' | 'manual_review'

export type CheckResult = {
  id: string
  label: string
  status: CheckStatus
  detail: string
}

const NOT_READ = 'Uploaded files are not read yet, so this file was not checked.'

// Shown for any uploaded file: nothing is extracted or verified until the engine can read files.
export const uploadChecks: CheckResult[] = [
  { id: 'field_extraction', label: 'Field extraction', status: 'not_checked', detail: NOT_READ },
  { id: 'issuer_key', label: 'Issuer public key', status: 'not_checked', detail: NOT_READ },
  { id: 'signature', label: 'Signature verification', status: 'not_checked', detail: NOT_READ },
  { id: 'issuer_identity', label: 'Issuer identity', status: 'not_checked', detail: NOT_READ },
  { id: 'payload_comparison', label: 'Signed payload comparison', status: 'not_checked', detail: NOT_READ },
  { id: 'duplicate_reference', label: 'Duplicate reference check', status: 'not_checked', detail: NOT_READ },
  {
    id: 'official_einvoice',
    label: 'IRN and QR verification (official)',
    status: 'not_checked',
    detail:
      'No authorized e-invoice verification service is connected. VerifiGST does not replace the official process.',
  },
]
