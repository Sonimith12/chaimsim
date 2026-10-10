import { useEffect } from 'react'
import { fetchLevels } from '../hooks/useCampaign'
import { totalStars, unlockedUpTo, useCampaignStore } from '../store/campaignStore'
import { useGameStore } from '../store/gameStore'

const W = 980
const H = 420

/** Level positions along a winding road. */
const point = (i: number): [number, number] => [70 + i * 93, H / 2 + Math.sin(i * 0.95 + 0.4) * 120]

export function CampaignMap() {
  const levels = useCampaignStore((s) => s.levels)
  const progress = useCampaignStore((s) => s.progress)
  const setView = useGameStore((s) => s.setSetupView)
  const error = useGameStore((s) => s.error)

  useEffect(() => {
    void fetchLevels()
  }, [])

  const unlocked = unlockedUpTo(progress, levels.length || 10)
  const road = levels.map((_, i) => point(i)).map(([x, y]) => `${x},${y}`).join(' ')
  const acts = [...new Set(levels.map((l) => l.act))]

  return (
    <div className="setup campaign-map">
      <div className="map-head">
        <button className="link-btn" onClick={() => setView('home')}>
          ← Back
        </button>
        <h1>Campaign</h1>
        <span className="map-stars">★ {totalStars(progress)} / {levels.length * 3}</span>
      </div>

      {levels.length === 0 ? (
        <p className="muted">{error ?? 'Loading levels…'}</p>
      ) : (
        <div className="map-scroll">
          <div className="map" style={{ width: W, height: H }}>
            <svg width={W} height={H} className="map-road" aria-hidden>
              <polyline points={road} fill="none" stroke="#1e293b" strokeWidth="16" strokeLinecap="round" strokeLinejoin="round" />
              <polyline points={road} fill="none" stroke="#38bdf8" strokeOpacity="0.35" strokeWidth="2" strokeDasharray="6 8" strokeLinecap="round" strokeLinejoin="round" />
            </svg>

            {acts.map((act) => {
              const first = levels.findIndex((l) => l.act === act)
              const [x] = point(first)
              return (
                <div key={act} className="act-label" style={{ left: x - 30 }}>
                  Act {act} — {levels.find((l) => l.act === act)?.act_name}
                </div>
              )
            })}

            {levels.map((level, i) => {
              const [x, y] = point(i)
              const p = progress[level.id]
              const locked = level.id > unlocked
              const done = (p?.stars ?? 0) > 0
              const current = !locked && !done && level.id === unlocked
              return (
                <button
                  key={level.id}
                  className={`map-node${locked ? ' locked' : ''}${done ? ' done' : ''}${current ? ' current' : ''}`}
                  style={{ left: x, top: y }}
                  disabled={locked}
                  onClick={() => setView('levelStart', level.id)}
                  aria-label={`Level ${level.id}: ${level.name}${locked ? ' (locked)' : ''}`}
                >
                  <span className="map-node-badge">
                    {locked ? '🔒' : done ? '✓' : level.id}
                  </span>
                  <span className="map-node-name">{level.name}</span>
                  <span className="map-node-stars" aria-label={`${p?.stars ?? 0} of 3 stars`}>
                    {[1, 2, 3].map((n) => (
                      <span key={n} className={n <= (p?.stars ?? 0) ? 'on' : ''}>★</span>
                    ))}
                  </span>
                  <span className="map-node-diff" aria-label={`Difficulty ${level.difficulty} of 5`}>
                    {[1, 2, 3, 4, 5].map((n) => (
                      <i key={n} className={n <= level.difficulty ? 'on' : ''} />
                    ))}
                  </span>
                </button>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}
