import { useMemo, type ReactNode } from 'react'
import { formatDate } from '../../lib/format'
import type { Analysis, ApiCompany, ApiFinding, ApiTransaction } from './explorerApi'
import {
  checkStateLabels,
  evidenceLabels,
  findingKey,
  formatAmount,
  priorityLabels,
  statusLabels,
  type NodeStatus,
} from './explorerModel'
import type { Selection } from './NetworkGraph'

type NameOf = (id: string) => string

function LinkButton({ onClick, children }: { onClick: () => void; children: ReactNode }) {
  return (
    <button type="button" onClick={onClick} className="text-forest underline underline-offset-2">
      {children}
    </button>
  )
}

function TransactionList({
  items,
  direction,
  nameOf,
  onSelect,
}: {
  items: ApiTransaction[]
  direction: 'in' | 'out'
  nameOf: NameOf
  onSelect: (s: Selection) => void
}) {
  if (items.length === 0) return <p className="mt-1">None in this dataset.</p>
  return (
    <ul className="mt-1 divide-y divide-line border border-line">
      {items.map((t) => (
        <li key={t.id}>
          <button
            type="button"
            onClick={() => onSelect({ kind: 'edge', id: t.id })}
            className="w-full px-3 py-2 text-left hover:bg-canvas"
          >
            <span className="font-semibold">{t.invoice_reference ?? 'No invoice reference'}</span>
            {' - '}
            {formatAmount(t.amount, t.currency)}
            <span className="block text-base text-ink/70">
              {direction === 'in' ? 'from ' : 'to '}
              {nameOf(direction === 'in' ? t.seller_id : t.buyer_id)}
            </span>
          </button>
        </li>
      ))}
    </ul>
  )
}

function CompanyDetails({
  company,
  transactions,
  status,
  nameOf,
  onSelect,
}: {
  company: ApiCompany
  transactions: ApiTransaction[]
  status: NodeStatus
  nameOf: NameOf
  onSelect: (s: Selection) => void
}) {
  const incoming = transactions.filter((t) => t.buyer_id === company.id)
  const outgoing = transactions.filter((t) => t.seller_id === company.id)
  return (
    <div>
      <h2 className="text-xl font-semibold">{company.name}</h2>
      <p className="text-base text-ink/70">
        {company.domain ?? 'No domain recorded'}
        {company.is_synthetic ? ' - synthetic demonstration company' : ''}
      </p>
      <p className="mt-3">
        <span className="font-semibold">Loop analysis:</span> {statusLabels[status]}
      </p>
      <h3 className="mt-4 font-semibold">Incoming transactions ({incoming.length})</h3>
      <TransactionList items={incoming} direction="in" nameOf={nameOf} onSelect={onSelect} />
      <h3 className="mt-4 font-semibold">Outgoing transactions ({outgoing.length})</h3>
      <TransactionList items={outgoing} direction="out" nameOf={nameOf} onSelect={onSelect} />
    </div>
  )
}

function TransactionDetails({
  transaction: t,
  transactions,
  nameOf,
  onSelect,
}: {
  transaction: ApiTransaction
  transactions: ApiTransaction[]
  nameOf: NameOf
  onSelect: (s: Selection) => void
}) {
  const sameRef = t.invoice_reference
    ? transactions.filter((o) => o.id !== t.id && o.invoice_reference === t.invoice_reference)
    : []
  return (
    <div>
      <h2 className="text-xl font-semibold">Transaction</h2>
      <dl className="mt-3 grid grid-cols-[8rem_1fr] gap-x-3 gap-y-2">
        <dt className="font-semibold">From</dt>
        <dd>
          <LinkButton onClick={() => onSelect({ kind: 'node', id: t.seller_id })}>
            {nameOf(t.seller_id)}
          </LinkButton>
        </dd>
        <dt className="font-semibold">To</dt>
        <dd>
          <LinkButton onClick={() => onSelect({ kind: 'node', id: t.buyer_id })}>
            {nameOf(t.buyer_id)}
          </LinkButton>
        </dd>
        <dt className="font-semibold">Invoice</dt>
        <dd>{t.invoice_reference ?? 'No invoice reference'}</dd>
        <dt className="font-semibold">Amount</dt>
        <dd>{formatAmount(t.amount, t.currency)}</dd>
        <dt className="font-semibold">Date</dt>
        <dd>{formatDate(t.occurred_on)}</dd>
        <dt className="font-semibold">Evidence</dt>
        <dd>{evidenceLabels[t.evidence_level]}</dd>
      </dl>
      {sameRef.length > 0 && (
        <p className="mt-3">
          The reference {t.invoice_reference} also appears on {sameRef.length} other transaction
          {sameRef.length > 1 ? 's' : ''}.
        </p>
      )}
      {t.note && <p className="mt-3">{t.note}</p>}
    </div>
  )
}

function FindingCard({
  finding,
  active,
  onToggle,
}: {
  finding: ApiFinding
  active: boolean
  onToggle: () => void
}) {
  const total = finding.checks.length
  const notEvaluated = finding.checks.filter((c) => c.result === 'not_evaluated').length
  return (
    <article className="border-t border-line pt-4">
      <h3 className="font-semibold">{finding.summary}</h3>
      <p className="mt-1">
        <span className="font-semibold">Review priority:</span>{' '}
        {priorityLabels[finding.priority]}
      </p>
      <p className="text-base text-ink/70">{finding.priority_explanation}</p>

      {finding.signals.length === 0 ? (
        <p className="mt-3">
          No additional signals were found. {total - notEvaluated} of {total} checks ran and none
          triggered
          {notEvaluated > 0 ? `; ${notEvaluated} could not be evaluated` : ''}. A quiet loop is
          not cleared: the loop itself is still a pattern worth knowing about.
        </p>
      ) : (
        <ul className="mt-3 flex flex-col gap-3">
          {finding.signals.map((signal) => (
            <li key={signal.code} className="border-l-4 border-gold bg-canvas px-3 py-2">
              <p className="font-semibold">{signal.title}</p>
              <dl className="mt-1 flex flex-col gap-1">
                <div>
                  <dt className="inline font-semibold">What we saw: </dt>
                  <dd className="inline">{signal.observed}</dd>
                </div>
                <div>
                  <dt className="inline font-semibold">Why it may matter: </dt>
                  <dd className="inline">{signal.may_indicate}</dd>
                </div>
                <div>
                  <dt className="inline font-semibold">What it does not prove: </dt>
                  <dd className="inline">{signal.does_not_prove}</dd>
                </div>
              </dl>
            </li>
          ))}
        </ul>
      )}

      <details className="mt-3">
        <summary className="cursor-pointer font-semibold">Checks run on this loop</summary>
        <ul className="mt-2 list-disc pl-5">
          {finding.checks.map((check) => (
            <li key={check.code}>
              {check.title}: {checkStateLabels[check.result]}
            </li>
          ))}
        </ul>
        {finding.not_evaluated.map((item) => (
          <p key={item.code} className="mt-2">
            {item.reason}
          </p>
        ))}
      </details>

      <p className="mt-3 text-base text-ink/70">{finding.disclaimer}</p>
      <button
        type="button"
        onClick={onToggle}
        aria-pressed={active}
        className={`mt-3 rounded-md border px-3 py-2 ${
          active ? 'border-forest bg-forest text-white' : 'border-line bg-surface hover:bg-canvas'
        }`}
      >
        {active ? 'Remove highlight' : 'Highlight on graph'}
      </button>
    </article>
  )
}

function FindingsSection({
  analysis,
  highlightedKey,
  onHighlight,
  onRetry,
}: {
  analysis: Analysis
  highlightedKey: string | null
  onHighlight: (key: string | null) => void
  onRetry: () => void
}) {
  if (analysis.status === 'unavailable') {
    return (
      <div role="alert" className="mt-3 border-l-4 border-gold bg-canvas px-3 py-2">
        <p>Loop analysis is not available right now. {analysis.message}</p>
        <button
          type="button"
          onClick={onRetry}
          className="mt-2 rounded-md border border-line bg-surface px-3 py-2 hover:bg-canvas"
        >
          Try again
        </button>
      </div>
    )
  }

  return (
    <>
      <p className="mt-1 text-base text-ink/70">
        Searched for loops of {analysis.minLength} to {analysis.maxLength} companies. Other
        patterns are not checked here.
      </p>
      {analysis.truncated && (
        <p className="mt-2 border-l-4 border-gold bg-canvas px-3 py-2">
          The search stopped at its limit, so this list is incomplete.
        </p>
      )}
      {analysis.findings.length === 0 && (
        <p className="mt-3">
          No trading loops of {analysis.minLength} to {analysis.maxLength} companies were found in
          this data.
        </p>
      )}
      <div className="mt-3 flex flex-col gap-4">
        {analysis.findings.map((finding) => {
          const key = findingKey(finding)
          return (
            <FindingCard
              key={key}
              finding={finding}
              active={highlightedKey === key}
              onToggle={() => onHighlight(highlightedKey === key ? null : key)}
            />
          )
        })}
      </div>
    </>
  )
}

type Props = {
  companies: ApiCompany[]
  transactions: ApiTransaction[]
  statuses: Map<string, NodeStatus>
  analysis: Analysis
  selection: Selection
  highlightedKey: string | null
  onSelect: (s: Selection) => void
  onHighlight: (key: string | null) => void
  onRetry: () => void
}

export default function DetailPanel({
  companies,
  transactions,
  statuses,
  analysis,
  selection,
  highlightedKey,
  onSelect,
  onHighlight,
  onRetry,
}: Props) {
  const names = useMemo(() => new Map(companies.map((c) => [c.id, c.name])), [companies])
  const nameOf: NameOf = (id) => names.get(id) ?? 'a company that is not loaded'

  const company = selection?.kind === 'node' ? companies.find((c) => c.id === selection.id) : undefined
  const transaction =
    selection?.kind === 'edge' ? transactions.find((t) => t.id === selection.id) : undefined

  return (
    <aside
      aria-label="Details"
      className="max-h-[70vh] overflow-y-auto border border-line bg-surface p-5"
    >
      {selection === null && (
        <p>Select a company or a transaction on the graph to see its details.</p>
      )}
      {company && (
        <CompanyDetails
          company={company}
          transactions={transactions}
          status={statuses.get(company.id) ?? 'unavailable'}
          nameOf={nameOf}
          onSelect={onSelect}
        />
      )}
      {transaction && (
        <TransactionDetails
          transaction={transaction}
          transactions={transactions}
          nameOf={nameOf}
          onSelect={onSelect}
        />
      )}

      <h2 className="mt-8 text-xl font-semibold">Trading loops</h2>
      <p className="mt-1 text-base text-ink/70">
        Rule-based indicators for investigation. They are not proof of wrongdoing.
      </p>
      <FindingsSection
        analysis={analysis}
        highlightedKey={highlightedKey}
        onHighlight={onHighlight}
        onRetry={onRetry}
      />
    </aside>
  )
}
