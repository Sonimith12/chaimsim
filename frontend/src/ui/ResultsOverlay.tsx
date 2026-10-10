import { backToSetup, resetRun } from '../hooks/useSimulation'
import { useGameStore } from '../store/gameStore'
import { useSimStore } from '../store/simStore'
import { formatValue, GRADE_COLORS, money, objectiveTitle, pct, whole } from './format'

export function Stars({ count }: { count: number }) {
  return (
    <span className="stars" aria-label={`${count} of 5 stars`}>
      {Array.from({ length: 5 }, (_, i) => (
        <span key={i} className={i < count ? 'star on' : 'star'}>
          ★
        </span>
      ))}
    </span>
  )
}

export function ResultsOverlay() {
  const phase = useGameStore((s) => s.currentPhase)
  const result = useSimStore((s) => s.result)
  const score = useSimStore((s) => s.score)
  const objectives = useSimStore((s) => s.objectives)
  const name = useSimStore((s) => s.scenarioName)
  if (phase !== 'results' || !result || !score) return null

  const { stats } = result
  return (
    <div className="results">
      <div className="results-scenario">{name} — run complete</div>

      <div className="results-hero">
        <div className="results-grade" style={{ color: GRADE_COLORS[result.grade] }}>
          {result.grade}
        </div>
        <div>
          <div className="results-score">{whole(score.total)}</div>
          <div className="hud-label">Final score</div>
          <Stars count={result.stars} />
        </div>
      </div>

      <ul className="objective-list results-objectives">
        {objectives.map((o) => (
          <li key={o.id} className={o.bonus ? 'bonus' : ''}>
            <span className={`check ${o.met ? 'met' : 'missed'}`}>{o.met ? '✓' : '✗'}</span>
            <span className="objective-title">{objectiveTitle(o)}</span>
            <span className="objective-actual">{formatValue(o.unit, o.actual)}</span>
          </li>
        ))}
      </ul>

      <dl className="results-stats">
        <dt>Total cost</dt>
        <dd>{money(stats.total_cost)}</dd>
        <dt>Avg fill rate</dt>
        <dd>{pct(stats.fill_rate)}</dd>
        <dt>Avg service level</dt>
        <dd>{pct(stats.service_level)}</dd>
        <dt>Total waste</dt>
        <dd>{whole(stats.waste)}</dd>
        <dt>Stockouts</dt>
        <dd>{stats.stockouts}</dd>
        <dt>Policy changes</dt>
        <dd>{stats.policy_changes}</dd>
      </dl>

      <div className="hud-controls results-actions">
        <button className="primary" onClick={resetRun}>
          Play Again
        </button>
        <button onClick={backToSetup}>Try Another Scenario</button>
      </div>
    </div>
  )
}
