import { useRef } from 'react'
import { useEditStore } from '../store/editStore'
import { useGameStore } from '../store/gameStore'
import type { DemandSpec, NodeSpec, PolicySpec } from '../types/sim'
import { NumField } from './NumField'
import { POLICY_OPTIONS, type PolicyType } from './PolicySelector'

const TYPE_LABELS: Record<string, string> = {
  Supplier: 'Supplier',
  Manufacturer: 'Manufacturer',
  DistributionCenter: 'Distribution center',
  Retailer: 'Retailer',
}

interface ParamField {
  key: keyof DemandSpec
  label: string
}

const DEMAND_FIELDS: Record<DemandSpec['type'], ParamField[]> = {
  stationary: [
    { key: 'mean', label: 'mean' },
    { key: 'std', label: 'std (normal only)' },
  ],
  seasonal: [
    { key: 'base', label: 'base' },
    { key: 'amplitude', label: 'amplitude' },
    { key: 'period_length', label: 'period_length' },
    { key: 'noise_std', label: 'noise_std' },
  ],
  trend: [
    { key: 'base', label: 'base' },
    { key: 'trend_per_period', label: 'trend_per_period' },
    { key: 'noise_std', label: 'noise_std' },
  ],
}

/** Sensible starting values when switching policy type, carrying over what means the same thing. */
function policyDefaults(type: PolicyType, prev: PolicySpec | null): Record<string, number> {
  const p = prev?.params ?? {}
  const level = p.S ?? p.base_stock_level ?? 300
  const point = p.s ?? p.R ?? Math.round(level * 0.5)
  switch (type) {
    case 'order_up_to':
      return { S: level }
    case 's_S':
      return { s: Math.min(point, level), S: level }
    case 'r_q':
      return { R: point, Q: p.Q ?? Math.max(1, Math.round(level * 0.5)) }
    case 'base_stock':
      return { base_stock_level: level }
  }
}

function DemandEditor({ node }: { node: NodeSpec }) {
  const update = useEditStore((s) => s.updateNode)
  const demand = node.demand
  if (!demand) return null
  const set = (patch: Partial<DemandSpec>) => update(node.id, { demand: { ...demand, ...patch } })

  return (
    <section className="policy">
      <h3>Demand</h3>
      <label className="field">
        <span>Type</span>
        <select
          value={demand.type}
          onChange={(e) => set({ type: e.target.value as DemandSpec['type'] })}
        >
          <option value="stationary">Stationary</option>
          <option value="seasonal">Seasonal</option>
          <option value="trend">Trend</option>
        </select>
      </label>
      {DEMAND_FIELDS[demand.type].map((f) => (
        <label className="field" key={f.key}>
          <span>{f.label}</span>
          <NumField
            value={demand[f.key] as number}
            min={0}
            step={f.key === 'period_length' ? 1 : 'any'}
            onCommit={(v) => set({ [f.key]: f.key === 'period_length' ? Math.max(1, Math.round(v)) : v })}
          />
        </label>
      ))}
      {demand.type === 'stationary' && (
        <label className="field">
          <span>distribution</span>
          <select
            value={demand.distribution}
            onChange={(e) => set({ distribution: e.target.value as DemandSpec['distribution'] })}
          >
            <option value="poisson">Poisson</option>
            <option value="normal">Normal</option>
          </select>
        </label>
      )}
    </section>
  )
}

function PolicyEditor({ node }: { node: NodeSpec }) {
  const update = useEditStore((s) => s.updateNode)
  const policy = node.policy
  const option = POLICY_OPTIONS.find((o) => o.type === policy?.type)

  const onType = (value: string) => {
    if (value === 'none') return update(node.id, { policy: null })
    const type = value as PolicyType
    update(node.id, { policy: { type, params: policyDefaults(type, policy) } })
  }

  return (
    <section className="policy">
      <h3>Replenishment policy</h3>
      <label className="field">
        <span>Policy type</span>
        <select value={policy?.type ?? 'none'} onChange={(e) => onType(e.target.value)}>
          <option value="none">None (external supply)</option>
          {POLICY_OPTIONS.map((o) => (
            <option key={o.type} value={o.type}>
              {o.label}
            </option>
          ))}
        </select>
      </label>
      {policy &&
        option?.fields.map((f) => (
          <label className="field" key={f.key}>
            <span>{f.label}</span>
            <NumField
              value={policy.params[f.key] ?? 0}
              min={0}
              onCommit={(v) =>
                update(node.id, { policy: { ...policy, params: { ...policy.params, [f.key]: v } } })
              }
            />
          </label>
        ))}
    </section>
  )
}

/** Right-hand configuration panel for the selected node while editing. */
export function EditPanel() {
  const selectedId = useGameStore((s) => s.selectedNodeId)
  const selectNode = useGameStore((s) => s.selectNode)
  const live = useEditStore((s) => s.spec?.nodes.find((n) => n.id === selectedId))
  const update = useEditStore((s) => s.updateNode)

  // Keep showing the last node while the panel slides out.
  const last = useRef<NodeSpec | undefined>(undefined)
  if (live) last.current = live
  const node = live ?? last.current
  const open = live !== undefined

  return (
    <aside className={`inspector edit-panel${open ? ' open' : ''}`} aria-hidden={!open}>
      {node && (
        <>
          <div className="inspector-head">
            <div>
              <h2>Configure node</h2>
              <span className="inspector-type">
                {TYPE_LABELS[node.type] ?? node.type} · id {node.id}
              </span>
            </div>
            <button className="icon-btn" onClick={() => selectNode(null)} aria-label="Close panel">
              ×
            </button>
          </div>

          <label className="field first">
            <span>Name</span>
            <input
              type="text"
              value={node.name}
              maxLength={30}
              onChange={(e) => update(node.id, { name: e.target.value })}
            />
          </label>
          <label className="field">
            <span>Initial inventory</span>
            <NumField value={node.initial_inventory} min={0} onCommit={(v) => update(node.id, { initial_inventory: v })} />
          </label>
          <label className="field">
            <span>Holding cost (per unit per period)</span>
            <NumField value={node.holding_cost} min={0} onCommit={(v) => update(node.id, { holding_cost: v })} />
          </label>
          {node.type === 'Retailer' && (
            <label className="field">
              <span>Backlog cost (per unit per period)</span>
              <NumField value={node.backlog_cost} min={0} onCommit={(v) => update(node.id, { backlog_cost: v })} />
            </label>
          )}
          <div className="field">
            <label className="check-row">
              <input
                type="checkbox"
                checked={node.capacity !== null}
                onChange={(e) => update(node.id, { capacity: e.target.checked ? 200 : null })}
              />
              <span>Limit capacity (units per period)</span>
            </label>
            {node.capacity !== null && (
              <NumField value={node.capacity} min={0} onCommit={(v) => update(node.id, { capacity: v })} />
            )}
          </div>

          {node.type === 'Retailer' && node.forecast !== null ? (
            <section className="policy">
              <h3>Demand forecast</h3>
              <p>
                About <strong>{Math.round(node.forecast)}</strong> units per period.
              </p>
              <p className="muted">Forecasts are approximate; actual demand will vary.</p>
            </section>
          ) : (
            node.type === 'Retailer' && <DemandEditor node={node} />
          )}
          <PolicyEditor node={node} />
        </>
      )}
    </aside>
  )
}
