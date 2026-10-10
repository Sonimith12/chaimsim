import { useMemo, useState } from 'react'
import { useGameStore } from '../store/gameStore'
import { useHistoryStore, type RunRecord } from '../store/historyStore'
import { Stars } from './ResultsOverlay'
import { formatValue, GRADE_COLORS, money, objectiveTitle, pct, whole } from './format'

function CompareView({ a, b, onBack }: { a: RunRecord; b: RunRecord; onBack: () => void }) {
  const rows: [string, (r: RunRecord) => string][] = [
    ['Scenario', (r) => r.scenarioName],
    ['Score', (r) => whole(r.score)],
    ['Grade', (r) => r.grade],
    ['Total cost', (r) => money(r.stats.total_cost)],
    ['Fill rate', (r) => pct(r.stats.fill_rate)],
    ['Service level', (r) => pct(r.stats.service_level)],
    ['Waste', (r) => whole(r.stats.waste)],
    ['Stockouts', (r) => String(r.stats.stockouts)],
    ['Policy changes', (r) => String(r.stats.policy_changes)],
  ]
  const objectives = a.objectives.map((o, i) => ({ a: o, b: b.objectives[i] }))

  return (
    <>
      <button className="link-btn" onClick={onBack}>
        ← Back to runs
      </button>
      <div className="compare-grid">
        <div />
        {[a, b].map((r) => (
          <div key={r.id} className="compare-head">
            <div>{new Date(r.finishedAt).toLocaleTimeString()}</div>
            <Stars count={r.stars} />
          </div>
        ))}
        {rows.map(([label, fmt]) => (
          <div className="compare-row" key={label}>
            <div className="muted">{label}</div>
            <div>{fmt(a)}</div>
            <div>{fmt(b)}</div>
          </div>
        ))}
        <div className="compare-section muted">Objectives</div>
        {objectives.map(({ a: oa, b: ob }) => (
          <div className="compare-row" key={oa.id}>
            <div className="muted" title={objectiveTitle(oa)}>
              {oa.id === 'bonus' ? 'Bonus' : oa.id}
            </div>
            {[oa, ob].map((o, i) => (
              <div key={i} className={o?.met ? 'met' : 'missed'}>
                {o ? `${o.met ? '✓' : '✗'} ${formatValue(o.unit, o.actual)}` : '—'}
              </div>
            ))}
          </div>
        ))}
      </div>
    </>
  )
}

export function HistoryPanel() {
  const open = useGameStore((s) => s.historyOpen)
  const setOpen = useGameStore((s) => s.setHistoryOpen)
  const runs = useHistoryStore((s) => s.runs)
  const [picked, setPicked] = useState<number[]>([])
  const [comparing, setComparing] = useState(false)

  // Best score per scenario, for the highlight.
  const bestIds = useMemo(() => {
    const best = new Map<string, RunRecord>()
    for (const r of runs) {
      const cur = best.get(r.scenarioId)
      if (!cur || r.score > cur.score) best.set(r.scenarioId, r)
    }
    return new Set([...best.values()].map((r) => r.id))
  }, [runs])

  const toggle = (id: number) =>
    setPicked((p) => (p.includes(id) ? p.filter((x) => x !== id) : [...p, id].slice(-2)))

  const [a, b] = picked.map((id) => runs.find((r) => r.id === id))

  return (
    <aside className={`history${open ? ' open' : ''}`} aria-hidden={!open}>
      <div className="inspector-head">
        <h2>Run history</h2>
        <button className="icon-btn" onClick={() => setOpen(false)} aria-label="Close history">
          ×
        </button>
      </div>

      {comparing && a && b ? (
        <CompareView a={a} b={b} onBack={() => setComparing(false)} />
      ) : runs.length === 0 ? (
        <p className="muted">No completed runs yet. Finish a simulation to see it here.</p>
      ) : (
        <>
          <ul className="run-list">
            {runs.map((r) => (
              <li key={r.id} className={bestIds.has(r.id) ? 'best' : ''}>
                <input
                  type="checkbox"
                  checked={picked.includes(r.id)}
                  onChange={() => toggle(r.id)}
                  aria-label="Select for comparison"
                />
                <div className="run-main">
                  <div className="run-name">
                    {r.scenarioName}
                    {bestIds.has(r.id) && <span className="best-badge">Best</span>}
                  </div>
                  <div className="muted">
                    {new Date(r.finishedAt).toLocaleTimeString()} · <Stars count={r.stars} />
                  </div>
                </div>
                <div className="run-score">
                  <span style={{ color: GRADE_COLORS[r.grade] }} className="run-grade">
                    {r.grade}
                  </span>
                  <span>{whole(r.score)}</span>
                </div>
              </li>
            ))}
          </ul>
          <button className="apply" disabled={!(a && b)} onClick={() => setComparing(true)}>
            Compare {picked.length === 2 ? 'selected runs' : `(select ${2 - picked.length} more)`}
          </button>
        </>
      )}
    </aside>
  )
}
