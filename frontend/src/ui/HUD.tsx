import { backToSetup, pause, play, resetRun, step } from '../hooks/useSimulation'
import { useGameStore, type Speed } from '../store/gameStore'
import { useSimStore } from '../store/simStore'
import { useHistoryStore } from '../store/historyStore'
import { useFeature } from '../store/campaignStore'
import { CashBadge } from './CashBadge'
import { ObjectivesPanel } from './ObjectivesPanel'
import { ScoreBar } from './ScoreBar'

const BASE_SPEEDS: Speed[] = ['slow', 'normal', 'fast']

const money = (n: number) =>
  n.toLocaleString(undefined, { style: 'currency', currency: 'USD', maximumFractionDigits: 0 })
const pct = (n: number) => `${(n * 100).toFixed(1)}%`

export function HUD() {
  const phase = useGameStore((s) => s.currentPhase)
  const period = useGameStore((s) => s.currentPeriod)
  const speed = useGameStore((s) => s.speed)
  const setSpeed = useGameStore((s) => s.setSpeed)
  const connection = useGameStore((s) => s.connection)
  const error = useGameStore((s) => s.error)
  const economy = useSimStore((s) => s.economy)

  const scenarioName = useSimStore((s) => s.scenarioName)
  const nPeriods = useSimStore((s) => s.nPeriods)
  const finished = useSimStore((s) => s.finished)
  const metrics = useSimStore((s) => s.metrics)
  const historyOpen = useGameStore((s) => s.historyOpen)
  const setHistoryOpen = useGameStore((s) => s.setHistoryOpen)
  const runCount = useHistoryStore((s) => s.runs.length)
  const eventLogOpen = useGameStore((s) => s.eventLogOpen)
  const setEventLogOpen = useGameStore((s) => s.setEventLogOpen)
  const eventCount = useSimStore((s) => s.eventLog.length)
  const pendingEvent = useSimStore((s) => s.pendingEvent)
  const turbo = useFeature('turbo')
  const forecastUnlocked = useFeature('forecast')
  const showForecast = useGameStore((s) => s.showForecast)
  const setShowForecast = useGameStore((s) => s.setShowForecast)
  const mode = useGameStore((s) => s.mode)
  const speeds: Speed[] = turbo ? [...BASE_SPEEDS, 'turbo'] : BASE_SPEEDS

  const playing = phase === 'playing'
  const ready = connection === 'open'

  return (
    <header className="hud">
      <div className="hud-row">
        <div className="hud-block">
          <span className="hud-label">Scenario</span>
          <span className="hud-value">{scenarioName}</span>
        </div>
        <div className="hud-block hud-period">
          <span className="hud-label">Period</span>
          <span className="hud-value hud-value-big">
            {period} / {nPeriods}
          </span>
          {finished && (
            <span className={`hud-complete${economy?.bankrupt ? ' bankrupt' : ''}`}>
              {economy?.bankrupt ? 'Bankrupt' : 'Simulation Complete'}
            </span>
          )}
        </div>
        <ScoreBar />
        <CashBadge />
        <div className="hud-block">
          <span className="hud-label">Total cost</span>
          <span className="hud-value">{money(metrics.totalCost)}</span>
        </div>
        <div className="hud-block">
          <span className="hud-label">Fill rate</span>
          <span className="hud-value">{pct(metrics.fillRate)}</span>
        </div>
        <div className="hud-block">
          <span className="hud-label">Service level</span>
          <span className="hud-value">{pct(metrics.serviceLevel)}</span>
        </div>

        <div className="hud-spacer" />

        <div className="hud-controls">
          {playing ? (
            <button onClick={pause}>Pause</button>
          ) : (
            <button onClick={play} disabled={!ready || finished || !!pendingEvent}>
              Play
            </button>
          )}
          <button onClick={step} disabled={!ready || finished || playing || !!pendingEvent}>
            Step
          </button>
          <button onClick={resetRun} disabled={!ready}>
            Reset
          </button>
          <div className="segmented" role="group" aria-label="Speed">
            {speeds.map((s) => (
              <button key={s} className={s === speed ? 'active' : ''} onClick={() => setSpeed(s)}>
                {s === 'turbo' ? 'turbo ×8' : s}
              </button>
            ))}
          </div>
          <ObjectivesPanel />
          <button
            className={eventLogOpen ? 'active' : ''}
            title="Event log"
            onClick={() => {
              setHistoryOpen(false)
              setEventLogOpen(!eventLogOpen)
            }}
          >
            📋 Events{eventCount > 0 ? ` (${eventCount})` : ''}
          </button>
          <button
            className={historyOpen ? 'active' : ''}
            onClick={() => {
              setEventLogOpen(false)
              setHistoryOpen(!historyOpen)
            }}
          >
            History{runCount > 0 ? ` (${runCount})` : ''}
          </button>
          {forecastUnlocked && (
            <button
              className={showForecast ? 'active' : ''}
              title="Show expected demand for the next 5 periods"
              onClick={() => setShowForecast(!showForecast)}
            >
              🔮 Forecast
            </button>
          )}
          <button onClick={backToSetup}>{mode === 'campaign' ? 'Levels' : 'Scenarios'}</button>
        </div>
      </div>
      {economy?.crisis && !finished && (
        <div className="hud-crisis">
          <strong>CASH CRISIS</strong> — point gains are halved and orders are capped at current
          demand. Bankruptcy in{' '}
          {economy.cash < -economy.overdraft_limit
            ? 0
            : Math.max(0, economy.bankruptcy_periods - economy.zero_streak)}{' '}
          periods unless cash recovers.
        </div>
      )}
      {(error || !ready) && (
        <div className="hud-banner">{error ?? `Connecting to simulation server (${connection})…`}</div>
      )}
    </header>
  )
}
