import { backToSetup, pause, play, resetRun, step } from '../hooks/useSimulation'
import { useGameStore, type Speed } from '../store/gameStore'
import { useSimStore } from '../store/simStore'
import { useHistoryStore } from '../store/historyStore'
import { ObjectivesPanel } from './ObjectivesPanel'
import { ScoreBar } from './ScoreBar'

const SPEEDS: Speed[] = ['slow', 'normal', 'fast']

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

  const scenarioName = useSimStore((s) => s.scenarioName)
  const nPeriods = useSimStore((s) => s.nPeriods)
  const finished = useSimStore((s) => s.finished)
  const metrics = useSimStore((s) => s.metrics)
  const historyOpen = useGameStore((s) => s.historyOpen)
  const setHistoryOpen = useGameStore((s) => s.setHistoryOpen)
  const runCount = useHistoryStore((s) => s.runs.length)

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
          {finished && <span className="hud-complete">Simulation Complete</span>}
        </div>
        <ScoreBar />
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
            <button onClick={play} disabled={!ready || finished}>
              Play
            </button>
          )}
          <button onClick={step} disabled={!ready || finished || playing}>
            Step
          </button>
          <button onClick={resetRun} disabled={!ready}>
            Reset
          </button>
          <div className="segmented" role="group" aria-label="Speed">
            {SPEEDS.map((s) => (
              <button key={s} className={s === speed ? 'active' : ''} onClick={() => setSpeed(s)}>
                {s}
              </button>
            ))}
          </div>
          <ObjectivesPanel />
          <button className={historyOpen ? 'active' : ''} onClick={() => setHistoryOpen(!historyOpen)}>
            History{runCount > 0 ? ` (${runCount})` : ''}
          </button>
          <button onClick={backToSetup}>Scenarios</button>
        </div>
      </div>
      {(error || !ready) && (
        <div className="hud-banner">{error ?? `Connecting to simulation server (${connection})…`}</div>
      )}
    </header>
  )
}
