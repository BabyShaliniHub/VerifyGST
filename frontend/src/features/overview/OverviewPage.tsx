import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { Check, CircleHelp, Clock, X, type LucideIcon } from 'lucide-react'
import {
  REFERENCE_DATE,
  cases,
  invoices,
  patterns,
  type DemoCase,
  type VerificationStatus,
} from './demoData'

const periodOptions = [
  { value: '30', label: 'Last 30 days' },
  { value: '90', label: 'Last 90 days' },
  { value: 'all', label: 'All demonstration data' },
]

const statusMeta: Record<
  VerificationStatus,
  { label: string; icon: LucideIcon; tone: string }
> = {
  verified: { label: 'Verified', icon: Check, tone: 'text-forest' },
  failed: { label: 'Failed', icon: X, tone: 'text-terracotta' },
  unknown: { label: 'Unknown', icon: CircleHelp, tone: 'text-ink/70' },
  pending: { label: 'Pending verification', icon: Clock, tone: 'text-gold' },
}

const statusOrder: VerificationStatus[] = ['verified', 'failed', 'unknown', 'pending']

function cutoffFor(value: string): string {
  if (value === 'all') return '0000-00-00'
  const ms = Date.parse(REFERENCE_DATE) - Number(value) * 86_400_000
  return new Date(ms).toISOString().slice(0, 10)
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString('en-IN', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    timeZone: 'UTC',
  })
}

function byUpdatedDesc(a: DemoCase, b: DemoCase): number {
  return b.updated.localeCompare(a.updated)
}

type FigureProps = {
  to: string
  label: string
  value: number
  icon?: LucideIcon
  tone?: string
}

function Figure({ to, label, value, icon: Icon, tone = '' }: FigureProps) {
  return (
    <Link to={to} className="block bg-surface px-6 py-4 hover:bg-canvas">
      <span className="flex items-center gap-2 text-base">
        {Icon && <Icon size={18} className={tone} aria-hidden="true" />}
        {label}
      </span>
      <span className={`mt-1 block text-3xl font-semibold tabular-nums ${tone}`}>
        {value}
      </span>
    </Link>
  )
}

export default function OverviewPage() {
  const [period, setPeriod] = useState('30')
  const cutoff = cutoffFor(period)

  const data = useMemo(() => {
    const periodInvoices = invoices.filter((i) => i.date >= cutoff)
    const counts: Record<VerificationStatus, number> = {
      verified: 0,
      failed: 0,
      unknown: 0,
      pending: 0,
    }
    periodInvoices.forEach((i) => {
      counts[i.status] += 1
    })

    const periodCases = cases.filter((c) => c.updated >= cutoff)
    const openCases = periodCases.filter((c) => c.status !== 'Closed')
    const priorityCases = openCases
      .filter((c) => c.priority === 'High priority' || c.priority === 'Elevated priority')
      .sort(byUpdatedDesc)
    const recent = [...periodCases].sort(byUpdatedDesc).slice(0, 5)

    return {
      total: periodInvoices.length,
      counts,
      reviewCount: openCases.length,
      gapCount: openCases.filter((c) => c.evidenceGap).length,
      patternCount: patterns.filter(
        (p) => p.date >= cutoff && p.level !== 'Insufficient data',
      ).length,
      priorityCases,
      recent,
    }
  }, [cutoff])

  return (
    <section>
      <h1 className="text-2xl font-semibold">Overview</h1>
      <p className="mt-2 max-w-2xl">
        Operational summary of invoices, verification results and investigations.
      </p>

      <p className="mt-4 max-w-3xl border-l-4 border-gold bg-surface px-4 py-3">
        Demonstration data. Every figure on this page comes from synthetic sample records
        inside the frontend. It is not connected to a backend or to real GST data.
      </p>

      <div className="mt-6 flex flex-wrap items-center gap-3">
        <label htmlFor="period" className="font-medium">
          Period
        </label>
        <select
          id="period"
          value={period}
          onChange={(e) => setPeriod(e.target.value)}
          className="rounded-md border border-line bg-surface px-3 py-2"
        >
          {periodOptions.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>
        <span className="text-base text-ink/70">
          Applies to invoice date, case last update and pattern detection date.
        </span>
      </div>

      <h2 className="mt-8 text-xl font-semibold">Invoice verification</h2>
      <p className="mt-1 text-base text-ink/70">{data.total} invoices in this period</p>
      <div className="mt-3 grid grid-cols-2 gap-px border border-line bg-line md:grid-cols-4">
        {statusOrder.map((s) => (
          <Figure
            key={s}
            to={`/verify?status=${s}`}
            label={statusMeta[s].label}
            value={data.counts[s]}
            icon={statusMeta[s].icon}
            tone={statusMeta[s].tone}
          />
        ))}
      </div>

      <h2 className="mt-8 text-xl font-semibold">Needs attention</h2>
      <div className="mt-3 grid grid-cols-1 gap-px border border-line bg-line sm:grid-cols-3">
        <Figure
          to="/investigations?status=open"
          label="Investigations requiring review"
          value={data.reviewCount}
        />
        <Figure
          to="/network?patterns=detected"
          label="Network patterns detected"
          value={data.patternCount}
        />
        <Figure
          to="/evidence?gaps=true"
          label="Cases with evidence gaps"
          value={data.gapCount}
        />
      </div>

      <h2 className="mt-8 text-xl font-semibold">Higher-priority open cases</h2>
      {data.priorityCases.length === 0 ? (
        <p className="mt-3">No higher-priority open cases in this period.</p>
      ) : (
        <ul className="mt-3 divide-y divide-line border border-line bg-surface">
          {data.priorityCases.map((c) => (
            <li key={c.id}>
              <Link
                to={`/investigations?case=${c.id}`}
                className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1 px-4 py-3 hover:bg-canvas"
              >
                <span>
                  <span className="font-semibold">{c.id}</span> {c.title}
                </span>
                <span className="text-base text-ink/70">
                  {c.priority}
                  {c.evidenceGap ? ' - evidence gap' : ''} - updated {formatDate(c.updated)}
                </span>
              </Link>
            </li>
          ))}
        </ul>
      )}

      <h2 className="mt-8 text-xl font-semibold">Recent investigation activity</h2>
      {data.recent.length === 0 ? (
        <p className="mt-3">No investigation activity in this period.</p>
      ) : (
        <ul className="mt-3 divide-y divide-line border border-line bg-surface">
          {data.recent.map((c) => (
            <li key={c.id}>
              <Link
                to={`/investigations?case=${c.id}`}
                className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1 px-4 py-3 hover:bg-canvas"
              >
                <span>
                  <span className="font-semibold">{c.id}</span> {c.lastAction}
                </span>
                <span className="text-base text-ink/70">{formatDate(c.updated)}</span>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}
