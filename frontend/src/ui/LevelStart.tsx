import { startCampaignLevel } from '../hooks/useCampaign'
import { useCampaignStore } from '../store/campaignStore'
import { useGameStore } from '../store/gameStore'

const TIER_LABEL = { required: 'Required', goal: 'Goal', bonus: 'Bonus' } as const

export function LevelStart() {
  const id = useGameStore((s) => s.selectedLevel)
  const setView = useGameStore((s) => s.setSetupView)
  const error = useGameStore((s) => s.error)
  const level = useCampaignStore((s) => s.levels.find((l) => l.id === id))
  const best = useCampaignStore((s) => (id ? s.progress[id] : undefined))

  if (!level) return null

  return (
    <div className="setup level-start">
      <button className="link-btn" onClick={() => setView('campaign')}>
        ← Campaign map
      </button>
      <div className="level-kicker">
        Act {level.act} · {level.act_name} · Level {level.id}
      </div>
      <h1>{level.name}</h1>
      <div className="difficulty" aria-label={`Difficulty ${level.difficulty} of 5`}>
        {[1, 2, 3, 4, 5].map((n) => (
          <i key={n} className={n <= level.difficulty ? 'on' : ''} />
        ))}
        <span className="muted"> difficulty</span>
      </div>

      <p className="level-blurb">{level.blurb}</p>
      <p className="muted">{level.description}</p>

      <section>
        <h3>Objectives</h3>
        <ul className="objective-list level-objectives">
          {level.objectives.map((o, i) => (
            <li key={i} className={o.tier === 'bonus' ? 'bonus' : ''}>
              <span className={`tier-pill ${o.tier}`}>{TIER_LABEL[o.tier]}</span>
              <span className="objective-title">{o.label}</span>
            </li>
          ))}
        </ul>
        <p className="muted tier-help">
          ★ meet the required objectives · ★★ and all goals · ★★★ and the bonus
        </p>
      </section>

      {level.special_rules.length > 0 && (
        <section>
          <h3>Special rules</h3>
          <ul className="rules">
            {level.special_rules.map((r) => (
              <li key={r}>{r}</li>
            ))}
          </ul>
        </section>
      )}

      <section className="level-best">
        {best ? (
          <>
            <span>
              Best: <strong>{Math.round(best.bestScore).toLocaleString()}</strong>
            </span>
            <span className="map-node-stars">
              {[1, 2, 3].map((n) => (
                <span key={n} className={n <= best.stars ? 'on' : ''}>★</span>
              ))}
            </span>
            <span className="muted">
              {best.attempts} attempt{best.attempts === 1 ? '' : 's'}
            </span>
          </>
        ) : (
          <span className="muted">Not attempted yet</span>
        )}
      </section>

      {error && <div className="hud-banner">{error}</div>}
      <button className="start-btn level-go" onClick={() => startCampaignLevel(level.id)}>
        {level.edit_mode ? 'Start Building ▶' : 'Start Level ▶'}
      </button>
    </div>
  )
}
