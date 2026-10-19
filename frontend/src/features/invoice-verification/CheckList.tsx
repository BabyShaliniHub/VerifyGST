import { Check, CircleHelp, Flag, Minus, X, type LucideIcon } from 'lucide-react'
import type { CheckResult, CheckStatus } from './demoInvoices'

export const statusMeta: Record<CheckStatus, { label: string; icon: LucideIcon; tone: string }> = {
  passed: { label: 'Passed', icon: Check, tone: 'text-forest' },
  failed: { label: 'Failed', icon: X, tone: 'text-terracotta' },
  unknown: { label: 'Unknown', icon: CircleHelp, tone: 'text-ink/70' },
  not_checked: { label: 'Not checked', icon: Minus, tone: 'text-ink/70' },
  manual_review: { label: 'Manual review required', icon: Flag, tone: 'text-gold' },
}

export function StatusLabel({ status }: { status: CheckStatus }) {
  const { label, icon: Icon, tone } = statusMeta[status]
  return (
    <span className="inline-flex items-center gap-1.5 font-semibold">
      <Icon size={18} className={tone} aria-hidden="true" />
      {label}
    </span>
  )
}

export default function CheckList({ checks }: { checks: CheckResult[] }) {
  return (
    <ul className="divide-y divide-line border border-line bg-surface">
      {checks.map((c) => (
        <li key={c.id} className="px-4 py-3">
          <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
            <span className="font-semibold">{c.label}</span>
            <StatusLabel status={c.status} />
          </div>
          <p className="mt-1 text-base text-ink/70">{c.detail}</p>
        </li>
      ))}
    </ul>
  )
}
