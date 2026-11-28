import { BASE_URL } from '../../lib/api'

export type EvidenceLevel = 'complete' | 'partial' | 'missing'
export type Priority = 'low' | 'medium' | 'high'
export type CheckState = 'triggered' | 'not_triggered' | 'not_evaluated'

export type ApiCompany = {
  id: string
  name: string
  domain: string | null
  is_synthetic: boolean
}

export type ApiTransaction = {
  id: string
  seller_id: string
  buyer_id: string
  invoice_reference: string | null
  amount: string // an exact decimal string such as "4800000.00"
  currency: string
  occurred_on: string
  evidence_level: EvidenceLevel
  note: string | null
  is_synthetic: boolean
}

export type GraphResponse = {
  companies: ApiCompany[]
  transactions: ApiTransaction[]
  truncated: { companies: boolean; transactions: boolean }
  contains_synthetic_data: boolean
}

export type ApiSignal = {
  code: string
  title: string
  observed: string
  may_indicate: string
  does_not_prove: string
  transaction_ids: string[]
}

export type ApiCheck = { code: string; title: string; result: CheckState }
export type ApiNotEvaluated = { code: string; reason: string }

export type ApiFinding = {
  companies: { id: string; name: string }[]
  transaction_ids: string[]
  summary: string
  priority: Priority
  priority_explanation: string
  signals: ApiSignal[]
  not_evaluated: ApiNotEvaluated[]
  checks: ApiCheck[]
  disclaimer: string
}

export type FindingsResponse = {
  findings: ApiFinding[]
  truncated: boolean
  min_length: number
  max_length: number
}

export type Analysis =
  | {
      status: 'ready'
      findings: ApiFinding[]
      truncated: boolean
      minLength: number
      maxLength: number
    }
  | { status: 'unavailable'; message: string }

export type ExplorerResult =
  | { status: 'error'; message: string }
  | { status: 'ready'; graph: GraphResponse; analysis: Analysis }

export class ExplorerApiError extends Error {
  readonly kind: 'offline' | 'service'
  readonly code: string | null

  constructor(kind: 'offline' | 'service', message: string, code: string | null = null) {
    super(message)
    this.kind = kind
    this.code = code
  }
}

async function getJson<T>(path: string, signal: AbortSignal): Promise<T> {
  let response: Response
  try {
    response = await fetch(`${BASE_URL}${path}`, { signal })
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') throw error
    throw new ExplorerApiError(
      'offline',
      'The VerifiGST service could not be reached. Check that the backend is running and try again.',
    )
  }

  if (!response.ok) {
    let message = `The service returned an error (${response.status}).`
    let code: string | null = null
    try {
      const body = (await response.json()) as { error?: { code?: unknown; message?: unknown } } | null
      if (typeof body?.error?.message === 'string') message = body.error.message
      if (typeof body?.error?.code === 'string') code = body.error.code
    } catch {
      // Keep the generic message.
    }
    throw new ExplorerApiError('service', message, code)
  }

  try {
    return (await response.json()) as T
  } catch {
    throw new ExplorerApiError('service', 'The service sent an unreadable response.')
  }
}

export function fetchGraph(signal: AbortSignal): Promise<GraphResponse> {
  return getJson<GraphResponse>('/api/v1/graph', signal)
}

export function fetchFindings(signal: AbortSignal): Promise<FindingsResponse> {
  return getJson<FindingsResponse>('/api/v1/findings', signal)
}

function messageOf(reason: unknown): string {
  return reason instanceof ExplorerApiError
    ? reason.message
    : 'Something went wrong while loading the data.'
}

/**
 * Loads the graph and the findings in parallel. They fail independently: without the graph there
 * is nothing to draw, but without the findings the graph can still be shown, marked as not analysed.
 */
export async function loadExplorerData(signal: AbortSignal): Promise<ExplorerResult> {
  const [graph, findings] = await Promise.allSettled([fetchGraph(signal), fetchFindings(signal)])

  if (graph.status === 'rejected') {
    return { status: 'error', message: messageOf(graph.reason) }
  }

  const analysis: Analysis =
    findings.status === 'fulfilled'
      ? {
          status: 'ready',
          findings: findings.value.findings,
          truncated: findings.value.truncated,
          minLength: findings.value.min_length,
          maxLength: findings.value.max_length,
        }
      : { status: 'unavailable', message: messageOf(findings.reason) }

  return { status: 'ready', graph: graph.value, analysis }
}
