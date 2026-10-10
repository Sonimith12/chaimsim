import { useMemo, useRef, useState } from 'react'
import { useFeature } from '../store/campaignStore'
import { useGameStore } from '../store/gameStore'
import { useSimStore } from '../store/simStore'
import type { FlowBuckets, NodeState } from '../types/sim'
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
const dollars = (n: number) => `${n < 0 ? '-' : ''}$${Math.abs(Math.round(n)).toLocaleString()}`

const FLOW_ROWS: { key: keyof FlowBuckets; label: string; income?: boolean }[] = [
  { key: 'revenue', label: 'Revenue', income: true },
  { key: 'holding', label: 'Holding cost' },
  { key: 'backlog', label: 'Backlog penalty' },
  { key: 'transport', label: 'Transport' },
  { key: 'ordering', label: 'Ordering' },
  { key: 'policy', label: 'Policy changes' },
  { key: 'events', label: 'Event decisions' },
]

const ANALYTICS: { label: string; pick: (n: NodeState) => number }[] = [
  { label: 'On hand', pick: (n) => n.on_hand },
  { label: 'Backlog', pick: (n) => n.backlog },
  { label: 'Orders placed', pick: (n) => n.last_order },
  { label: 'Demand received', pick: (n) => n.last_demand },
]

/** Whole-run history of one node: small charts of its key series. */
function Analytics({ nodeId }: { nodeId: string }) {
  const history = useSimStore((s) => s.history)
  const rows = useMemo(
    () => history.map((h) => h.nodes.find((n) => n.id === nodeId)).filter((n): n is NodeState => !!n),
    [history, nodeId],
  )
  return (
    <div className="analytics">
      {ANALYTICS.map((a) => {
        const values = rows.map(a.pick)
        const last = values[values.length - 1]
        return (
          <div key={a.label} className="analytics-row">
            <div className="analytics-head">
              <span>{a.label}</span>
              <span>{last === undefined ? '—' : Math.round(last).toLocaleString()}</span>
            </div>
            <Sparkline values={values} width={252} height={34} />
          </div>
        )
      })}
      <p className="muted sparkline-caption">All {rows.length} periods so far</p>
    </div>
  )
}

function Financials({ node }: { node: NodeState }) {
  const f = node.financials
  if (!f) return <p className="muted">No financial data yet.</p>
  const cell = (v: number, income: boolean) => (
    <td className={v === 0 ? 'muted' : income ? 'pos' : 'neg'}>
      {v === 0 ? '—' : `${income ? '+' : '-'}${dollars(v)}`}
    </td>
  )
  return (
    <table className="fin-table">
      <thead>
        <tr>
          <th />
          <th>This period</th>
          <th>Cumulative</th>
        </tr>
      </thead>
      <tbody>
        {FLOW_ROWS.map((r) => (
          <tr key={r.key}>
            <td>{r.label}</td>
            {cell(f.period[r.key], !!r.income)}
            {cell(f.cumulative[r.key], !!r.income)}
          </tr>
        ))}
        <tr className="total">
          <td>Net profit / loss</td>
          <td className={f.period.net >= 0 ? 'pos' : 'neg'}>{dollars(f.period.net)}</td>
          <td className={f.cumulative.net >= 0 ? 'pos' : 'neg'}>{dollars(f.cumulative.net)}</td>
        </tr>
      </tbody>
    </table>
  )
}
const pct = (n: number | null) => (n === null ? '—' : `${(n * 100).toFixed(1)}%`)

export function NodeInspector() {
  const selectedId = useGameStore((s) => s.selectedNodeId)
  const selectNode = useGameStore((s) => s.selectNode)
  const nodes = useSimStore((s) => s.networkState.nodes)
  const history = useSimStore((s) => s.history)

  const [tab, setTab] = useState<'overview' | 'financials' | 'analytics'>('overview')
  const analytics = useFeature('analytics')
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

          <div className="tabs" role="tablist">
            <button
              role="tab"
              className={tab === 'overview' ? 'active' : ''}
              onClick={() => setTab('overview')}
            >
              Overview
            </button>
            <button
              role="tab"
              className={tab === 'financials' ? 'active' : ''}
              onClick={() => setTab('financials')}
            >
              Financials
            </button>
            {analytics && (
              <button
                role="tab"
                className={tab === 'analytics' ? 'active' : ''}
                onClick={() => setTab('analytics')}
              >
                Analytics
              </button>
            )}
          </div>

          {tab === 'financials' ? (
            <Financials node={node} />
          ) : tab === 'analytics' && analytics ? (
            <Analytics nodeId={node.id} />
          ) : (
            <>
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
        </>
      )}
    </aside>
  )
}
