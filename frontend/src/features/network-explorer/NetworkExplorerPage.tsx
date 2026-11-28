import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import type cytoscape from 'cytoscape'
import { Maximize, RotateCcw, ZoomIn, ZoomOut } from 'lucide-react'
import DetailPanel from './DetailPanel'
import {
  loadExplorerData,
  type Analysis,
  type ApiFinding,
  type ExplorerResult,
  type GraphResponse,
} from './explorerApi'
import { buildLayout, companyStatuses } from './explorerModel'
import Legend from './Legend'
import NetworkGraph, { type Selection } from './NetworkGraph'

const buttonClass =
  'inline-flex items-center gap-2 rounded-md border border-line bg-surface px-3 py-2 hover:bg-canvas'

const NO_FINDINGS: ApiFinding[] = []

type PageState = { status: 'loading' } | ExplorerResult

function Explorer({
  graph,
  analysis,
  onRetry,
}: {
  graph: GraphResponse
  analysis: Analysis
  onRetry: () => void
}) {
  const cyRef = useRef<cytoscape.Core | null>(null)
  const [selection, setSelection] = useState<Selection>(null)
  const [highlightedKey, setHighlightedKey] = useState<string | null>(null)

  const statuses = useMemo(() => companyStatuses(graph.companies, analysis), [graph, analysis])
  const layout = useMemo(
    () => buildLayout(graph.companies, graph.transactions),
    [graph.companies, graph.transactions],
  )
  const findings = analysis.status === 'ready' ? analysis.findings : NO_FINDINGS

  const handleReady = useCallback((cy: cytoscape.Core | null) => {
    cyRef.current = cy
  }, [])

  const fit = () => {
    cyRef.current?.fit(undefined, 60)
  }

  const zoomBy = (factor: number) => {
    const cy = cyRef.current
    if (!cy) return
    cy.zoom({
      level: cy.zoom() * factor,
      renderedPosition: { x: cy.width() / 2, y: cy.height() / 2 },
    })
  }

  const resetLayout = () => {
    cyRef.current?.layout(layout).run()
  }

  return (
    <>
      {graph.contains_synthetic_data && (
        <p className="mt-4 max-w-3xl border-l-4 border-gold bg-surface px-4 py-3">
          Synthetic demonstration data. The companies, invoices and transactions shown here are
          invented and loaded from the VerifiGST backend. They describe no real business and no
          real GST data.
        </p>
      )}

      {(graph.truncated.companies || graph.truncated.transactions) && (
        <p className="mt-4 max-w-3xl border-l-4 border-gold bg-surface px-4 py-3">
          More records exist than this view loads, so the graph below is incomplete.
        </p>
      )}

      {analysis.status === 'unavailable' && (
        <div role="alert" className="mt-4 max-w-3xl border-l-4 border-gold bg-surface px-4 py-3">
          <p>
            Loop analysis is not available right now. {analysis.message} The graph below shows
            companies and transactions only. Companies with a dashed grey outline have not been
            checked for trading loops.
          </p>
          <button type="button" onClick={onRetry} className={`${buttonClass} mt-2`}>
            Try again
          </button>
        </div>
      )}

      <div className="mt-4 flex flex-wrap items-center gap-2">
        <button type="button" onClick={fit} className={buttonClass}>
          <Maximize size={18} aria-hidden="true" />
          Fit to view
        </button>
        <button type="button" onClick={resetLayout} className={buttonClass}>
          <RotateCcw size={18} aria-hidden="true" />
          Reset layout
        </button>
        <button type="button" onClick={() => zoomBy(1.25)} className={buttonClass}>
          <ZoomIn size={18} aria-hidden="true" />
          Zoom in
        </button>
        <button type="button" onClick={() => zoomBy(0.8)} className={buttonClass}>
          <ZoomOut size={18} aria-hidden="true" />
          Zoom out
        </button>
        <span className="text-base text-ink/70">
          {graph.companies.length} companies, {graph.transactions.length} transactions
        </span>
      </div>

      <div className="mt-4 grid gap-4 lg:grid-cols-[minmax(0,1fr)_24rem]">
        <div>
          <div className="h-[70vh] min-h-[480px] border border-line bg-surface">
            <NetworkGraph
              companies={graph.companies}
              transactions={graph.transactions}
              statuses={statuses}
              findings={findings}
              layout={layout}
              selection={selection}
              highlightedKey={highlightedKey}
              onSelect={setSelection}
              onReady={handleReady}
            />
          </div>
          <Legend />
        </div>
        <DetailPanel
          companies={graph.companies}
          transactions={graph.transactions}
          statuses={statuses}
          analysis={analysis}
          selection={selection}
          highlightedKey={highlightedKey}
          onSelect={setSelection}
          onHighlight={setHighlightedKey}
          onRetry={onRetry}
        />
      </div>
    </>
  )
}

export default function NetworkExplorerPage() {
  const [state, setState] = useState<PageState>({ status: 'loading' })
  const [attempt, setAttempt] = useState(0)

  useEffect(() => {
    const controller = new AbortController()
    void loadExplorerData(controller.signal).then((result) => {
      if (!controller.signal.aborted) setState(result)
    })
    return () => controller.abort()
  }, [attempt])

  const retry = () => {
    setState({ status: 'loading' })
    setAttempt((n) => n + 1)
  }

  return (
    <section>
      <h1 className="text-2xl font-semibold">Network Explorer</h1>
      <p className="mt-2 max-w-3xl">
        Directed graph of companies and the transactions between them. Network patterns are
        indicators for investigation, not proof of wrongdoing.
      </p>

      {state.status === 'loading' && (
        <p role="status" className="mt-4">
          Loading the network...
        </p>
      )}

      {state.status === 'error' && (
        <div role="alert" className="mt-4 max-w-3xl border-l-4 border-gold bg-surface px-4 py-3">
          <p>The network could not be loaded. {state.message}</p>
          <button type="button" onClick={retry} className={`${buttonClass} mt-2`}>
            Try again
          </button>
        </div>
      )}

      {state.status === 'ready' && (
        <Explorer graph={state.graph} analysis={state.analysis} onRetry={retry} />
      )}
    </section>
  )
}
