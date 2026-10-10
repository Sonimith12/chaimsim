import { useState } from 'react'
import { useSimStore } from '../store/simStore'
import { changePolicy } from '../hooks/useSimulation'
import type { NodeState, PolicyInfo } from '../types/sim'

export type PolicyType = Exclude<PolicyInfo['type'], 'custom'>

export interface Field {
  /** Param name the backend expects. */
  key: string
  label: string
}

export const POLICY_OPTIONS: { type: PolicyType; label: string; fields: Field[] }[] = [
  { type: 'order_up_to', label: 'OrderUpTo', fields: [{ key: 'S', label: 'target_level' }] },
  {
    type: 's_S',
    label: '(s, S)',
    fields: [
      { key: 's', label: 'reorder_point' },
      { key: 'S', label: 'order_up_to_level' },
    ],
  },
  {
    type: 'r_q',
    label: '(R, Q)',
    fields: [
      { key: 'R', label: 'reorder_point' },
      { key: 'Q', label: 'order_quantity' },
    ],
  },
  {
    type: 'base_stock',
    label: 'BaseStock',
    fields: [{ key: 'base_stock_level', label: 'base_stock_level' }],
  },
]

const LABEL_BY_TYPE: Record<PolicyInfo['type'], string> = {
  order_up_to: 'OrderUpTo',
  s_S: '(s, S)',
  r_q: '(R, Q)',
  base_stock: 'BaseStock',
  custom: 'Custom',
}

const fmt = (n: number) => (Number.isInteger(n) ? String(n) : n.toFixed(2))

/** Carry over values that mean the same thing under the newly chosen policy type. */
function prefill(fields: Field[], current: PolicyInfo | null): Record<string, string> {
  const p = current?.params ?? {}
  const level = p.S ?? p.base_stock_level
  const point = p.s ?? p.R
  const out: Record<string, string> = {}
  for (const f of fields) {
    let v: number | undefined
    if (f.key === 'S' || f.key === 'base_stock_level') v = level
    else if (f.key === 's' || f.key === 'R') v = point
    else if (f.key === 'Q') v = p.Q
    out[f.key] = v === undefined ? '' : String(Math.round(v * 100) / 100)
  }
  return out
}

function optionFor(type: PolicyType) {
  return POLICY_OPTIONS.find((o) => o.type === type)!
}

export function PolicySelector({ node }: { node: NodeState }) {
  const current = node.policy
  const initialType: PolicyType =
    current && current.type !== 'custom' ? current.type : 'order_up_to'

  const [type, setType] = useState<PolicyType>(initialType)
  const [values, setValues] = useState<Record<string, string>>(() =>
    prefill(optionFor(initialType).fields, current),
  )
  const [applied, setApplied] = useState(false)
  const [confirming, setConfirming] = useState(false)
  const cost = useSimStore((s) => s.economy?.policy_change_cost ?? 0)

  const option = optionFor(type)
  const parsed = option.fields.map((f) => (values[f.key]?.trim() === '' ? NaN : Number(values[f.key])))
  const allValid = parsed.every((n) => Number.isFinite(n) && n >= 0)

  let problem: string | null = null
  if (type === 's_S' && allValid && parsed[0] > parsed[1]) {
    problem = 'Reorder point must not exceed the order-up-to level'
  } else if (type === 'r_q' && allValid && parsed[1] <= 0) {
    problem = 'Order quantity must be positive'
  }

  const onTypeChange = (next: PolicyType) => {
    setType(next)
    setValues(prefill(optionFor(next).fields, current))
    setApplied(false)
  }

  const apply = () => {
    setConfirming(false)
    const params = Object.fromEntries(option.fields.map((f, i) => [f.key, parsed[i]]))
    if (changePolicy(node.id, type, params)) {
      setApplied(true)
      setTimeout(() => setApplied(false), 3000)
    }
  }

  return (
    <section className="policy">
      <h3>Replenishment policy</h3>

      <div className="policy-current">
        {current ? (
          <>
            <span className="policy-name">{LABEL_BY_TYPE[current.type]}</span>
            <span className="policy-params">
              {Object.entries(current.params)
                .map(([k, v]) => `${k} ${fmt(v)}`)
                .join(' · ')}
            </span>
          </>
        ) : (
          <span className="muted">None — replenishes from outside the network</span>
        )}
      </div>

      <label className="field">
        <span>Policy type</span>
        <select value={type} onChange={(e) => onTypeChange(e.target.value as PolicyType)}>
          {POLICY_OPTIONS.map((o) => (
            <option key={o.type} value={o.type}>
              {o.label}
            </option>
          ))}
        </select>
      </label>

      {option.fields.map((f) => (
        <label className="field" key={f.key}>
          <span>{f.label}</span>
          <input
            type="number"
            min={0}
            step="any"
            inputMode="decimal"
            value={values[f.key] ?? ''}
            onChange={(e) => {
              setValues({ ...values, [f.key]: e.target.value })
              setApplied(false)
            }}
          />
        </label>
      ))}

      {problem && <div className="field-problem">{problem}</div>}

      {confirming ? (
        <div className="confirm-box">
          <p>
            Change {node.name} policy to <strong>{option.label}</strong>? Cost:{' '}
            <strong>${Math.round(cost).toLocaleString()}</strong>
          </p>
          <div className="confirm-actions">
            <button className="primary" onClick={apply}>
              Confirm
            </button>
            <button onClick={() => setConfirming(false)}>Cancel</button>
          </div>
        </div>
      ) : (
        <button
          className="apply"
          onClick={() => setConfirming(true)}
          disabled={!allValid || problem !== null}
        >
          Apply{cost > 0 ? ` ($${Math.round(cost).toLocaleString()})` : ''}
        </button>
      )}
      <div className="policy-note">
        {applied
          ? 'Applied — takes effect on the next period.'
          : 'Changes take effect on the next period and cost money.'}
      </div>
    </section>
  )
}
