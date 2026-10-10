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

const signed = (n: number) => `${n < 0 ? '-' : ''}${money(Math.abs(n))}`

const BANKRUPT_REASONS = {
  insolvent: 'Cash stayed at zero for too many consecutive periods.',
  overdraft: 'Cash fell past the overdraft limit.',
} as const

function EventsSummary() {
  const log = useSimStore((s) => s.eventLog)
  if (log.length === 0) return null
  return (
    <div className="results-section">
      <h3>Events ({log.length})</h3>
      <ul className="event-log compact">
        {log.map((e) => (
          <li key={e.uid}>
            <span>
              {e.icon} <strong>P{e.period}</strong> {e.title}
            </span>
            <span className="muted">
              {e.auto ? 'timed out → ' : ''}
              {e.choice}
            </span>
            <span className={e.cash_delta < 0 ? 'neg' : e.cash_delta > 0 ? 'pos' : 'muted'}>
              {e.cash_delta === 0 ? '—' : signed(e.cash_delta)}
            </span>
          </li>
        ))}
      </ul>
    </div>
  )
}

function Financials() {
  const result = useSimStore((s) => s.result)
  if (!result) return null
  const { stats } = result
  const c = stats.costs
  return (
    <div className="results-section">
      <h3>Financials</h3>
      <dl className="results-stats">
        <dt>Total revenue</dt>
        <dd className="pos">{money(stats.revenue)}</dd>
        <dt>Holding costs</dt>
        <dd>{money(c.holding)}</dd>
        <dt>Backlog penalties</dt>
        <dd>{money(c.backlog)}</dd>
        <dt>Transportation</dt>
        <dd>{money(c.transport)}</dd>
        <dt>Ordering</dt>
        <dd>{money(c.ordering)}</dd>
        <dt>Policy changes</dt>
        <dd>{money(c.policy)}</dd>
        <dt>Event decisions</dt>
        <dd>{money(c.events)}</dd>
        <dt>Infrastructure</dt>
        <dd>{money(c.infrastructure)}</dd>
        <dt>Total costs</dt>
        <dd>{money(c.total)}</dd>
        <dt>Net profit</dt>
        <dd className={stats.net_profit >= 0 ? 'pos' : 'neg'}>{signed(stats.net_profit)}</dd>
        <dt>Profit margin</dt>
        <dd className={stats.margin >= 0 ? 'pos' : 'neg'}>{pct(stats.margin)}</dd>
        <dt>Final cash</dt>
        <dd className={stats.cash >= 0 ? '' : 'neg'}>{signed(stats.cash)}</dd>
      </dl>
    </div>
  )
}

export function ResultsOverlay() {
  const phase = useGameStore((s) => s.currentPhase)
  const result = useSimStore((s) => s.result)
  const score = useSimStore((s) => s.score)
  const objectives = useSimStore((s) => s.objectives)
  const name = useSimStore((s) => s.scenarioName)
  const nPeriods = useSimStore((s) => s.nPeriods)
  const mode = useGameStore((s) => s.mode)
  if (phase !== 'results' || !result || !score) return null
  if (mode === 'campaign' && result.campaign) return null // CampaignResults handles it

  const { stats } = result
  const actions = (
    <div className="hud-controls results-actions">
      <button className="primary" onClick={resetRun}>
        {result.bankrupt ? 'Try Again' : 'Play Again'}
      </button>
      <button onClick={backToSetup}>Try Another Scenario</button>
    </div>
  )

  if (result.bankrupt) {
    return (
      <div className="results bankrupt">
        <div className="results-scenario">{name}</div>
        <div className="bankrupt-title">BANKRUPTCY</div>
        <p className="muted">
          {result.bankrupt_reason ? BANKRUPT_REASONS[result.bankrupt_reason] : ''} The company
          folded after {result.periods_completed} of {nPeriods} periods.
        </p>
        <dl className="results-stats">
          <dt>Score at collapse</dt>
          <dd>{whole(score.total)}</dd>
          <dt>Revenue</dt>
          <dd>{money(stats.revenue)}</dd>
          <dt>Total costs</dt>
          <dd>{money(stats.costs.total)}</dd>
          <dt>Final cash</dt>
          <dd className="neg">{signed(stats.cash)}</dd>
          <dt>Stockouts</dt>
          <dd>{stats.stockouts}</dd>
          <dt>Policy changes</dt>
          <dd>{stats.policy_changes}</dd>
        </dl>
        <Financials />
        <EventsSummary />
        {actions}
      </div>
    )
  }

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

      <Financials />
      <EventsSummary />
      {actions}
    </div>
  )
}
