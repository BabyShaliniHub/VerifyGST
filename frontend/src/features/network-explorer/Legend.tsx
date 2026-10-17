function Item({ children, label }: { children: React.ReactNode; label: string }) {
  return (
    <li className="flex items-center gap-2">
      {children}
      <span>{label}</span>
    </li>
  )
}

function NodeShape({ children }: { children: React.ReactNode }) {
  return (
    <svg width="28" height="28" viewBox="0 0 28 28" aria-hidden="true">
      {children}
    </svg>
  )
}

function LineSample({ dash }: { dash?: string }) {
  return (
    <svg width="40" height="16" viewBox="0 0 40 16" aria-hidden="true">
      <line
        x1="2"
        y1="8"
        x2="38"
        y2="8"
        stroke="#9A9C94"
        strokeWidth="3"
        strokeDasharray={dash}
        strokeLinecap={dash === '1 5' ? 'round' : 'butt'}
      />
    </svg>
  )
}

export default function Legend() {
  return (
    <div className="mt-4 grid gap-6 border border-line bg-surface p-4 sm:grid-cols-2">
      <div>
        <h2 className="text-lg font-semibold">Companies (network analysis)</h2>
        <ul className="mt-2 flex flex-col gap-1">
          <Item label="No configured rule triggered">
            <NodeShape>
              <circle cx="14" cy="14" r="9" fill="#FFFFFF" stroke="#356859" strokeWidth="3" />
            </NodeShape>
          </Item>
          <Item label="Suspicious pattern detected">
            <NodeShape>
              <polygon
                points="14,3 24,8.5 24,19.5 14,25 4,19.5 4,8.5"
                fill="#FFFFFF"
                stroke="#B58A45"
                strokeWidth="3"
              />
            </NodeShape>
          </Item>
          <Item label="High-priority pattern detected">
            <NodeShape>
              <polygon
                points="14,3 25,14 14,25 3,14"
                fill="#FFFFFF"
                stroke="#A84F43"
                strokeWidth="3"
              />
            </NodeShape>
          </Item>
          <Item label="Insufficient data">
            <NodeShape>
              <rect
                x="4"
                y="4"
                width="20"
                height="20"
                rx="5"
                fill="#FFFFFF"
                stroke="#8A8C84"
                strokeWidth="3"
                strokeDasharray="4 3"
              />
            </NodeShape>
          </Item>
        </ul>
      </div>
      <div>
        <h2 className="text-lg font-semibold">Transactions (evidence)</h2>
        <ul className="mt-2 flex flex-col gap-1">
          <Item label="Evidence complete">
            <LineSample />
          </Item>
          <Item label="Evidence partial">
            <LineSample dash="7 5" />
          </Item>
          <Item label="Evidence missing">
            <LineSample dash="1 5" />
          </Item>
        </ul>
        <p className="mt-2 text-base text-ink/70">
          Arrows point from supplier to buyer. Labels show the invoice reference.
        </p>
      </div>
    </div>
  )
}
