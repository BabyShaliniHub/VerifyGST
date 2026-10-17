import type { ReactNode } from 'react'
import { formatDate, formatInr } from '../../lib/format'
import {
  companies,
  evidenceLabels,
  findings,
  statusLabels,
  transactions,
  type DemoFinding,
  type DemoTransaction,
} from './demoGraph'
import type { Selection } from './NetworkGraph'

const nameOf = (id: string) => companies.find((c) => c.id === id)?.name ?? id

function pathText(f: DemoFinding): string {
  const txs = f.transactionIds.flatMap((id) => {
    const t = transactions.find((x) => x.id === id)
    return t ? [t] : []
  })
  if (txs.length === 0) return ''
  return [txs[0].source, ...txs.map((t) => t.target)].map(nameOf).join(' -> ')
}

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
  onSelect,
}: {
  items: DemoTransaction[]
  direction: 'in' | 'out'
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
            <span className="font-semibold">{t.invoiceRef}</span> - {formatInr(t.amountInr)}
            <span className="block text-base text-ink/70">
              {direction === 'in' ? 'from ' : 'to '}
              {nameOf(direction === 'in' ? t.source : t.target)}
            </span>
          </button>
        </li>
      ))}
    </ul>
  )
}

function CompanyDetails({ id, onSelect }: { id: string; onSelect: (s: Selection) => void }) {
  const company = companies.find((c) => c.id === id)
  if (!company) return null
  const incoming = transactions.filter((t) => t.target === id)
  const outgoing = transactions.filter((t) => t.source === id)
  return (
    <div>
      <h2 className="text-xl font-semibold">{company.name}</h2>
      <p className="text-base text-ink/70">{company.demoRef} - demonstration company</p>
      <p className="mt-3">
        <span className="font-semibold">Network analysis:</span> {statusLabels[company.status]}
      </p>
      <h3 className="mt-4 font-semibold">Incoming transactions ({incoming.length})</h3>
      <TransactionList items={incoming} direction="in" onSelect={onSelect} />
      <h3 className="mt-4 font-semibold">Outgoing transactions ({outgoing.length})</h3>
      <TransactionList items={outgoing} direction="out" onSelect={onSelect} />
    </div>
  )
}

function TransactionDetails({ id, onSelect }: { id: string; onSelect: (s: Selection) => void }) {
  const t = transactions.find((x) => x.id === id)
  if (!t) return null
  const sameRef = transactions.filter((o) => o.id !== t.id && o.invoiceRef === t.invoiceRef)
  return (
    <div>
      <h2 className="text-xl font-semibold">Transaction {t.id}</h2>
      <dl className="mt-3 grid grid-cols-[8rem_1fr] gap-x-3 gap-y-2">
        <dt className="font-semibold">From</dt>
        <dd>
          <LinkButton onClick={() => onSelect({ kind: 'node', id: t.source })}>
            {nameOf(t.source)}
          </LinkButton>
        </dd>
        <dt className="font-semibold">To</dt>
        <dd>
          <LinkButton onClick={() => onSelect({ kind: 'node', id: t.target })}>
            {nameOf(t.target)}
          </LinkButton>
        </dd>
        <dt className="font-semibold">Invoice</dt>
        <dd>{t.invoiceRef}</dd>
        <dt className="font-semibold">Amount</dt>
        <dd>{formatInr(t.amountInr)}</dd>
        <dt className="font-semibold">Date</dt>
        <dd>{formatDate(t.date)}</dd>
        <dt className="font-semibold">Evidence</dt>
        <dd>{evidenceLabels[t.evidence]}</dd>
      </dl>
      {sameRef.length > 0 && (
        <p className="mt-3">
          The reference {t.invoiceRef} also appears on {sameRef.length} other transaction
          {sameRef.length > 1 ? 's' : ''} ({sameRef.map((o) => o.id).join(', ')}).
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
  finding: DemoFinding
  active: boolean
  onToggle: () => void
}) {
  return (
    <article className="border-t border-line pt-4">
      <h3 className="font-semibold">{finding.title}</h3>
      <p className="text-base text-ink/70">{finding.level}</p>
      <dl className="mt-2 flex flex-col gap-2">
        <div>
          <dt className="font-semibold">Rule</dt>
          <dd>{finding.rule}</dd>
        </div>
        <div>
          <dt className="font-semibold">Path</dt>
          <dd>{pathText(finding)}</dd>
        </div>
        <div>
          <dt className="font-semibold">Supporting data</dt>
          <dd>
            <ul className="list-disc pl-5">
              {finding.supportingData.map((s) => (
                <li key={s}>{s}</li>
              ))}
            </ul>
          </dd>
        </div>
        <div>
          <dt className="font-semibold">Limitations</dt>
          <dd>{finding.limitations}</dd>
        </div>
        <div>
          <dt className="font-semibold">Suggested next step</dt>
          <dd>{finding.nextStep}</dd>
        </div>
      </dl>
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

type Props = {
  selection: Selection
  highlightedId: string | null
  onSelect: (s: Selection) => void
  onHighlight: (id: string | null) => void
}

export default function DetailPanel({ selection, highlightedId, onSelect, onHighlight }: Props) {
  return (
    <aside
      aria-label="Details"
      className="max-h-[70vh] overflow-y-auto border border-line bg-surface p-5"
    >
      {selection === null && (
        <p>Select a company or a transaction on the graph to see its details.</p>
      )}
      {selection?.kind === 'node' && <CompanyDetails id={selection.id} onSelect={onSelect} />}
      {selection?.kind === 'edge' && <TransactionDetails id={selection.id} onSelect={onSelect} />}

      <h2 className="mt-8 text-xl font-semibold">Findings in this dataset</h2>
      <p className="mt-1 text-base text-ink/70">
        Rule-based indicators for investigation. They are not proof of wrongdoing.
      </p>
      <div className="mt-3 flex flex-col gap-4">
        {findings.map((f) => (
          <FindingCard
            key={f.id}
            finding={f}
            active={highlightedId === f.id}
            onToggle={() => onHighlight(highlightedId === f.id ? null : f.id)}
          />
        ))}
      </div>
    </aside>
  )
}
