import { useEffect, useRef } from 'react'
import cytoscape from 'cytoscape'
import type { ApiCompany, ApiFinding, ApiTransaction } from './explorerApi'
import { findingKey, type NodeStatus } from './explorerModel'

export type Selection = { kind: 'node' | 'edge'; id: string } | null

type Props = {
  companies: ApiCompany[]
  transactions: ApiTransaction[]
  statuses: Map<string, NodeStatus>
  findings: ApiFinding[]
  layout: cytoscape.LayoutOptions
  selection: Selection
  highlightedKey: string | null
  onSelect: (selection: Selection) => void
  onReady: (cy: cytoscape.Core | null) => void
}

export default function NetworkGraph({
  companies,
  transactions,
  statuses,
  findings,
  layout,
  selection,
  highlightedKey,
  onSelect,
  onReady,
}: Props) {
  const containerRef = useRef<HTMLDivElement>(null)
  const cyRef = useRef<cytoscape.Core | null>(null)
  const onSelectRef = useRef(onSelect)

  useEffect(() => {
    onSelectRef.current = onSelect
  }, [onSelect])

  useEffect(() => {
    if (!containerRef.current) return

    // When the graph limit cut companies off, some transactions point at companies that are not
    // loaded. They are skipped here, because a graph edge needs both of its ends.
    const known = new Set(companies.map((c) => c.id))

    const cy = cytoscape({
      container: containerRef.current,
      elements: [
        ...companies.map((c) => ({
          data: { id: c.id, name: c.name, status: statuses.get(c.id) ?? 'unavailable' },
        })),
        ...transactions
          .filter((t) => known.has(t.seller_id) && known.has(t.buyer_id))
          .map((t) => ({
            data: {
              id: t.id,
              source: t.seller_id,
              target: t.buyer_id,
              evidence: t.evidence_level,
              label: t.invoice_reference ?? '',
            },
          })),
      ],
      layout,
      minZoom: 0.3,
      maxZoom: 2.5,
      style: [
        {
          selector: 'node',
          style: {
            'background-color': '#FFFFFF',
            'border-width': 3,
            'border-color': '#356859',
            shape: 'ellipse',
            width: 54,
            height: 54,
            label: 'data(name)',
            color: '#393B35',
            'font-size': 14,
            'text-valign': 'bottom',
            'text-margin-y': 8,
            'text-wrap': 'wrap',
            'text-max-width': '110px',
          },
        },
        {
          selector: 'node[status = "loop"]',
          style: { shape: 'hexagon', 'border-color': '#B58A45' },
        },
        {
          selector: 'node[status = "high"]',
          style: { shape: 'diamond', 'border-color': '#A84F43', width: 62, height: 62 },
        },
        {
          selector: 'node[status = "unavailable"]',
          style: {
            shape: 'round-rectangle',
            'border-color': '#8A8C84',
            'border-style': 'dashed',
          },
        },
        {
          selector: 'edge',
          style: {
            width: 2,
            'line-color': '#9A9C94',
            'target-arrow-color': '#9A9C94',
            'target-arrow-shape': 'triangle',
            'curve-style': 'bezier',
            label: 'data(label)',
            color: '#393B35',
            'font-size': 12,
            'text-rotation': 'autorotate',
            'text-background-color': '#FFFFFF',
            'text-background-opacity': 1,
            'text-background-padding': '2px',
          },
        },
        { selector: 'edge[evidence = "partial"]', style: { 'line-style': 'dashed' } },
        { selector: 'edge[evidence = "missing"]', style: { 'line-style': 'dotted', width: 3 } },
        {
          selector: 'node:selected',
          style: {
            'border-width': 6,
            'overlay-color': '#393B35',
            'overlay-opacity': 0.1,
            'overlay-padding': 8,
          },
        },
        {
          selector: 'edge:selected',
          style: { width: 5, 'overlay-color': '#393B35', 'overlay-opacity': 0.1 },
        },
        { selector: '.dim', style: { opacity: 0.2 } },
        {
          selector: 'edge.hl-high',
          style: { 'line-color': '#A84F43', 'target-arrow-color': '#A84F43', width: 5 },
        },
        {
          selector: 'edge.hl-susp',
          style: { 'line-color': '#B58A45', 'target-arrow-color': '#B58A45', width: 5 },
        },
      ],
    })

    cyRef.current = cy
    onReady(cy)

    const observer = new ResizeObserver(() => {
      cy.resize()
      cy.fit(undefined, 60)
    })
    observer.observe(containerRef.current)

    cy.on('tap', 'node', (evt) => {
      onSelectRef.current({ kind: 'node', id: evt.target.id() })
    })
    cy.on('tap', 'edge', (evt) => {
      onSelectRef.current({ kind: 'edge', id: evt.target.id() })
    })
    cy.on('tap', (evt) => {
      if (evt.target === cy) onSelectRef.current(null)
    })

    return () => {
      observer.disconnect()
      onReady(null)
      cy.destroy()
      cyRef.current = null
    }
  }, [companies, transactions, statuses, layout, onReady])

  useEffect(() => {
    const cy = cyRef.current
    if (!cy) return
    cy.elements().removeClass('dim hl-high hl-susp')
    if (!highlightedKey) return
    const finding = findings.find((f) => findingKey(f) === highlightedKey)
    if (!finding) return
    const cls = finding.priority === 'high' ? 'hl-high' : 'hl-susp'
    const members = cy
      .elements()
      .filter(
        (el) =>
          finding.transaction_ids.includes(el.id()) ||
          finding.companies.some((company) => company.id === el.id()),
      )
    cy.elements().not(members).addClass('dim')
    members.addClass(cls)
  }, [companies, transactions, statuses, layout, findings, highlightedKey])

  useEffect(() => {
    const cy = cyRef.current
    if (!cy) return
    cy.elements().unselect()
    if (selection) cy.getElementById(selection.id).select()
  }, [companies, transactions, statuses, layout, selection])

  return <div ref={containerRef} className="h-full w-full" />
}
