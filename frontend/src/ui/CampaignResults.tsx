import { startCampaignLevel } from '../hooks/useCampaign'
import { backToSetup, resetRun } from '../hooks/useSimulation'
import { useCampaignStore } from '../store/campaignStore'
import { useGameStore } from '../store/gameStore'
import { useSimStore } from '../store/simStore'
import { formatValue, GRADE_COLORS, money, whole } from './format'

const TIER_LABEL = { required: 'Required', goal: 'Goal', bonus: 'Bonus' } as const

/** End-of-run screen for a campaign level: stars, best-score comparison, what's next. */
export function CampaignResults() {
  const phase = useGameStore((s) => s.currentPhase)
  const levelId = useGameStore((s) => s.campaignLevel)
  const result = useSimStore((s) => s.result)
  const score = useSimStore((s) => s.score)
  const objectives = useSimStore((s) => s.objectives)
  const level = useCampaignStore((s) => s.levels.find((l) => l.id === levelId))
  const last = useCampaignStore((s) => s.lastRecord)
  const total = useCampaignStore((s) => s.levels.length)

  if (phase !== 'results' || !result?.campaign || !score || !level) return null
  const c = result.campaign
  const isFinal = level.id === total
  const mastered = isFinal && c.passed
  const prev = last?.levelId === level.id ? last : null

  const headline = result.bankrupt ? 'BANKRUPT' : c.passed ? 'LEVEL COMPLETE' : 'LEVEL FAILED'
  const tone = c.passed ? 'win' : 'loss'

  return (
    <div className={`results campaign-results ${tone}${mastered ? ' mastered' : ''}`}>
      {mastered && <div className="master-banner">★ SUPPLY CHAIN MASTER ★</div>}
      <div className="results-scenario">
        Level {level.id} · {level.name}
      </div>
      <div className={`campaign-headline ${tone}`}>{headline}</div>

      <div className="big-stars" aria-label={`${c.stars} of 3 stars`}>
        {[1, 2, 3].map((n) => (
          <span key={n} className={n <= c.stars ? 'on' : ''} style={{ animationDelay: `${n * 0.18}s` }}>
            ★
          </span>
        ))}
      </div>

      <div className="results-hero compact">
        <div className="results-grade" style={{ color: GRADE_COLORS[result.grade] }}>
          {result.grade}
        </div>
        <div>
          <div className="results-score">{whole(score.total)}</div>
          <div className="hud-label">Final score</div>
          {prev && (
            <div className="best-compare">
              {prev.previousBest === null
                ? 'First attempt'
                : prev.isBestScore
                  ? `New best! (was ${whole(prev.previousBest)})`
                  : `Best: ${whole(prev.previousBest)}`}
            </div>
          )}
        </div>
      </div>

      <ul className="objective-list results-objectives">
        {objectives.map((o) => (
          <li key={o.id} className={o.bonus ? 'bonus' : ''}>
            <span className={`check ${o.met ? 'met' : 'missed'}`}>{o.met ? '✓' : '✗'}</span>
            <span className="objective-title">
              {o.tier && <span className={`tier-pill ${o.tier}`}>{TIER_LABEL[o.tier]}</span>}
              {o.label}
            </span>
            <span className="objective-actual">{formatValue(o.unit, o.actual)}</span>
          </li>
        ))}
      </ul>

      <dl className="results-stats">
        <dt>Final cash</dt>
        <dd className={result.stats.cash >= 0 ? '' : 'neg'}>{money(result.stats.cash)}</dd>
        <dt>Net profit</dt>
        <dd className={result.stats.net_profit >= 0 ? 'pos' : 'neg'}>{money(result.stats.net_profit)}</dd>
        <dt>Stockouts</dt>
        <dd>{result.stats.stockouts}</dd>
      </dl>

      <p className="story">
        {c.passed
          ? level.completion
          : result.bankrupt
            ? 'The company ran out of money. Rethink the budget and try again.'
            : 'Not quite. Check which required objective slipped and try again.'}
      </p>
      {prev?.newlyUnlocked && !isFinal && <p className="unlock-note">🔓 Level {level.id + 1} unlocked</p>}

      <div className="hud-controls results-actions">
        {c.passed && !isFinal && (
          <button className="primary" onClick={() => startCampaignLevel(level.id + 1)}>
            Next Level ▶
          </button>
        )}
        <button className={c.passed ? '' : 'primary'} onClick={resetRun}>
          {c.passed ? 'Replay' : 'Try Again'}
        </button>
        <button onClick={backToSetup}>Level Select</button>
      </div>
    </div>
  )
}
