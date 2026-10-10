import { useAnimatedNumber } from '../hooks/useAnimatedNumber'
import { useGameStore } from '../store/gameStore'
import { useSimStore } from '../store/simStore'
import { STATUS_COLORS, whole } from './format'

/** Running score with a rolling counter, coloured by how the objectives are tracking. */
export function ScoreBar() {
  const score = useSimStore((s) => s.score)
  const warnAt = useGameStore((s) => s.scoreWarnAt)
  const shown = useAnimatedNumber(score?.total ?? 0)

  const status = score?.status ?? 'green'
  return (
    <div className="hud-block hud-score">
      <span className="hud-label">Score</span>
      {/* Re-keyed on each warning so the pulse animation restarts. */}
      <span
        key={warnAt}
        className={`hud-value hud-score-value${warnAt ? ' warn-pulse' : ''}`}
        style={{ color: STATUS_COLORS[status] }}
      >
        {whole(shown)}
      </span>
    </div>
  )
}
