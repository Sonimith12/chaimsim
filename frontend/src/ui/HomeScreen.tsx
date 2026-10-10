import { useEffect } from 'react'
import { fetchLevels } from '../hooks/useCampaign'
import { useCampaignStore, useFeature, totalStars, unlockedUpTo } from '../store/campaignStore'
import { useGameStore } from '../store/gameStore'

export function HomeScreen() {
  const setView = useGameStore((s) => s.setSetupView)
  const setMode = useGameStore((s) => s.setMode)
  const error = useGameStore((s) => s.error)
  const progress = useCampaignStore((s) => s.progress)
  const levels = useCampaignStore((s) => s.levels)
  const master = useFeature('master')

  useEffect(() => {
    void fetchLevels()
  }, [])

  const stars = totalStars(progress)
  const next = unlockedUpTo(progress, levels.length || 10)
  const started = Object.keys(progress).length > 0

  return (
    <div className="setup home">
      <h1>ChainSim 3D</h1>
      <p className="tagline">
        {master ? 'Supply Chain Master' : 'Run the supply chain. Survive the surprises.'}
      </p>

      <div className="home-options">
        <button
          className="home-card primary"
          onClick={() => {
            setMode('campaign')
            setView('campaign')
          }}
        >
          <span className="home-card-kicker">Campaign</span>
          <span className="home-card-title">{started ? 'Continue the journey' : 'Start the journey'}</span>
          <span className="home-card-desc">
            Ten levels, from a corner shop to a global network. Meet the objectives to unlock the next.
          </span>
          <span className="home-card-meta">
            {started ? `Next: level ${next} · ★ ${stars} collected` : '10 levels · 4 acts'}
          </span>
        </button>

        <button
          className="home-card"
          onClick={() => {
            setMode('sandbox')
            setView('sandbox')
          }}
        >
          <span className="home-card-kicker">Sandbox</span>
          <span className="home-card-title">Free play</span>
          <span className="home-card-desc">
            Pick a scenario or start from a blank map. Edit the network, set the rules, run it.
          </span>
        </button>
      </div>
      {error && <div className="hud-banner">{error}</div>}
    </div>
  )
}
