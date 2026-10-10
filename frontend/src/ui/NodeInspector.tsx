import { useMemo, useRef } from 'react'
import { useGameStore } from '../store/gameStore'
import { useSimStore } from '../store/simStore'
import type { NodeState } from '../types/sim'
import { PolicySelector } from './PolicySelector'
import { Sparkline } from './Sparkline'

const TYPE_LABELS: Record<string, string> = {
  Supplier: 'Supplier',
  Manufacturer: 'Manufacturer',
  DistributionCenter: 'DC',
  Retailer: 'Retailer',
}

const SPARKLINE_PERIODS = 10

const fmt = (n: number) => Math.round(n).toLocaleString()
const pct = (n: number | null) => (n === null ? '—' : `${(n * 100).toFixed(1)}%`)

export function NodeInspector() {
  const selectedId = useGameStore((s) => s.selectedNodeId)
  const selectNode = useGameStore((s) => s.selectNode)
  const nodes = useSimStore((s) => s.networkState.nodes)
  const history = useSimStore((s) => s.history)

  const live = selectedId ? nodes.find((n) => n.id === selectedId) : undefined
  // Keep showing the last node while the panel slides out.
  const lastShown = useRef<NodeState | undefined>(undefined)
  if (live) lastShown.current = live
  const node = live ?? lastShown.current
  const open = live !== undefined

  const trend = useMemo(() => {
    if (!node) return []
    return history
      .slice(-SPARKLINE_PERIODS)
      .map((h) => h.nodes.find((n) => n.id === node.id)?.on_hand)
      .filter((v): v is number => v !== undefined)
  }, [history, node?.id]) // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <aside className={`inspector${open ? ' open' : ''}`} aria-hidden={!open}>
      {node && (
        <>
          <div className="inspector-head">
            <div>
              <h2>{node.name}</h2>
              <span className="inspector-type">{TYPE_LABELS[node.type] ?? node.type}</span>
            </div>
            <button className="icon-btn" onClick={() => selectNode(null)} aria-label="Close panel">
              ×
            </button>
          </div>

          {!node.active && <div className="inspector-alert">Offline — disruption in effect</div>}

          <div className="stat-hero">
            <div>
              <span className="hud-label">On hand</span>
              <span className="stat-hero-value">{fmt(node.on_hand)}</span>
            </div>
            <Sparkline values={trend} />
            <span className="sparkline-caption">Last {SPARKLINE_PERIODS} periods</span>
          </div>

          <dl>
            <dt>Backlog</dt>
            <dd className={node.backlog > 0.5 ? 'warn' : ''}>{fmt(node.backlog)}</dd>
            <dt>Pipeline (on order to this node)</dt>
            <dd>{fmt(node.pipeline)}</dd>
            <dt>Last order placed</dt>
            <dd>{fmt(node.last_order)}</dd>
            <dt>Last demand received</dt>
            <dd>{fmt(node.last_demand)}</dd>
            <dt>Fill rate</dt>
            <dd>{pct(node.fill_rate)}</dd>
            <dt>Service level</dt>
            <dd>{pct(node.service_level)}</dd>
          </dl>

          <PolicySelector key={node.id} node={node} />
        </>
      )}
    </aside>
  )
}
