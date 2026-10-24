import type { CheckResult, CheckStatus } from '../features/invoice-verification/checkTypes'

const BASE_URL: string = import.meta.env.VITE_API_URL ?? 'http://127.0.0.1:8000'

export type ApiFieldComparison = {
  field: string
  label: string
  visible: string | null
  signed: string | null
  status: CheckStatus
}

export type ApiReport = {
  checks: CheckResult[]
  field_comparisons: ApiFieldComparison[]
  next_actions: string[]
}

export type ApiSampleField = {
  field: string
  label: string
  value: string | null
  confidence: number
  unclear: boolean
}

export type ApiSample = {
  id: string
  label: string
  visible: ApiSampleField[]
}

export class ApiError extends Error {}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  let response: Response
  try {
    response = await fetch(`${BASE_URL}${path}`, init)
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') throw error
    throw new ApiError('The verification service could not be reached.')
  }
  if (!response.ok) {
    throw new ApiError(`The verification service returned an error (${response.status}).`)
  }
  try {
    return (await response.json()) as T
  } catch {
    throw new ApiError('The verification service sent an unreadable response.')
  }
}

export function fetchSamples(signal?: AbortSignal): Promise<ApiSample[]> {
  return request<ApiSample[]>('/api/v1/demo/samples', { signal })
}

export function verifySample(sampleId: string, signal?: AbortSignal): Promise<ApiReport> {
  return request<ApiReport>(`/api/v1/demo/samples/${encodeURIComponent(sampleId)}/verify`, {
    method: 'POST',
    signal,
  })
}
