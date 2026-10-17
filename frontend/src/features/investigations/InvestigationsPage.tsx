import { useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { formatDate } from '../../lib/format'
import { REFERENCE_DATE, cases, type CasePriority, type DemoCase } from '../overview/demoData'
import { caseDetails } from './demoCaseDetails'

type CaseStatus = DemoCase['status']
type StatusFilter = 'all' | 'active' | CaseStatus
type SortKey = 'updated' | 'priority' | 'reference'

const priorities: CasePriority[] = ['High priority', 'Elevated priority', 'Review', 'Informational']
const statuses: CaseStatus[] = ['Open', 'In review', 'Closed']

const priorityRank: Record<CasePriority, number> = {
  'High priority': 0,
  'Elevated priority': 1,
  Review: 2,
  Informational: 3,
}

const fieldClass = 'rounded-md border border-line bg-surface px-3 py-2'

function compareCases(sortKey: SortKey) {
  return (a: DemoCase, b: DemoCase): number => {
    if (sortKey === 'reference') return a.id.localeCompare(b.id)
    if (sortKey === 'priority') {
      return priorityRank[a.priority] - priorityRank[b.priority] || b.updated.localeCompare(a.updated)
    }
    return b.updated.localeCompare(a.updated)
  }
}

export default function InvestigationsPage() {
  const [params, setParams] = useSearchParams()
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState<StatusFilter>(
    params.get('status') === 'open' ? 'active' : 'all',
  )
  const [priorityFilter, setPriorityFilter] = useState<'all' | CasePriority>('all')
  const [sortKey, setSortKey] = useState<SortKey>('updated')
  const [overrides, setOverrides] = useState<Record<string, { status: CaseStatus; updated: string }>>({})

  const selectedId = params.get('case')

  const effective = useMemo(
    () => cases.map((c) => (overrides[c.id] ? { ...c, ...overrides[c.id] } : c)),
    [overrides],
  )

  const visible = useMemo(() => {
    const q = search.trim().toLowerCase()
    return effective
      .filter((c) => {
        if (statusFilter === 'active' && c.status === 'Closed') return false
        if (statusFilter !== 'all' && statusFilter !== 'active' && c.status !== statusFilter) {
          return false
        }
        if (priorityFilter !== 'all' && c.priority !== priorityFilter) return false
        if (q) {
          const d = caseDetails[c.id]
          const text = [c.id, c.title, ...(d ? [...d.companies, ...d.records] : [])]
            .join(' ')
            .toLowerCase()
          if (!text.includes(q)) return false
        }
        return true
      })
      .sort(compareCases(sortKey))
  }, [effective, search, statusFilter, priorityFilter, sortKey])

  const selectCase = (id: string) => {
    setParams((prev) => {
      const next = new URLSearchParams(prev)
      next.set('case', id)
      return next
    })
  }

  const updateStatus = (id: string, status: CaseStatus) => {
    setOverrides((prev) => ({ ...prev, [id]: { status, updated: REFERENCE_DATE } }))
  }

  const clearFilters = () => {
    setSearch('')
    setStatusFilter('all')
    setPriorityFilter('all')
  }

  const selected = effective.find((c) => c.id === selectedId)
  const detail = selectedId ? caseDetails[selectedId] : undefined

  return (
    <section>
      <h1 className="text-2xl font-semibold">Investigations</h1>
      <p className="mt-2 max-w-3xl">
        Cases, related records, evidence completeness and review status. Findings are indicators
        for investigation, not proof of wrongdoing.
      </p>

      <p className="mt-4 max-w-3xl border-l-4 border-gold bg-surface px-4 py-3">
        Demonstration data. These cases are synthetic. Status changes are kept only in this
        browser session and are lost when the page reloads.
      </p>

      <div className="mt-6 flex flex-wrap items-end gap-4">
        <div className="flex flex-col gap-1">
          <label htmlFor="case-search" className="font-medium">
            Search
          </label>
          <input
            id="case-search"
            type="search"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Case, company or invoice"
            className={`${fieldClass} w-64`}
          />
        </div>
        <div className="flex flex-col gap-1">
          <label htmlFor="case-status" className="font-medium">
            Status
          </label>
          <select
            id="case-status"
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value as StatusFilter)}
            className={fieldClass}
          >
            <option value="all">All statuses</option>
            <option value="active">Open or in review</option>
            {statuses.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </div>
        <div className="flex flex-col gap-1">
          <label htmlFor="case-priority" className="font-medium">
            Priority
          </label>
          <select
            id="case-priority"
            value={priorityFilter}
            onChange={(e) => setPriorityFilter(e.target.value as 'all' | CasePriority)}
            className={fieldClass}
          >
            <option value="all">All priorities</option>
            {priorities.map((p) => (
              <option key={p} value={p}>
                {p}
              </option>
            ))}
          </select>
        </div>
        <div className="flex flex-col gap-1">
          <label htmlFor="case-sort" className="font-medium">
            Sort by
          </label>
          <select
            id="case-sort"
            value={sortKey}
            onChange={(e) => setSortKey(e.target.value as SortKey)}
            className={fieldClass}
          >
            <option value="updated">Recently updated</option>
            <option value="priority">Priority</option>
            <option value="reference">Case reference</option>
          </select>
        </div>
        <button type="button" onClick={clearFilters} className={`${fieldClass} hover:bg-canvas`}>
          Clear filters
        </button>
        <span className="pb-2 text-base text-ink/70">
          {visible.length} of {cases.length} cases
        </span>
      </div>

      <div className="mt-4 grid gap-4 lg:grid-cols-[minmax(0,1fr)_28rem]">
        <div>
          {visible.length === 0 ? (
            <p className="border border-line bg-surface px-4 py-3">
              No cases match these filters.
            </p>
          ) : (
            <ul className="divide-y divide-line border border-line bg-surface">
              {visible.map((c) => (
                <li key={c.id}>
                  <button
                    type="button"
                    onClick={() => selectCase(c.id)}
                    aria-current={c.id === selectedId ? 'true' : undefined}
                    className={`w-full px-4 py-3 text-left hover:bg-canvas ${
                      c.id === selectedId ? 'bg-sunken' : ''
                    }`}
                  >
                    <span className="font-semibold">{c.id}</span> {c.title}
                    <span className="block text-base text-ink/70">
                      {c.priority} - {c.status}
                      {c.evidenceGap ? ' - evidence gap' : ''} - updated {formatDate(c.updated)}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>

        <aside aria-label="Case details" className="border border-line bg-surface p-5">
          {!selectedId && <p>Select a case to see its details.</p>}
          {selectedId && !selected && <p>Case {selectedId} was not found.</p>}
          {selected && (
            <div>
              <h2 className="text-xl font-semibold">{selected.id}</h2>
              <p className="mt-1">{selected.title}</p>

              <div className="mt-4 flex flex-col gap-1">
                <label htmlFor="case-status-update" className="font-semibold">
                  Review status
                </label>
                <select
                  id="case-status-update"
                  value={selected.status}
                  onChange={(e) => updateStatus(selected.id, e.target.value as CaseStatus)}
                  className={`${fieldClass} w-48`}
                >
                  {statuses.map((s) => (
                    <option key={s} value={s}>
                      {s}
                    </option>
                  ))}
                </select>
              </div>

              <dl className="mt-4 flex flex-col gap-3">
                <div>
                  <dt className="font-semibold">Priority</dt>
                  <dd>{selected.priority}</dd>
                </div>
                {detail && (
                  <div>
                    <dt className="font-semibold">Created</dt>
                    <dd>{formatDate(detail.created)}</dd>
                  </div>
                )}
                <div>
                  <dt className="font-semibold">Last updated</dt>
                  <dd>{formatDate(selected.updated)}</dd>
                </div>
                {detail && (
                  <>
                    <div>
                      <dt className="font-semibold">Related companies</dt>
                      <dd>
                        <ul className="list-disc pl-5">
                          {detail.companies.map((c) => (
                            <li key={c}>{c}</li>
                          ))}
                        </ul>
                      </dd>
                    </div>
                    <div>
                      <dt className="font-semibold">Related records</dt>
                      <dd>
                        <ul className="list-disc pl-5">
                          {detail.records.map((r) => (
                            <li key={r}>{r}</li>
                          ))}
                        </ul>
                      </dd>
                    </div>
                    <div>
                      <dt className="font-semibold">Evidence completeness</dt>
                      <dd>{detail.evidenceCompleteness}</dd>
                    </div>
                    <div>
                      <dt className="font-semibold">Reasons for the finding</dt>
                      <dd>
                        <ul className="list-disc pl-5">
                          {detail.reasons.map((r) => (
                            <li key={r}>{r}</li>
                          ))}
                        </ul>
                      </dd>
                    </div>
                    <div>
                      <dt className="font-semibold">Suggested next step</dt>
                      <dd>{detail.nextStep}</dd>
                    </div>
                  </>
                )}
              </dl>
            </div>
          )}
        </aside>
      </div>
    </section>
  )
}
