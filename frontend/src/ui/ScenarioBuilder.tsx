import { useEffect, useState } from 'react'
import { openBlank, openPresetForEdit } from '../hooks/useEditor'
import { useGameStore } from '../store/gameStore'
import type { ScenarioInfo } from '../types/sim'

// Matches the backend's pre-built scenario ids; the descriptions come from the server when reachable.
const FALLBACK: ScenarioInfo[] = [
  { id: 'retail_replenishment', name: 'Retail Replenishment', description: '', n_periods: 0 },
  { id: 'pharma_cold_chain', name: 'Pharma Cold Chain', description: '', n_periods: 0 },
  { id: 'manufacturing_jit', name: 'Manufacturing JIT', description: '', n_periods: 0 },
  { id: 'global_commodity_flow', name: 'Global Commodity Flow', description: '', n_periods: 0 },
]

export function ScenarioBuilder() {
  const [scenarios, setScenarios] = useState<ScenarioInfo[]>(FALLBACK)
  const [loading, setLoading] = useState<string | null>(null)
  const error = useGameStore((s) => s.error)

  useEffect(() => {
    fetch('/api/scenarios')
      .then((r) => (r.ok ? r.json() : Promise.reject()))
      .then(setScenarios)
      .catch(() => {})
  }, [])

  const pick = async (id: string) => {
    setLoading(id)
    await openPresetForEdit(id)
    setLoading(null)
  }

  return (
    <div className="setup">
      <h1>ChainSim 3D</h1>
      <p className="muted">Pick a scenario to edit, then run it.</p>
      <div className="scenario-grid">
        {scenarios.map((s) => (
          <button key={s.id} className="scenario-card" disabled={loading !== null} onClick={() => pick(s.id)}>
            <span className="scenario-name">{s.name}</span>
            {s.description && <span className="scenario-desc">{s.description}</span>}
            {s.n_periods > 0 && <span className="scenario-meta">{s.n_periods} periods</span>}
            {loading === s.id && <span className="scenario-meta">Loading…</span>}
          </button>
        ))}
      </div>
      <p className="setup-blank">
        <button className="link-btn" onClick={openBlank}>
          Or start with an empty network
        </button>
      </p>
      {error && <div className="hud-banner">{error}</div>}
    </div>
  )
}
