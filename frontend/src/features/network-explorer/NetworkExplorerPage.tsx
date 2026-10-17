import { useCallback, useRef, useState } from 'react'
import type cytoscape from 'cytoscape'
import { Maximize, RotateCcw, ZoomIn, ZoomOut } from 'lucide-react'
import DetailPanel from './DetailPanel'
import { companies, transactions } from './demoGraph'
import Legend from './Legend'
import NetworkGraph, { presetLayout, type Selection } from './NetworkGraph'

const buttonClass =
  'inline-flex items-center gap-2 rounded-md border border-line bg-surface px-3 py-2 hover:bg-canvas'

export default function NetworkExplorerPage() {
  const cyRef = useRef<cytoscape.Core | null>(null)
  const [selection, setSelection] = useState<Selection>(null)
  const [highlightedId, setHighlightedId] = useState<string | null>(null)

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
    cyRef.current?.layout(presetLayout).run()
  }

  return (
    <section>
      <h1 className="text-2xl font-semibold">Network Explorer</h1>
      <p className="mt-2 max-w-3xl">
        Directed graph of companies and the transactions between them. Network patterns are
        indicators for investigation, not proof of wrongdoing.
      </p>

      <p className="mt-4 max-w-3xl border-l-4 border-gold bg-surface px-4 py-3">
        Demonstration data. The companies, invoices and transactions shown here are synthetic.
        They describe no real business, and the graph is not connected to a backend or to real
        GST data.
      </p>

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
          {companies.length} companies, {transactions.length} transactions
        </span>
      </div>

      <div className="mt-4 grid gap-4 lg:grid-cols-[minmax(0,1fr)_24rem]">
        <div>
          <div className="h-[70vh] min-h-[480px] border border-line bg-surface">
            <NetworkGraph
              selection={selection}
              highlightedFindingId={highlightedId}
              onSelect={setSelection}
              onReady={handleReady}
            />
          </div>
          <Legend />
        </div>
        <DetailPanel
          selection={selection}
          highlightedId={highlightedId}
          onSelect={setSelection}
          onHighlight={setHighlightedId}
        />
      </div>
    </section>
  )
}
