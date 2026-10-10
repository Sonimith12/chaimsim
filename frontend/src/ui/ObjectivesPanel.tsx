import { useEffect, useState } from 'react'
import { useSimStore } from '../store/simStore'
import type { Objective } from '../types/sim'
import { formatValue, objectiveTitle } from './format'

const INTRO_MS = 3000

const STATUS_LABEL: Record<Objective['status'], string> = {
  ok: 'On track',
  borderline: 'Borderline',
  failing: 'Off track',
}

function ObjectiveList({ objectives }: { objectives: Objective[] }) {
  return (
    <ul className="objective-list">
      {objectives.map((o) => (
        <li key={o.id} className={o.bonus ? 'bonus' : ''}>
          <span className={`dot ${o.status}`} title={STATUS_LABEL[o.status]} />
          <span className="objective-title">
            {o.tier && <span className={`tier-pill ${o.tier}`}>{o.tier}</span>}
            {objectiveTitle(o)}
          </span>
          <span className="objective-actual">{formatValue(o.unit, o.actual)}</span>
        </li>
      ))}
    </ul>
  )
}

/**
 * Shows the run's objectives for a few seconds when a scenario loads, then
 * collapses to a small HUD button that toggles a dropdown.
 */
export function ObjectivesPanel() {
  const objectives = useSimStore((s) => s.objectives)
  const runId = useSimStore((s) => s.runId)
  const [view, setView] = useState<'intro' | 'closed' | 'open'>('intro')

  useEffect(() => {
    setView('intro')
    const timer = setTimeout(() => setView((v) => (v === 'intro' ? 'closed' : v)), INTRO_MS)
    return () => clearTimeout(timer)
  }, [runId])

  if (objectives.length === 0) return null

  return (
    <>
      <button
        className={`objectives-btn${view === 'open' ? ' active' : ''}`}
        onClick={() => setView((v) => (v === 'open' ? 'closed' : 'open'))}
        title="Objectives"
      >
        ◎ Objectives
      </button>

      <div className={`objectives-card${view === 'intro' ? ' intro show' : ''}${view === 'open' ? ' show' : ''}`}>
        <h2>{view === 'intro' ? 'Your objectives' : 'Objectives'}</h2>
        <ObjectiveList objectives={objectives} />
      </div>
    </>
  )
}
