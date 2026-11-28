import type cytoscape from 'cytoscape'
import { formatInr } from '../../lib/format'
import type {
  Analysis,
  ApiCompany,
  ApiFinding,
  ApiTransaction,
  CheckState,
  EvidenceLevel,
  Priority,
} from './explorerApi'

export type NodeStatus = 'none' | 'loop' | 'high' | 'unavailable'

export const statusLabels: Record<NodeStatus, string> = {
  none: 'Not in a loop found by this search',
  loop: 'In a trading loop',
  high: 'In a trading loop with several signals (high review priority)',
  unavailable: 'Loop analysis not available',
}

export const evidenceLabels: Record<EvidenceLevel, string> = {
  complete: 'Evidence complete',
  partial: 'Evidence partial',
  missing: 'Evidence missing',
}

export const priorityLabels: Record<Priority, string> = {
  low: 'Low',
  medium: 'Medium',
  high: 'High',
}

export const checkStateLabels: Record<CheckState, string> = {
  triggered: 'Triggered',
  not_triggered: 'Ran, nothing triggered',
  not_evaluated: 'Could not be evaluated',
}

/** A stable key for a loop: the ids of its companies in trade order. */
export function findingKey(finding: ApiFinding): string {
  return finding.companies.map((company) => company.id).join('>')
}

export function formatAmount(amount: string, currency: string): string {
  const value = Number(amount)
  if (currency === 'INR' && Number.isFinite(value)) return formatInr(value)
  return `${currency} ${amount}`
}

/**
 * Review status of each company. When the analysis is unavailable every company is marked
 * 'unavailable', never 'none', because "no loop found" would claim a check that did not run.
 */
export function companyStatuses(
  companies: ApiCompany[],
  analysis: Analysis,
): Map<string, NodeStatus> {
  const statuses = new Map<string, NodeStatus>()
  const start: NodeStatus = analysis.status === 'ready' ? 'none' : 'unavailable'
  for (const company of companies) statuses.set(company.id, start)
  if (analysis.status !== 'ready') return statuses

  for (const finding of analysis.findings) {
    for (const company of finding.companies) {
      if (!statuses.has(company.id)) continue
      if (finding.priority === 'high') statuses.set(company.id, 'high')
      else if (statuses.get(company.id) === 'none') statuses.set(company.id, 'loop')
    }
  }
  return statuses
}

/**
 * A repeatable order for the companies: a depth-first walk that follows the trades, starting from
 * the first company by name. Companies in the same loop end up next to each other.
 */
export function traversalOrder(
  companies: ApiCompany[],
  transactions: ApiTransaction[],
): Map<string, number> {
  const nameOf = new Map(companies.map((company) => [company.id, company.name]))
  const byName = (a: string, b: string) =>
    (nameOf.get(a) ?? a).localeCompare(nameOf.get(b) ?? b) || a.localeCompare(b)

  const outgoing = new Map<string, string[]>()
  for (const t of transactions) {
    const list = outgoing.get(t.seller_id) ?? []
    list.push(t.buyer_id)
    outgoing.set(t.seller_id, list)
  }
  for (const list of outgoing.values()) list.sort(byName)

  const order = new Map<string, number>()
  const starts = companies.map((company) => company.id).sort(byName)
  for (const start of starts) {
    if (order.has(start)) continue
    const stack = [start]
    while (stack.length > 0) {
      const id = stack.pop() as string
      if (order.has(id)) continue
      order.set(id, order.size)
      const next = outgoing.get(id) ?? []
      for (let i = next.length - 1; i >= 0; i--) {
        if (!order.has(next[i])) stack.push(next[i])
      }
    }
  }
  return order
}

const CIRCLE_LAYOUT_LIMIT = 40

export function buildLayout(
  companies: ApiCompany[],
  transactions: ApiTransaction[],
): cytoscape.LayoutOptions {
  if (companies.length > CIRCLE_LAYOUT_LIMIT) {
    return { name: 'cose', animate: false, fit: true, padding: 60, randomize: true }
  }
  const order = traversalOrder(companies, transactions)
  return {
    name: 'circle',
    fit: true,
    padding: 60,
    sort: (a, b) => (order.get(a.id()) ?? 0) - (order.get(b.id()) ?? 0),
  }
}
