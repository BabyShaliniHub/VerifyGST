import { useMemo, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { Download } from 'lucide-react'
import { downloadText, toCsv } from '../../lib/download'
import { formatDate } from '../../lib/format'
import { cases } from '../overview/demoData'
import {
  demoEvidence,
  evidenceKinds,
  type EvidenceKind,
  type EvidenceRecord,
} from './demoEvidence'

const fieldClass = 'rounded-md border border-line bg-surface px-3 py-2'

const gapCaseIds = new Set(cases.filter((c) => c.evidenceGap).map((c) => c.id))

const sectionHeadings: Record<EvidenceKind, string> = {
  Fact: 'FACTS',
  'Rule-based finding': 'RULE-BASED FINDINGS',
  'Uncertain information': 'UNCERTAIN INFORMATION',
  'Investigator note': 'INVESTIGATOR NOTES',
}

function formatDateTime(iso: string): string {
  const text = new Date(iso).toLocaleString('en-IN', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
    timeZone: 'UTC',
  })
  return `${text} UTC`
}

function buildReport(caseId: string): string {
  const c = cases.find((x) => x.id === caseId)
  const records = demoEvidence.filter((e) => e.caseId === caseId)
  const lines: string[] = [
    'VerifiGST case report - demonstration data',
    '',
    `Case: ${caseId}${c ? ` - ${c.title}` : ''}`,
  ]
  if (c) {
    lines.push(
      `Priority: ${c.priority}`,
      `Status (demonstration dataset): ${c.status}`,
      `Last updated: ${formatDate(c.updated)}`,
    )
  }
  lines.push(
    '',
    'This report keeps facts, rule-based findings, uncertain information and investigator notes separate. Rule-based findings are indicators for investigation, not proof of wrongdoing. Missing evidence is not treated as a positive result.',
  )
  evidenceKinds.forEach((kind) => {
    lines.push('', sectionHeadings[kind])
    const items = records.filter((e) => e.kind === kind)
    if (items.length === 0) lines.push('None recorded.')
    items.forEach((e) => {
      lines.push(
        `- [${e.id}] ${e.check}: ${e.result}`,
        `  ${e.explanation}`,
        `  Limitations: ${e.limitations}`,
        `  Source: ${e.source} (${e.sourceType}); recorded ${e.timestamp}; source available: ${
          e.sourceAvailable ? 'yes' : 'no'
        }`,
      )
    })
  })
  return lines.join('\r\n') + '\r\n'
}

function exportCsv(rows: EvidenceRecord[]) {
  const header = [
    'evidence_id',
    'case_id',
    'kind',
    'subject',
    'check',
    'result',
    'explanation',
    'limitations',
    'source',
    'source_type',
    'source_available',
    'timestamp_utc',
    'data_label',
  ]
  const body = rows.map((e) => [
    e.id,
    e.caseId,
    e.kind,
    e.subject,
    e.check,
    e.result,
    e.explanation,
    e.limitations,
    e.source,
    e.sourceType,
    e.sourceAvailable ? 'yes' : 'no',
    e.timestamp,
    'Synthetic demonstration data',
  ])
  downloadText(
    'verifigst-evidence-demo.csv',
    '\uFEFF' + toCsv([header, ...body]),
    'text/csv;charset=utf-8',
  )
}

export default function EvidencePage() {
  const [params] = useSearchParams()
  const [search, setSearch] = useState('')
  const [kindFilter, setKindFilter] = useState<'all' | EvidenceKind>('all')
  const [caseFilter, setCaseFilter] = useState('all')
  const [gapsOnly, setGapsOnly] = useState(params.get('gaps') === 'true')
  const [selectedId, setSelectedId] = useState<string | null>(null)

  const visible = useMemo(() => {
    const q = search.trim().toLowerCase()
    return demoEvidence
      .filter((e) => {
        if (kindFilter !== 'all' && e.kind !== kindFilter) return false
        if (caseFilter !== 'all' && e.caseId !== caseFilter) return false
        if (gapsOnly && !gapCaseIds.has(e.caseId)) return false
        if (q) {
          const text = [e.id, e.caseId, e.subject, e.check, e.result, e.explanation, e.source]
            .join(' ')
            .toLowerCase()
          if (!text.includes(q)) return false
        }
        return true
      })
      .sort((a, b) => b.timestamp.localeCompare(a.timestamp))
  }, [search, kindFilter, caseFilter, gapsOnly])

  const clearFilters = () => {
    setSearch('')
    setKindFilter('all')
    setCaseFilter('all')
    setGapsOnly(false)
  }

  const selected = demoEvidence.find((e) => e.id === selectedId)
  const selectedCase = selected ? cases.find((c) => c.id === selected.caseId) : undefined

  return (
    <section>
      <h1 className="text-2xl font-semibold">Evidence and Reports</h1>
      <p className="mt-2 max-w-3xl">
        A traceable record of what each check found. Facts are retrieved from a source.
        Rule-based findings come from configured rules and are indicators, not proof. Uncertain
        information has limits or a missing source. Investigator notes are human comments.
      </p>

      <p className="mt-4 max-w-3xl border-l-4 border-gold bg-surface px-4 py-3">
        Demonstration data. These evidence records are synthetic and are not connected to a
        backend, a document store or any real source. Exports contain only this synthetic data.
      </p>

      <div className="mt-6 flex flex-wrap items-end gap-4">
        <div className="flex flex-col gap-1">
          <label htmlFor="ev-search" className="font-medium">
            Search
          </label>
          <input
            id="ev-search"
            type="search"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Record, case, invoice or check"
            className={`${fieldClass} w-64`}
          />
        </div>
        <div className="flex flex-col gap-1">
          <label htmlFor="ev-kind" className="font-medium">
            Kind
          </label>
          <select
            id="ev-kind"
            value={kindFilter}
            onChange={(e) => setKindFilter(e.target.value as 'all' | EvidenceKind)}
            className={fieldClass}
          >
            <option value="all">All kinds</option>
            {evidenceKinds.map((k) => (
              <option key={k} value={k}>
                {k}
              </option>
            ))}
          </select>
        </div>
        <div className="flex flex-col gap-1">
          <label htmlFor="ev-case" className="font-medium">
            Case
          </label>
          <select
            id="ev-case"
            value={caseFilter}
            onChange={(e) => setCaseFilter(e.target.value)}
            className={fieldClass}
          >
            <option value="all">All cases</option>
            {cases.map((c) => (
              <option key={c.id} value={c.id}>
                {c.id}
              </option>
            ))}
          </select>
        </div>
        <label className="flex items-center gap-2 pb-2">
          <input
            type="checkbox"
            checked={gapsOnly}
            onChange={(e) => setGapsOnly(e.target.checked)}
            className="h-5 w-5"
          />
          Only cases with evidence gaps
        </label>
        <button type="button" onClick={clearFilters} className={`${fieldClass} hover:bg-canvas`}>
          Clear filters
        </button>
        <button
          type="button"
          onClick={() => exportCsv(visible)}
          disabled={visible.length === 0}
          className={`${fieldClass} inline-flex items-center gap-2 hover:bg-canvas disabled:opacity-50`}
        >
          <Download size={18} aria-hidden="true" />
          Export CSV
        </button>
        <span className="pb-2 text-base text-ink/70">
          {visible.length} of {demoEvidence.length} records
        </span>
      </div>

      <div className="mt-4 grid gap-4 lg:grid-cols-[minmax(0,1fr)_28rem]">
        <div>
          {visible.length === 0 ? (
            <p className="border border-line bg-surface px-4 py-3">
              No evidence records match these filters.
            </p>
          ) : (
            <ul className="divide-y divide-line border border-line bg-surface">
              {visible.map((e) => (
                <li key={e.id}>
                  <button
                    type="button"
                    onClick={() => setSelectedId(e.id)}
                    aria-current={e.id === selectedId ? 'true' : undefined}
                    className={`w-full px-4 py-3 text-left hover:bg-canvas ${
                      e.id === selectedId ? 'bg-sunken' : ''
                    }`}
                  >
                    <span className="font-semibold">{e.id}</span> {e.check}: {e.result}
                    <span className="block text-base text-ink/70">
                      {e.kind} - {e.caseId} - {formatDateTime(e.timestamp)}
                      {e.sourceAvailable ? '' : ' - source not available'}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>

        <aside aria-label="Evidence details" className="border border-line bg-surface p-5">
          {!selected && <p>Select an evidence record to see its details.</p>}
          {selected && (
            <div>
              <h2 className="text-xl font-semibold">{selected.id}</h2>
              <p className="text-base text-ink/70">{selected.kind}</p>
              <dl className="mt-4 flex flex-col gap-3">
                <div>
                  <dt className="font-semibold">Case</dt>
                  <dd>
                    <Link
                      to={`/investigations?case=${selected.caseId}`}
                      className="text-forest underline underline-offset-2"
                    >
                      {selected.caseId}
                    </Link>
                    {selectedCase ? ` - ${selectedCase.title}` : ''}
                  </dd>
                </div>
                <div>
                  <dt className="font-semibold">Subject</dt>
                  <dd>{selected.subject}</dd>
                </div>
                <div>
                  <dt className="font-semibold">Check</dt>
                  <dd>{selected.check}</dd>
                </div>
                <div>
                  <dt className="font-semibold">Result</dt>
                  <dd>{selected.result}</dd>
                </div>
                <div>
                  <dt className="font-semibold">Explanation</dt>
                  <dd>{selected.explanation}</dd>
                </div>
                <div>
                  <dt className="font-semibold">Limitations</dt>
                  <dd>{selected.limitations}</dd>
                </div>
                <div>
                  <dt className="font-semibold">Source</dt>
                  <dd>
                    {selected.source} ({selected.sourceType})
                  </dd>
                </div>
                <div>
                  <dt className="font-semibold">Source available</dt>
                  <dd>
                    {selected.sourceAvailable
                      ? 'Yes'
                      : 'No. The source was not available in this demonstration.'}
                  </dd>
                </div>
                <div>
                  <dt className="font-semibold">Recorded</dt>
                  <dd>{formatDateTime(selected.timestamp)}</dd>
                </div>
              </dl>
              <button
                type="button"
                onClick={() =>
                  downloadText(
                    `${selected.caseId}-report.txt`,
                    buildReport(selected.caseId),
                    'text/plain;charset=utf-8',
                  )
                }
                className={`${fieldClass} mt-5 inline-flex items-center gap-2 hover:bg-canvas`}
              >
                <Download size={18} aria-hidden="true" />
                Download report for {selected.caseId}
              </button>
            </div>
          )}
        </aside>
      </div>
    </section>
  )
}
